MECHWAR-X PYTHON GUI
Python 3.10+ | Tkinter | MySQL 8.0.16+

START HERE (WINDOWS)
1. Extract MechWarX_GUI.zip. Keep all six .py files together in the extracted
   MechWarX_GUI folder. Do not run the app from inside the ZIP.
2. Your MySQL server must be running. Run the earlier SQL files 01-04 once in
   MySQL Workbench if you have not already. For an existing project database, close the GUI and run the updated SQL files
   02 and 03 once to apply the consolidated setup. File 02 preserves existing
   tables and file 03 replaces project procedures/triggers. Do not repeat sample
   insertion (04) if its records already exist. File 05 is optional testing.
   No separate repair scripts are required; SQL setup is not run on each launch.
3. Open that extracted folder in File Explorer. Click the address bar, type
   cmd, and press Enter. This opens a terminal in the correct folder.
4. Install the connector:
       py -m pip install -r requirements.txt
5. Launch:
       py main.py
   If you use the python command instead of py, use python for BOTH commands:
       python -m pip install -r requirements.txt
       python main.py
6. In the app, enter the SAME MySQL connection details used by Workbench:
       Host:     127.0.0.1 (if MySQL is on this computer)
       Port:     3306 (or your configured port)
       Username: your MySQL user, such as root for your local class setup
       Password: your MySQL password
       Database: MechWarX
   Click Connect. No password needs to be written into a Python file.

Run main.py only. It imports the other five modules automatically.
There is no separate GUI server or browser to start.

FILES
main.py                 Login window, tabs, common widgets, background DB work,
                        shared display helpers and the full AI disclosure.
database.py             MySQL connections, parameterized queries, validation,
                        stored procedure calls and readable error messages.
mech_registration.py    Screen 1: register mechs, list fleet, garage crew contacts.
manifest_dashboard.py  Screen 2: ClientID search, cancel/start/complete manifests.
booking.py              Screen 3: create bookings, estimate cost, view schedule.
maintenance.py          Screen 4: report incidents, inspect/update logs, repairs.
requirements.txt        Python connector dependency.
README.txt              These instructions and local verification checklist.

WHAT EACH SCREEN DOES
1. Fleet Registration
   Enter every field. Chassis serial must be unique, year and daily rate must
   be positive, combat hours may be zero. The type/garage lists come from MySQL.
   Select a fleet row to see technicians in that mech's garage.

2. Sponsor Manifests
   Enter ClientID and Search, or select a client from the dropdown. Current and
   historical manifests are listed. Select a row to cancel, start or complete.
   Start requires a booked contract inside its scheduled window, a valid pilot
   license and a mech at the departure garage. Completion asks for actual combat
   hours, calculates final cost in SQL, and updates the return garage.

3. Hangar Scheduling
   Select client, mech, departure/return garages and timestamps. Preview estimates
   whole commenced 24-hour days. Create booking calls sp_BookDeployment; the
   database rejects conflicts, expired licenses, critical failures and active
   deployments. A mech labelled Available can still have future reservations.
   The right-hand table shows open bookings for the selected mech.

4. Maintenance
   Report Routine or Critical issues. Reporting client and chief may initially
   be None. Select an existing log to change its status, assign a chief and save
   notes. Repaired requires a chief and engineering notes. Critical incidents
   immediately mark the mech Unavailable. One repair does not release a mech
   while another critical incident remains unresolved.
   Include repaired shows history; View full selected log shows untruncated text.

TIME AND DATA RULES
- Every displayed/entered timestamp is UTC. Use the live UTC clock at the bottom
  of the app. Format: YYYY-MM-DD HH:MM:SS. There is no silent local-time conversion.
- The MySQL server determines the authoritative current time.
- Prices display two decimals without assuming a currency.
- Clients, mech types, garages and technicians are maintained by the SQL scripts;
  dedicated editors for those entities were not part of the four required screens.
- Newly registered mechs start Available; procedures handle later state changes.
- A booking may return to another garage. Its return garage becomes the mech's
  current garage on completion. Future departures must match actual location.
- Stored procedures own their transactions. The connector uses autocommit=True
  and does not wrap procedure calls in an outer transaction.
- Database calls run in a background thread with a separate connection per call.
  Forms are temporarily disabled to avoid accidental duplicate submissions.
- If a connection is lost during a save, check the records before retrying:
  the server may have committed the change before the connection was lost.
- Connection settings/password stay in process memory; nothing is saved to disk.
  This is a local coursework app, not a deployed multi-user authentication system.

QUICK DEMO / LOCAL VERIFICATION
1. Connect. Fleet Registration should list four sample mechs after SQL file 04.
2. Register a unique chassis and confirm it appears in the fleet. Try a duplicate
   serial and a negative rate; confirm clear validation/database errors.
3. In Scheduling, select a sample client and an available mech. Use the UTC clock
   to choose a start 1-2 minutes ahead and a return at least one hour later.
4. Create the booking. Try an overlapping booking for the SAME mech and verify
   rejection. An exactly adjacent booking should be allowed.
5. Search that client's ID in Sponsor Manifests. Select the booking and cancel
   it; confirm Cancelled is recorded. A damaged mech must remain Unavailable.
6. Create another short booking. When its start arrives, select Start deployment.
   Wait at least a few seconds, then Complete with 0 combat hours for a brief
   classroom demo. Confirm Completed, final cost, actual timestamps and garage.
7. In Maintenance, report a Critical issue on an available mech. Confirm that
   booking it fails. Select the log, choose Repaired, assign a chief, enter notes
   and save. Confirm availability returns unless another failure remains.
8. Capture 4-6 real screenshots of the running screens and validation results.

TROUBLESHOOTING
- 'py/python is not recognized': install Python with Tcl/Tk support and reopen
  the terminal. On Windows, the normal python.org installer includes Tkinter.
- 'No module named mysql': run pip with the SAME interpreter used to launch.
- Test Tkinter installation: py -m tkinter (or python -m tkinter).
- Linux: use python3 instead of py; Tkinter may require the python3-tk OS package.
- Access denied: check the MySQL username/password and account permissions.
- Cannot connect: MySQL Workbench is a client; the separate MySQL SERVER service
  must be running. Check the port and host against your Workbench connection.
- Empty dropdowns: load SQL sample data (04) once, then Refresh.
- Missing tables/procedures: run the matching earlier SQL files 02/03.
- Each screen refreshes when you open its tab. A Refresh button is also provided.
- The existing SQL schema is required; do not substitute differently named columns.

AI DISCLOSURE (ALSO AT TOP OF main.py)
OpenAI ChatGPT generated the six Python modules, including the Tkinter layouts,
MySQL connection functions, input validation, parameterized SQL queries and
stored-procedure integration. The group is responsible for reviewing and testing
all generated code. Add an accurate account of your group's own modifications
and testing to your formal project documentation.

VERIFICATION PERFORMED WHILE CREATING THESE FILES
All six modules passed syntax compilation and import checks. 27 automated tests
passed for input validation, parameter binding, procedure output handling,
connection cleanup, UTC/autocommit configuration and error messages, using a
mock database connection. No MySQL server or graphical display was available
here, so the live windows and end-to-end MySQL workflow have NOT been verified.
Run the local checklist above before presenting or submitting the project.

SUBMISSION
Put all six source modules, the AI disclosure and 4-6 genuine running-system
screenshots in GX_GUI.pdf. Replace X with your group number. These development
files are not a substitute for that PDF or your actual in-class demonstration.

CONNECTOR REFERENCES
Connection arguments (including time_zone/autocommit/timeouts):
https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html
Result-set handling:
https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-nextset.html
