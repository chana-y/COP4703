-- MechWar-X | MySQL 8.0.16+ | InnoDB
-- AI disclosure: OpenAI ChatGPT generated this SQL, sample data and tests.
-- The group must review, execute and verify it before submission.
USE MechWarX;
-- Creates all seven project tables, including any missing after partial setup.
-- Existing tables and records are retained. This does not migrate altered schemas.
CREATE TABLE IF NOT EXISTS MechType (
    MechTypeID INT AUTO_INCREMENT PRIMARY KEY,
    TypeName VARCHAR(60) NOT NULL UNIQUE,
    CONSTRAINT ck_type_name CHECK (CHAR_LENGTH(TRIM(TypeName)) > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS BattleGarage (
    GarageID INT AUTO_INCREMENT PRIMARY KEY,
    GarageName VARCHAR(100) NOT NULL,
    GridAddress VARCHAR(255) NOT NULL,
    DispatchPhone VARCHAR(30) NOT NULL,
    CONSTRAINT ck_garage_name CHECK (CHAR_LENGTH(TRIM(GarageName)) > 0),
    CONSTRAINT ck_garage_address CHECK (CHAR_LENGTH(TRIM(GridAddress)) > 0),
    CONSTRAINT ck_garage_phone CHECK (CHAR_LENGTH(TRIM(DispatchPhone)) > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS PitCrewTechnician (
    StaffID INT AUTO_INCREMENT PRIMARY KEY,
    GarageID INT NOT NULL,
    FullName VARCHAR(120) NOT NULL,
    Phone VARCHAR(30) NOT NULL,
    CorporateEmail VARCHAR(254) NOT NULL UNIQUE,
    CONSTRAINT ck_staff_name CHECK (CHAR_LENGTH(TRIM(FullName)) > 0),
    CONSTRAINT ck_staff_phone CHECK (CHAR_LENGTH(TRIM(Phone)) > 0),
    CONSTRAINT ck_staff_email CHECK (CHAR_LENGTH(TRIM(CorporateEmail)) > 0),
    CONSTRAINT fk_staff_garage FOREIGN KEY (GarageID) REFERENCES BattleGarage(GarageID)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Client (
    ClientID INT AUTO_INCREMENT PRIMARY KEY,
    FirstName VARCHAR(60) NOT NULL,
    LastName VARCHAR(60) NOT NULL,
    CorporateAddress VARCHAR(255) NOT NULL,
    Phone VARCHAR(30) NOT NULL,
    Email VARCHAR(254) NOT NULL,
    CombatLicenseToken VARCHAR(100) NOT NULL UNIQUE,
    LicenseExpiration DATE NOT NULL,
    CONSTRAINT ck_client_first CHECK (CHAR_LENGTH(TRIM(FirstName)) > 0),
    CONSTRAINT ck_client_last CHECK (CHAR_LENGTH(TRIM(LastName)) > 0),
    CONSTRAINT ck_client_address CHECK (CHAR_LENGTH(TRIM(CorporateAddress)) > 0),
    CONSTRAINT ck_client_phone CHECK (CHAR_LENGTH(TRIM(Phone)) > 0),
    CONSTRAINT ck_client_email CHECK (CHAR_LENGTH(TRIM(Email)) > 0),
    CONSTRAINT ck_client_license CHECK (CHAR_LENGTH(TRIM(CombatLicenseToken)) > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Mech (
    MechID INT AUTO_INCREMENT PRIMARY KEY,
    ChassisSerial VARCHAR(80) NOT NULL UNIQUE,
    Make VARCHAR(80) NOT NULL,
    Model VARCHAR(80) NOT NULL,
    AssemblyYear SMALLINT NOT NULL,
    ArmorColor VARCHAR(50) NOT NULL,
    DailyRate DECIMAL(12,2) NOT NULL,
    CombatHours DECIMAL(12,2) NOT NULL DEFAULT 0,
    MechTypeID INT NOT NULL,
    GarageID INT NOT NULL,
    OperationalStatus ENUM('Available','Deployed','Unavailable') NOT NULL DEFAULT 'Available',
    CONSTRAINT ck_mech_serial CHECK (CHAR_LENGTH(TRIM(ChassisSerial)) > 0),
    CONSTRAINT ck_mech_make CHECK (CHAR_LENGTH(TRIM(Make)) > 0),
    CONSTRAINT ck_mech_model CHECK (CHAR_LENGTH(TRIM(Model)) > 0),
    CONSTRAINT ck_mech_color CHECK (CHAR_LENGTH(TRIM(ArmorColor)) > 0),
    CONSTRAINT ck_mech_year CHECK (AssemblyYear > 0),
    CONSTRAINT ck_mech_rate CHECK (DailyRate > 0),
    CONSTRAINT ck_mech_hours CHECK (CombatHours >= 0),
    CONSTRAINT fk_mech_type FOREIGN KEY (MechTypeID) REFERENCES MechType(MechTypeID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_mech_garage FOREIGN KEY (GarageID) REFERENCES BattleGarage(GarageID)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS DeploymentManifest (
    SerialID INT AUTO_INCREMENT PRIMARY KEY,
    ClientID INT NOT NULL,
    MechID INT NOT NULL,
    ScheduledStart DATETIME NOT NULL,
    ScheduledReturn DATETIME NOT NULL,
    ActualStart DATETIME NULL,
    ActualReturn DATETIME NULL,
    -- Rate captured at booking; later fleet rate changes do not alter a contract.
    BookedDailyRate DECIMAL(12,2) NOT NULL,
    EstimatedCost DECIMAL(14,2) NOT NULL,
    FinalCost DECIMAL(14,2) NULL,
    Status ENUM('Match Booked','Active in Arena','Completed','Cancelled') NOT NULL DEFAULT 'Match Booked',
    DepartureGarageID INT NOT NULL,
    ReturnGarageID INT NOT NULL,
    -- Actual combat hours are supplied at completion, not inferred from rental time.
    CombatHoursUsed DECIMAL(12,2) NULL,
    CONSTRAINT ck_manifest_window CHECK (ScheduledReturn > ScheduledStart),
    CONSTRAINT ck_manifest_rate CHECK (BookedDailyRate > 0),
    CONSTRAINT ck_manifest_cost CHECK (EstimatedCost > 0 AND (FinalCost IS NULL OR FinalCost > 0)),
    CONSTRAINT ck_manifest_hours CHECK (CombatHoursUsed IS NULL OR CombatHoursUsed >= 0),
    CONSTRAINT ck_manifest_lifecycle CHECK (
      (Status IN ('Match Booked','Cancelled') AND ActualStart IS NULL AND ActualReturn IS NULL AND FinalCost IS NULL AND CombatHoursUsed IS NULL)
      OR (Status = 'Active in Arena' AND ActualStart IS NOT NULL AND ActualReturn IS NULL AND FinalCost IS NULL AND CombatHoursUsed IS NULL)
      OR (Status = 'Completed' AND ActualStart IS NOT NULL AND ActualReturn IS NOT NULL
          AND ActualReturn > ActualStart AND FinalCost IS NOT NULL AND CombatHoursUsed IS NOT NULL)
    ),
    CONSTRAINT fk_manifest_client FOREIGN KEY (ClientID) REFERENCES Client(ClientID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_manifest_mech FOREIGN KEY (MechID) REFERENCES Mech(MechID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_manifest_departure FOREIGN KEY (DepartureGarageID) REFERENCES BattleGarage(GarageID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_manifest_return FOREIGN KEY (ReturnGarageID) REFERENCES BattleGarage(GarageID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX ix_manifest_schedule (MechID, Status, ScheduledStart, ScheduledReturn),
    INDEX ix_manifest_client (ClientID, ScheduledStart)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS MaintenanceLog (
    LogID INT AUTO_INCREMENT PRIMARY KEY,
    ReportedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    MechID INT NOT NULL,
    ReportingClientID INT NULL, -- NULL for telemetry/staff reports.
    IssueType ENUM('Routine','Critical') NOT NULL,
    Description TEXT NOT NULL,
    Status ENUM('Reported','In-Progress','Awaiting Parts','Repaired') NOT NULL DEFAULT 'Reported',
    ResolvedAt DATETIME NULL,
    PitCrewChiefID INT NULL, -- May be assigned after initial report.
    EngineeringNotes TEXT NULL,
    CONSTRAINT ck_log_description CHECK (CHAR_LENGTH(TRIM(Description)) > 0),
    CONSTRAINT ck_log_resolution CHECK (
      (Status = 'Repaired' AND ResolvedAt IS NOT NULL AND ResolvedAt >= ReportedAt)
      OR (Status <> 'Repaired' AND ResolvedAt IS NULL)
    ),
    CONSTRAINT fk_log_mech FOREIGN KEY (MechID) REFERENCES Mech(MechID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_log_client FOREIGN KEY (ReportingClientID) REFERENCES Client(ClientID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_log_chief FOREIGN KEY (PitCrewChiefID) REFERENCES PitCrewTechnician(StaffID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX ix_log_open (MechID, IssueType, Status)
) ENGINE=InnoDB;

-- 3NF: each entity stores facts about its primary key; related descriptive data
-- stays in its own table. Costs/rate represent contract snapshots, not a join to
-- today's Mech.DailyRate. Report date and time are stored once as ReportedAt.
-- Relationships (parent -> child; each parent can have zero or many children):
-- MechType 1:M Mech; BattleGarage 1:M Mech; BattleGarage 1:M PitCrewTechnician.
-- Client 1:M DeploymentManifest; Mech 1:M DeploymentManifest.
-- BattleGarage 1:M DeploymentManifest twice (departure and return roles).
-- Mech 1:M MaintenanceLog; Client 1:M MaintenanceLog (optional on log).
-- PitCrewTechnician 1:M MaintenanceLog (optional assigned chief on log).
-- Every other child-to-parent relationship is mandatory (exactly one parent).
