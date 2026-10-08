-- MechWar-X | MySQL 8.0.16+ | InnoDB
-- AI disclosure: OpenAI ChatGPT generated this SQL, sample data and tests.
-- The group must review, execute and verify it before submission.
USE MechWarX;
SET SESSION time_zone = '+00:00';
-- Run once after 01-03; IDs are captured, not assumed to start at 1.
START TRANSACTION;
INSERT INTO MechType(TypeName) VALUES ('Light Scout'); SET @scout=LAST_INSERT_ID();
INSERT INTO MechType(TypeName) VALUES ('Assault Brawler'); SET @brawler=LAST_INSERT_ID();
INSERT INTO MechType(TypeName) VALUES ('Heavy Artillery'); SET @artillery=LAST_INSERT_ID();
INSERT INTO MechType(TypeName) VALUES ('Juggernaut'); SET @juggernaut=LAST_INSERT_ID();
INSERT INTO BattleGarage(GarageName,GridAddress,DispatchPhone)
 VALUES('Neo-Prime Central','Sector A, Grid 12-08','555-0101'); SET @central=LAST_INSERT_ID();
INSERT INTO BattleGarage(GarageName,GridAddress,DispatchPhone)
 VALUES('East Battle Hangar','Sector E, Grid 31-17','555-0102'); SET @east=LAST_INSERT_ID();
INSERT INTO PitCrewTechnician(GarageID,FullName,Phone,CorporateEmail)
 VALUES(@central,'Alex Rivera','555-0201','alex@mechwar.example'); SET @chief=LAST_INSERT_ID();
INSERT INTO PitCrewTechnician(GarageID,FullName,Phone,CorporateEmail)
 VALUES(@east,'Jordan Lee','555-0202','jordan@mechwar.example');
INSERT INTO Client(FirstName,LastName,CorporateAddress,Phone,Email,CombatLicenseToken,LicenseExpiration)
 VALUES('Maya','Grant','Sponsor Plaza 10','555-0301','maya@sponsor.example','PILOT-DEMO-001',DATE_ADD(CURRENT_DATE,INTERVAL 3 YEAR));
SET @client1=LAST_INSERT_ID();
INSERT INTO Client(FirstName,LastName,CorporateAddress,Phone,Email,CombatLicenseToken,LicenseExpiration)
 VALUES('Noah','Chen','Sponsor Plaza 22','555-0302','noah@sponsor.example','PILOT-DEMO-002',DATE_ADD(CURRENT_DATE,INTERVAL 3 YEAR));
SET @client2=LAST_INSERT_ID();
INSERT INTO Mech(ChassisSerial,Make,Model,AssemblyYear,ArmorColor,DailyRate,MechTypeID,GarageID)
 VALUES('MWX-SCOUT-001','NovaWorks','Swift',2025,'Silver',500,@scout,@central);
SET @mech1=LAST_INSERT_ID();
INSERT INTO Mech(ChassisSerial,Make,Model,AssemblyYear,ArmorColor,DailyRate,MechTypeID,GarageID)
 VALUES('MWX-BRAWLER-002','TitanForge','Hammer',2026,'Red',900,@brawler,@central);
SET @mech2=LAST_INSERT_ID();
INSERT INTO Mech(ChassisSerial,Make,Model,AssemblyYear,ArmorColor,DailyRate,MechTypeID,GarageID)
 VALUES('MWX-ARTILLERY-003','NovaWorks','Longshot',2025,'Blue',1200,@artillery,@east);
SET @mech3=LAST_INSERT_ID();
INSERT INTO Mech(ChassisSerial,Make,Model,AssemblyYear,ArmorColor,DailyRate,MechTypeID,GarageID)
 VALUES('MWX-JUGGERNAUT-004','TitanForge','Fortress',2026,'Black',1800,@juggernaut,@east);
COMMIT;
SET @start=TIMESTAMP(DATE_ADD(CURRENT_DATE,INTERVAL 7 DAY),'10:00:00');
CALL sp_BookDeployment(@client1,@mech1,@start,DATE_ADD(@start,INTERVAL 2 DAY),@central,@east,@booking1);
CALL sp_BookDeployment(@client2,@mech2,@start,DATE_ADD(@start,INTERVAL 1 DAY),@central,@central,@booking2);
CALL sp_CancelDeployment(@booking2);
CALL sp_ReportMaintenance(@mech3,@client2,'Critical','Shield generator failure.',@chief,@incident);
CALL sp_ReportMaintenance(@mech1,NULL,'Routine','Scheduled sensor calibration.',@chief,@routine);
SELECT MechID,ChassisSerial,OperationalStatus FROM Mech ORDER BY MechID;
SELECT SerialID,ClientID,Status,EstimatedCost FROM DeploymentManifest ORDER BY SerialID;
SELECT LogID,MechID,IssueType,Status FROM MaintenanceLog ORDER BY LogID;
