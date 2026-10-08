-- MechWar-X | MySQL 8.0.16+ | InnoDB
-- AI disclosure: OpenAI ChatGPT generated this SQL, sample data and tests.
-- The group must review, execute and verify it before submission.
USE MechWarX;
SET SESSION time_zone = '+00:00';
-- Runs isolated fixtures; never changes the sample mechs or clients.
-- Test fixtures are deleted on success or failure. Temporary results remain
-- visible only in this connection. Run this file as a complete script.
DROP TEMPORARY TABLE IF EXISTS MechWarXTestResults;
CREATE TEMPORARY TABLE MechWarXTestResults (
    TestNumber INT AUTO_INCREMENT PRIMARY KEY,
    TestName VARCHAR(150), Result ENUM('PASS','FAIL')
);
DROP PROCEDURE IF EXISTS sp_RunProjectTests;
DELIMITER $$
CREATE PROCEDURE sp_RunProjectTests()
BEGIN
    DECLARE v_type INT DEFAULT NULL;
    DECLARE v_garage INT DEFAULT NULL;
    DECLARE v_other INT DEFAULT NULL;
    DECLARE v_chief INT DEFAULT NULL;
    DECLARE v_client INT DEFAULT NULL;
    DECLARE v_mech INT DEFAULT NULL;
    DECLARE v_book INT;
    DECLARE v_adjacent INT;
    DECLARE v_log1 INT;
    DECLARE v_log2 INT;
    DECLARE v_out INT;
    DECLARE v_rejected BOOLEAN;
    DECLARE v_ok BOOLEAN;
    DECLARE v_start DATETIME;
    DECLARE v_end DATETIME;
    DECLARE v_suffix VARCHAR(36);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
      ROLLBACK;
      DELETE FROM MaintenanceLog WHERE MechID=v_mech;
      DELETE FROM DeploymentManifest WHERE MechID=v_mech;
      DELETE FROM Mech WHERE MechID=v_mech;
      DELETE FROM Client WHERE ClientID=v_client;
      DELETE FROM PitCrewTechnician WHERE StaffID=v_chief;
      DELETE FROM BattleGarage WHERE GarageID IN(v_garage,v_other);
      DELETE FROM MechType WHERE MechTypeID=v_type;
      RESIGNAL;
    END;
    SET v_suffix=UUID();
    INSERT INTO MechType(TypeName) VALUES(CONCAT('TEST-',v_suffix)); SET v_type=LAST_INSERT_ID();
    INSERT INTO BattleGarage(GarageName,GridAddress,DispatchPhone) VALUES('Test Departure','Test A','555-1000');
    SET v_garage=LAST_INSERT_ID();
    INSERT INTO BattleGarage(GarageName,GridAddress,DispatchPhone) VALUES('Test Return','Test B','555-1001');
    SET v_other=LAST_INSERT_ID();
    INSERT INTO PitCrewTechnician(GarageID,FullName,Phone,CorporateEmail)
      VALUES(v_garage,'Test Chief','555-1002',CONCAT(v_suffix,'@test.example')); SET v_chief=LAST_INSERT_ID();
    INSERT INTO Client(FirstName,LastName,CorporateAddress,Phone,Email,CombatLicenseToken,LicenseExpiration)
      VALUES('Test','Pilot','Test Address','555-1003','pilot@test.example',v_suffix,DATE_ADD(CURRENT_DATE,INTERVAL 1 YEAR));
    SET v_client=LAST_INSERT_ID();
    INSERT INTO Mech(ChassisSerial,Make,Model,AssemblyYear,ArmorColor,DailyRate,MechTypeID,GarageID)
      VALUES(v_suffix,'Test','Test',2026,'White',100,v_type,v_garage); SET v_mech=LAST_INSERT_ID();
    SET v_start=DATE_ADD(CURRENT_TIMESTAMP,INTERVAL 10 DAY);
    SET v_end=DATE_ADD(v_start,INTERVAL 1 DAY);
    CALL sp_BookDeployment(v_client,v_mech,v_start,v_end,v_garage,v_other,v_book);
    SELECT COUNT(*)=1 INTO v_ok FROM DeploymentManifest WHERE SerialID=v_book AND EstimatedCost=100;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Valid booking and estimated cost',IF(v_ok,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      CALL sp_BookDeployment(v_client,v_mech,DATE_ADD(v_start,INTERVAL 1 HOUR),DATE_ADD(v_end,INTERVAL 1 HOUR),v_garage,v_other,v_out);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Overlapping booking rejected',IF(v_rejected,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      CALL sp_BookDeployment(v_client,v_mech,DATE_SUB(v_start,INTERVAL 1 HOUR),DATE_ADD(v_end,INTERVAL 1 HOUR),v_garage,v_other,v_out);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Enclosing booking rejected',IF(v_rejected,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      CALL sp_BookDeployment(v_client,v_mech,v_start,v_start,v_garage,v_other,v_out);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Zero-length booking rejected',IF(v_rejected,'PASS','FAIL'));
    CALL sp_BookDeployment(v_client,v_mech,v_end,DATE_ADD(v_end,INTERVAL 1 DAY),v_garage,v_other,v_adjacent);
    SELECT COUNT(*)=1 INTO v_ok FROM DeploymentManifest WHERE SerialID=v_adjacent;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Adjacent booking allowed',IF(v_ok,'PASS','FAIL'));
    CALL sp_CancelDeployment(v_adjacent);
    SELECT OperationalStatus='Available' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Cancellation restores availability',IF(v_ok,'PASS','FAIL'));
    CALL sp_ReportMaintenance(v_mech,v_client,'Critical','Test failure one',v_chief,v_log1);
    CALL sp_ReportMaintenance(v_mech,v_client,'Critical','Test failure two',v_chief,v_log2);
    SELECT OperationalStatus='Unavailable' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Critical incident locks mech',IF(v_ok,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      CALL sp_BookDeployment(v_client,v_mech,DATE_ADD(v_end,INTERVAL 2 DAY),DATE_ADD(v_end,INTERVAL 3 DAY),v_garage,v_other,v_out);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Booking blocked during critical failure',IF(v_rejected,'PASS','FAIL'));
    CALL sp_CancelDeployment(v_book);
    SELECT OperationalStatus='Unavailable' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Cancellation preserves critical lock',IF(v_ok,'PASS','FAIL'));
    CALL sp_UpdateMaintenance(v_log1,'Repaired',v_chief,'First failure repaired.');
    SELECT OperationalStatus='Unavailable' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('One remaining failure keeps mech locked',IF(v_ok,'PASS','FAIL'));
    CALL sp_UpdateMaintenance(v_log2,'Repaired',v_chief,'Second failure repaired.');
    SELECT OperationalStatus='Available' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('All critical repairs restore availability',IF(v_ok,'PASS','FAIL'));
    CALL sp_ReportMaintenance(v_mech,NULL,'Routine','Routine calibration',v_chief,v_out);
    SELECT OperationalStatus='Available' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Routine maintenance does not lock mech',IF(v_ok,'PASS','FAIL'));
    UPDATE Client SET LicenseExpiration=DATE_SUB(CURRENT_DATE,INTERVAL 1 DAY) WHERE ClientID=v_client;
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      CALL sp_BookDeployment(v_client,v_mech,v_start,v_end,v_garage,v_other,v_out);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Expired pilot license rejected',IF(v_rejected,'PASS','FAIL'));
    UPDATE Client SET LicenseExpiration=DATE_ADD(CURRENT_DATE,INTERVAL 1 YEAR) WHERE ClientID=v_client;
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      INSERT INTO Mech(ChassisSerial,Make,Model,AssemblyYear,ArmorColor,DailyRate,MechTypeID,GarageID) VALUES(v_suffix,'Test','Test',2026,'Blue',100,v_type,v_garage);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Duplicate chassis rejected',IF(v_rejected,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      UPDATE Mech SET DailyRate=-1 WHERE MechID=v_mech;
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Negative daily rate rejected',IF(v_rejected,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      UPDATE Mech SET MechTypeID=-1 WHERE MechID=v_mech;
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Invalid foreign key rejected',IF(v_rejected,'PASS','FAIL'));
    CALL sp_BookDeployment(v_client,v_mech,v_start,v_end,v_garage,v_other,v_book);
    -- TEST ONLY: move fixture window to now instead of waiting ten days.
    UPDATE DeploymentManifest SET ScheduledStart=DATE_SUB(CURRENT_TIMESTAMP,INTERVAL 1 HOUR),
      ScheduledReturn=DATE_ADD(CURRENT_TIMESTAMP,INTERVAL 1 DAY) WHERE SerialID=v_book;
    CALL sp_StartDeployment(v_book);
    SELECT OperationalStatus='Deployed' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Starting sets Deployed status',IF(v_ok,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      CALL sp_BookDeployment(v_client,v_mech,DATE_ADD(v_end,INTERVAL 2 DAY),DATE_ADD(v_end,INTERVAL 3 DAY),v_garage,v_other,v_out);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Active mech cannot be booked even outside its window',IF(v_rejected,'PASS','FAIL'));
    -- TEST ONLY: simulate two hours of elapsed deployment.
    UPDATE DeploymentManifest SET ActualStart=DATE_SUB(CURRENT_TIMESTAMP,INTERVAL 2 HOUR) WHERE SerialID=v_book;
    CALL sp_CompleteDeployment(v_book,1.50);
    SELECT CombatHours=1.50 AND GarageID=v_other AND OperationalStatus='Available' INTO v_ok FROM Mech WHERE MechID=v_mech;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Completion increments combat hours and moves garage',IF(v_ok,'PASS','FAIL'));
    SELECT Status='Completed' AND ActualReturn IS NOT NULL AND FinalCost=100 INTO v_ok FROM DeploymentManifest WHERE SerialID=v_book;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Completion records actual return and final cost',IF(v_ok,'PASS','FAIL'));
    SET v_rejected=FALSE;
    BEGIN
      DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_rejected=TRUE;
      CALL sp_CompleteDeployment(v_book,1.50);
    END;
    INSERT INTO MechWarXTestResults(TestName,Result) VALUES('Second completion rejected without double-counting hours',IF(v_rejected,'PASS','FAIL'));
    DELETE FROM MaintenanceLog WHERE MechID=v_mech;
    DELETE FROM DeploymentManifest WHERE MechID=v_mech;
    DELETE FROM Mech WHERE MechID=v_mech;
    DELETE FROM Client WHERE ClientID=v_client;
    DELETE FROM PitCrewTechnician WHERE StaffID=v_chief;
    DELETE FROM BattleGarage WHERE GarageID IN(v_garage,v_other);
    DELETE FROM MechType WHERE MechTypeID=v_type;
END$$
DELIMITER ;
CALL sp_RunProjectTests();
DROP PROCEDURE sp_RunProjectTests;
SELECT * FROM MechWarXTestResults ORDER BY TestNumber;
SELECT COUNT(*) AS TotalTests, SUM(Result='PASS') AS Passed,
       SUM(Result='FAIL') AS Failed FROM MechWarXTestResults;

-- Screenshot-friendly dashboard query. Change the token for another client.
SELECT d.SerialID,c.FirstName,c.LastName,m.ChassisSerial,d.ScheduledStart,
       d.ScheduledReturn,d.Status,d.EstimatedCost,d.FinalCost
FROM DeploymentManifest d JOIN Client c ON c.ClientID=d.ClientID
JOIN Mech m ON m.MechID=d.MechID
WHERE c.CombatLicenseToken='PILOT-DEMO-001'
ORDER BY d.ScheduledStart DESC;

-- GUI dashboard uses this same query with WHERE d.ClientID = a bound parameter.
-- Active maintenance console:
SELECT l.LogID,m.ChassisSerial,l.IssueType,l.Description,l.Status,l.ReportedAt,
       t.FullName AS PitCrewChief,t.Phone,t.CorporateEmail
FROM MaintenanceLog l JOIN Mech m ON m.MechID=l.MechID
LEFT JOIN PitCrewTechnician t ON t.StaffID=l.PitCrewChiefID
WHERE l.Status<>'Repaired' ORDER BY l.ReportedAt DESC;

-- Manual concurrency check (two separate Workbench connections):
-- CALL sp_BookDeployment in both connections with the SAME available mech and
-- overlapping future windows. Exactly one should succeed; the other rejects.
-- This is separate from the single-connection tests above.
