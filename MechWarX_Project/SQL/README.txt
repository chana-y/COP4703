MECHWAR-X SQL FILES

Platform: MySQL 8.0.16 or later (not MariaDB or SQLite).
Run each numbered file in order using MySQL Workbench, connected as the schema
owner. Use Execute All, not just Execute Current Statement. For a NEW database, run 01-04 in order, then optionally 05.
For your EXISTING database, close the GUI and run the updated 02 and 03.
File 02 keeps existing tables/data and creates missing tables. It does not alter
an existing table's columns if you independently changed the schema.
File 03 replaces the seven project procedures and three triggers. Execute ALL
of it, including DELIMITER lines. Confirm seven procedure rows and three trigger
rows at the end. A warning about dropping a nonexistent routine is expected on
a new database; a red error is not.
File 04 inserts demonstration data and is for ONE-TIME use only. Skip it if your
sample records already exist. File 05 is an optional test suite, not startup.
Once the database is installed, launch GUI/main.py without running SQL again.
No separate repair scripts are used or included.

01_create_database.sql - create/select database; does not erase existing data.
02_create_tables.sql - creates missing tables with constraints and indexes.
03_stored_procedures.sql - installs/reinstalls procedures and synchronization triggers.
04_sample_data.sql - fictional demonstration records.
05_test_queries.sql - 21 checks with PASS/FAIL results and display queries.

AI DISCLOSURE
OpenAI ChatGPT generated the SQL schema, stored procedures, triggers, sample
data and test queries. The group reviewed and tested [replace this sentence
with an accurate description of your actual review/testing before submitting].

GUI integration
Use parameterized database calls. Set each connection time_zone to +00:00;
convert display times in the GUI if needed. Public mutation procedures own their
transactions. Do not call them inside an existing transaction. Register mechs
with a parameterized INSERT; use the procedures for deployment/maintenance.
For an OUT parameter: CALL sp_BookDeployment(..., @new_id); SELECT @new_id;
Consume all result sets in your database connector after CALL.

Procedures
sp_BookDeployment(client, mech, start, return, departureGarage, returnGarage, OUT id)
sp_CancelDeployment(manifest)
sp_ReportMaintenance(mech, reportingClientOrNull, RoutineOrCritical, description, chiefOrNull, OUT id)
sp_UpdateMaintenance(log, status, chief, notes)
sp_StartDeployment(manifest)
sp_CompleteDeployment(manifest, actualCombatHours)
sp_SyncMechStatus is internal; GUI users should not call it directly.

Design decisions
- Reservations use [start, return): back-to-back reservations are allowed.
- Future bookings do not set the current operational status to Unavailable.
- An active deployment blocks all new bookings until it is completed.
- A critical failure blocks bookings and starts; already-booked future contracts
  remain recorded and must be cancelled or delayed by staff if repairs run late.
- Cancellation applies to bookings; an active deployment must be completed.
- Cancelled is the canonical cancellation status. Destruction is recorded as a
  critical incident, so cancellation cannot release a damaged mech.
- Repair releases a mech only after ALL critical incidents are repaired; an
  active contract continues to keep it Deployed.
- Costs use whole commenced 24-hour days (minimum one), using the booked rate.
- Actual combat hours are supplied at completion and cannot exceed elapsed time.
- The return garage becomes the mech's current garage on completion. Starting a
  contract requires the mech to be physically at the departure garage. Separate
  staff-managed transport is needed if a later booking departs elsewhere.
- Routine logs do not reserve a downtime window; the brief gives no maintenance
  start/end interval. Add that feature only if your instructor requires it.
- Use procedures for all lifecycle writes. Triggers cover cancellation and
  incident status changes but arbitrary direct SQL can bypass other rules.
  A production GUI role should have EXECUTE on public procedures, needed SELECT,
  and column-limited mech registration INSERT; no direct lifecycle-table writes.
- Restrictive foreign keys preserve audit history. Do not delete real incidents.

Verification
The scripts were reviewed statically here; no MySQL server was available to
execute them. Run 05 and confirm 21 PASS / 0 FAIL locally, plus the documented
two-connection concurrency test. Test fixtures use unique IDs, clean themselves
up and do not alter sample records. Failed constraint tests may consume IDs;
auto-increment gaps are normal.

Submission
These are development files. Put SQL and 2-3 genuine implementation screenshots
in GX_SQL.pdf. Your separate ERD and GUI PDFs are still required. Replace X with
your group number. Do not submit the raw SQL scripts if the brief prohibits it.
