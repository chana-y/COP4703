-- MechWar-X | MySQL 8.0.16+ | InnoDB
-- AI disclosure: OpenAI ChatGPT generated this SQL, sample data and tests.
-- The group must review, execute and verify it before submission.
-- Close the GUI while installing. This file can be rerun after partial setup.
-- Replaces only this project's procedures and triggers; keeps tables and data.
DELIMITER ;
USE MechWarX;
DROP TRIGGER IF EXISTS trg_manifest_cancelled;
DROP TRIGGER IF EXISTS trg_incident_created;
DROP TRIGGER IF EXISTS trg_incident_updated;
DROP PROCEDURE IF EXISTS sp_CompleteDeployment;
DROP PROCEDURE IF EXISTS sp_StartDeployment;
DROP PROCEDURE IF EXISTS sp_UpdateMaintenance;
DROP PROCEDURE IF EXISTS sp_ReportMaintenance;
DROP PROCEDURE IF EXISTS sp_CancelDeployment;
DROP PROCEDURE IF EXISTS sp_BookDeployment;
DROP PROCEDURE IF EXISTS sp_SyncMechStatus;

SET SESSION time_zone = '+00:00';
-- GUI contract: call these public procedures for lifecycle changes; do not
-- INSERT/UPDATE manifests or maintenance directly. Use parameterized CALLs.
-- Calls own their transactions; do not wrap them inside another transaction.
-- The shared Mech row lock serializes concurrent bookings/maintenance actions.
-- Availability describes current condition. Future bookings are in the calendar,
-- so an Available mech can still have future, non-overlapping reservations.
DELIMITER $$

-- Internal helper, also used by automatic triggers. Never starts a transaction.
CREATE PROCEDURE sp_SyncMechStatus(IN p_MechID INT)
BEGIN
    DECLARE v_critical INT DEFAULT 0;
    DECLARE v_active INT DEFAULT 0;
    SELECT COUNT(*) INTO v_critical FROM MaintenanceLog
      WHERE MechID=p_MechID AND IssueType='Critical' AND Status<>'Repaired';
    SELECT COUNT(*) INTO v_active FROM DeploymentManifest
      WHERE MechID=p_MechID AND Status='Active in Arena';
    UPDATE Mech SET OperationalStatus = CASE
      WHEN v_critical>0 THEN 'Unavailable'
      WHEN v_active>0 THEN 'Deployed'
      ELSE 'Available' END WHERE MechID=p_MechID;
END$$

-- Procedure A: half-open intervals [start, return); adjacent bookings are valid.
CREATE PROCEDURE sp_BookDeployment(
    IN p_ClientID INT, IN p_MechID INT,
    IN p_Start DATETIME, IN p_Return DATETIME,
    IN p_DepartureGarageID INT, IN p_ReturnGarageID INT,
    OUT p_SerialID INT)
BEGIN
    DECLARE v_rate DECIMAL(12,2) DEFAULT NULL;
    DECLARE v_status VARCHAR(20);
    DECLARE v_expiry DATE DEFAULT NULL;
    DECLARE v_conflicts INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
    SET p_SerialID=NULL;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;
    IF p_Start IS NULL OR p_Return IS NULL OR p_Return<=p_Start OR p_Start<CURRENT_TIMESTAMP THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Booking requires a future start and return after start.';
    END IF;
    SELECT DailyRate, OperationalStatus INTO v_rate,v_status
      FROM Mech WHERE MechID=p_MechID FOR UPDATE;
    IF v_rate IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Mech does not exist.'; END IF;
    IF v_status<>'Available' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Mech is unavailable or still deployed.'; END IF;
    SELECT LicenseExpiration INTO v_expiry FROM Client WHERE ClientID=p_ClientID FOR SHARE;
    IF v_expiry IS NULL OR v_expiry<DATE(p_Return) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Client missing or license expires before scheduled return.';
    END IF;
    SELECT COUNT(*) INTO v_conflicts FROM DeploymentManifest
      WHERE MechID=p_MechID AND
      (Status='Active in Arena' OR
       (Status='Match Booked' AND ScheduledStart<p_Return AND ScheduledReturn>p_Start));
    IF v_conflicts>0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Mech already has a conflicting deployment.'; END IF;
    INSERT INTO DeploymentManifest
      (ClientID,MechID,ScheduledStart,ScheduledReturn,BookedDailyRate,EstimatedCost,DepartureGarageID,ReturnGarageID)
    VALUES (p_ClientID,p_MechID,p_Start,p_Return,v_rate,
      GREATEST(1,CEILING(TIMESTAMPDIFF(SECOND,p_Start,p_Return)/86400.0))*v_rate,
      p_DepartureGarageID,p_ReturnGarageID);
    SET p_SerialID=LAST_INSERT_ID();
    COMMIT;
END$$

-- Procedure B: the trigger below calls status synchronization automatically
-- whenever a manifest becomes Cancelled (including an ordinary SQL UPDATE).
CREATE PROCEDURE sp_CancelDeployment(IN p_SerialID INT)
BEGIN
    DECLARE v_mech INT DEFAULT NULL;
    DECLARE v_lock INT;
    DECLARE v_status VARCHAR(30);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;
    SELECT MechID INTO v_mech FROM DeploymentManifest WHERE SerialID=p_SerialID;
    IF v_mech IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Manifest does not exist.'; END IF;
    SELECT MechID INTO v_lock FROM Mech WHERE MechID=v_mech FOR UPDATE;
    SELECT Status INTO v_status FROM DeploymentManifest WHERE SerialID=p_SerialID FOR UPDATE;
    IF v_status<>'Match Booked' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Only a booked deployment can be cancelled.'; END IF;
    UPDATE DeploymentManifest SET Status='Cancelled' WHERE SerialID=p_SerialID;
    COMMIT;
END$$

CREATE TRIGGER trg_manifest_cancelled AFTER UPDATE ON DeploymentManifest
FOR EACH ROW
BEGIN
    IF NEW.Status='Cancelled' AND OLD.Status<>'Cancelled' THEN
      CALL sp_SyncMechStatus(NEW.MechID);
    END IF;
END$$

-- Procedure C: inserts an incident; the INSERT trigger immediately locks out
-- the asset for Critical incidents, including incidents inserted directly.
CREATE PROCEDURE sp_ReportMaintenance(
    IN p_MechID INT, IN p_ClientID INT, IN p_Type VARCHAR(20),
    IN p_Description TEXT, IN p_ChiefID INT, OUT p_LogID INT)
BEGIN
    DECLARE v_mech INT DEFAULT NULL;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
    SET p_LogID=NULL;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;
    SELECT MechID INTO v_mech FROM Mech WHERE MechID=p_MechID FOR UPDATE;
    IF v_mech IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Mech does not exist.'; END IF;
    IF p_Type IS NULL OR p_Type NOT IN ('Routine','Critical') THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Issue type must be Routine or Critical.';
    END IF;
    IF p_Description IS NULL OR CHAR_LENGTH(TRIM(p_Description))=0 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Incident description is required.';
    END IF;
    INSERT INTO MaintenanceLog(MechID,ReportingClientID,IssueType,Description,PitCrewChiefID)
      VALUES(p_MechID,p_ClientID,p_Type,p_Description,p_ChiefID);
    SET p_LogID=LAST_INSERT_ID();
    COMMIT;
END$$

CREATE TRIGGER trg_incident_created AFTER INSERT ON MaintenanceLog
FOR EACH ROW
BEGIN
    IF NEW.IssueType='Critical' AND NEW.Status<>'Repaired' THEN
      UPDATE Mech SET OperationalStatus='Unavailable' WHERE MechID=NEW.MechID;
    END IF;
END$$

CREATE TRIGGER trg_incident_updated AFTER UPDATE ON MaintenanceLog
FOR EACH ROW
BEGIN
    CALL sp_SyncMechStatus(OLD.MechID);
    IF NEW.MechID<>OLD.MechID THEN CALL sp_SyncMechStatus(NEW.MechID); END IF;
END$$

CREATE PROCEDURE sp_UpdateMaintenance(
    IN p_LogID INT, IN p_Status VARCHAR(20), IN p_ChiefID INT, IN p_Notes TEXT)
BEGIN
    DECLARE v_mech INT DEFAULT NULL;
    DECLARE v_lock INT;
    DECLARE v_old VARCHAR(20);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;
    SELECT MechID INTO v_mech FROM MaintenanceLog WHERE LogID=p_LogID;
    IF v_mech IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Maintenance log does not exist.'; END IF;
    SELECT MechID INTO v_lock FROM Mech WHERE MechID=v_mech FOR UPDATE;
    SELECT Status INTO v_old FROM MaintenanceLog WHERE LogID=p_LogID FOR UPDATE;
    IF v_old='Repaired' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Repaired logs are closed; create a new incident.'; END IF;
    IF p_Status IS NULL OR p_Status NOT IN ('Reported','In-Progress','Awaiting Parts','Repaired') THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Invalid maintenance status.';
    END IF;
    IF p_Status='Repaired' AND (p_ChiefID IS NULL OR p_Notes IS NULL OR CHAR_LENGTH(TRIM(p_Notes))=0) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Repair requires an assigned chief and engineering notes.';
    END IF;
    UPDATE MaintenanceLog SET Status=p_Status, PitCrewChiefID=p_ChiefID,
      EngineeringNotes=p_Notes, ResolvedAt=IF(p_Status='Repaired',CURRENT_TIMESTAMP,NULL)
      WHERE LogID=p_LogID;
    COMMIT;
END$$

CREATE PROCEDURE sp_StartDeployment(IN p_SerialID INT)
BEGIN
    DECLARE v_mech INT DEFAULT NULL;
    DECLARE v_garage INT;
    DECLARE v_departure INT;
    DECLARE v_client INT;
    DECLARE v_status VARCHAR(30);
    DECLARE v_op VARCHAR(20);
    DECLARE v_start DATETIME;
    DECLARE v_return DATETIME;
    DECLARE v_expiry DATE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;
    SELECT MechID INTO v_mech FROM DeploymentManifest WHERE SerialID=p_SerialID;
    IF v_mech IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Manifest does not exist.'; END IF;
    SELECT OperationalStatus,GarageID INTO v_op,v_garage FROM Mech WHERE MechID=v_mech FOR UPDATE;
    SELECT Status,ScheduledStart,ScheduledReturn,DepartureGarageID,ClientID
      INTO v_status,v_start,v_return,v_departure,v_client
      FROM DeploymentManifest WHERE SerialID=p_SerialID FOR UPDATE;
    IF v_status<>'Match Booked' OR v_op<>'Available' THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Deployment must be booked and mech must be available.';
    END IF;
    IF CURRENT_TIMESTAMP<v_start OR CURRENT_TIMESTAMP>=v_return THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Start is allowed only within the reserved time window.';
    END IF;
    IF v_garage<>v_departure THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Mech is not at the departure garage.'; END IF;
    SELECT LicenseExpiration INTO v_expiry FROM Client WHERE ClientID=v_client FOR SHARE;
    IF v_expiry<DATE(v_return) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Pilot license expires before scheduled return.'; END IF;
    UPDATE DeploymentManifest SET Status='Active in Arena',ActualStart=CURRENT_TIMESTAMP WHERE SerialID=p_SerialID;
    UPDATE Mech SET OperationalStatus='Deployed' WHERE MechID=v_mech;
    COMMIT;
END$$

CREATE PROCEDURE sp_CompleteDeployment(IN p_SerialID INT, IN p_CombatHours DECIMAL(12,2))
BEGIN
    DECLARE v_mech INT DEFAULT NULL;
    DECLARE v_lock INT;
    DECLARE v_status VARCHAR(30);
    DECLARE v_start DATETIME;
    DECLARE v_now DATETIME;
    DECLARE v_rate DECIMAL(12,2);
    DECLARE v_return_garage INT;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;
    SELECT MechID INTO v_mech FROM DeploymentManifest WHERE SerialID=p_SerialID;
    IF v_mech IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Manifest does not exist.'; END IF;
    SELECT MechID INTO v_lock FROM Mech WHERE MechID=v_mech FOR UPDATE;
    SELECT Status,ActualStart,BookedDailyRate,ReturnGarageID
      INTO v_status,v_start,v_rate,v_return_garage FROM DeploymentManifest WHERE SerialID=p_SerialID FOR UPDATE;
    SET v_now=CURRENT_TIMESTAMP;
    IF v_status<>'Active in Arena' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Only an active deployment can be completed.'; END IF;
    IF v_now<=v_start OR p_CombatHours IS NULL OR p_CombatHours<0
       OR p_CombatHours>TIMESTAMPDIFF(SECOND,v_start,v_now)/3600.0 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Combat hours must fit within the positive actual deployment duration.';
    END IF;
    UPDATE DeploymentManifest SET Status='Completed',ActualReturn=v_now,CombatHoursUsed=p_CombatHours,
      FinalCost=GREATEST(1,CEILING(TIMESTAMPDIFF(SECOND,v_start,v_now)/86400.0))*v_rate
      WHERE SerialID=p_SerialID;
    UPDATE Mech SET CombatHours=CombatHours+p_CombatHours,GarageID=v_return_garage WHERE MechID=v_mech;
    CALL sp_SyncMechStatus(v_mech);
    COMMIT;
END$$
DELIMITER ;

-- Installation check: expect seven procedures and three triggers.
SELECT ROUTINE_NAME AS InstalledProcedure
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA=DATABASE() AND ROUTINE_TYPE='PROCEDURE'
  AND LOWER(ROUTINE_NAME) IN ('sp_syncmechstatus','sp_bookdeployment','sp_canceldeployment','sp_reportmaintenance','sp_updatemaintenance','sp_startdeployment','sp_completedeployment')
ORDER BY ROUTINE_NAME;
SELECT TRIGGER_NAME AS InstalledTrigger
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA=DATABASE()
  AND LOWER(TRIGGER_NAME) IN ('trg_manifest_cancelled','trg_incident_created','trg_incident_updated')
ORDER BY TRIGGER_NAME;
