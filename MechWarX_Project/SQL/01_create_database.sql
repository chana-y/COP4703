-- MechWar-X | MySQL 8.0.16+ | InnoDB
-- AI disclosure: OpenAI ChatGPT generated this SQL, sample data and tests.
-- The group must review, execute and verify it before submission.
-- Run files 01 through 05 in order in MySQL Workbench.
-- Use a NEW project schema. This script does not delete existing databases.
CREATE DATABASE IF NOT EXISTS MechWarX
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE MechWarX;
-- Store all timestamps consistently in UTC, including GUI connections.
SET SESSION time_zone = '+00:00';
