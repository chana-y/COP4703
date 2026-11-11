"""MySQL access and validation for the existing mechwarx SQL scripts.
AI disclosure: OpenAI ChatGPT generated this module.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

try:
    import mysql.connector as connector
except ImportError:
    connector = None


class InputError(ValueError):
    """A validation error that can be shown directly to the user."""


class DatabaseError(RuntimeError):
    """A database error with a readable explanation."""


def required(value, label, max_length=255):
    value = str(value).strip()
    if not value:
        raise InputError(f'{label} is required.')
    if len(value) > max_length:
        raise InputError(f'{label} must be {max_length} characters or fewer.')
    return value


def positive_int(value, label, maximum=2147483647):
    try:
        number = int(str(value).strip())
    except ValueError:
        raise InputError(f'{label} must be a whole number.') from None
    if not 1 <= number <= maximum:
        raise InputError(f'{label} must be between 1 and {maximum}.')
    return number


def decimal_value(value, label, allow_zero=False):
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        raise InputError(f'{label} must be a number.') from None
    if not number.is_finite() or number < 0 or (number == 0 and not allow_zero):
        raise InputError(f'{label} must be {"zero or positive" if allow_zero else "positive"}.')
    if number > Decimal('99999999.99'):
        raise InputError(f'{label} exceeds the database limit.')
    if number != number.quantize(Decimal('0.01')):
        raise InputError(f'{label} can have at most two decimal places.')
    return number.quantize(Decimal('0.01'))


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def parse_time(value, label):
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise InputError(f'{label}: use YYYY-MM-DD HH:MM:SS in UTC.') from None


def validate_window(start, end):
    if start <= utc_now():
        raise InputError('Scheduled start must be in the future (UTC).')
    if end <= start:
        raise InputError('Scheduled return must be after scheduled start.')


def text_value(value, label, mandatory=True):
    value = value.strip()
    if mandatory and not value:
        raise InputError(f'{label} is required.')
    if len(value.encode('utf-8')) > 65535:
        raise InputError(f'{label} is too long for a MySQL TEXT field.')
    return value or None


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    database: str = 'mechwarx'


# Procedure names are fixed in code; no user input is interpolated into SQL.
PROCEDURES = {
    'sp_BookDeployment': (6, True),
    'sp_CancelDeployment': (1, False),
    'sp_ReportMaintenance': (5, True),
    'sp_UpdateMaintenance': (4, False),
    'sp_StartDeployment': (1, False),
    'sp_CompleteDeployment': (2, False),
}


class Database:
    def __init__(self, config):
        self.config = config

    @contextmanager
    def cursor(self):
        if connector is None:
            raise DatabaseError('Install the dependency first:\npython -m pip install -r requirements.txt')
        connection = None
        cursor = None
        try:
            connection = connector.connect(
                host=self.config.host, port=self.config.port, user=self.config.user,
                password=self.config.password, database=self.config.database,
                autocommit=True, time_zone='+00:00', charset='utf8mb4',
                connection_timeout=8, read_timeout=15, write_timeout=15,
            )
            cursor = connection.cursor(dictionary=True, buffered=True)
            yield cursor
        except connector.Error as exc:
            if exc.sqlstate == '45000':
                message = exc.msg
            elif exc.errno == 1062:
                message = 'That chassis serial or another unique value already exists.'
            elif exc.errno == 1045:
                message = 'MySQL rejected the username/password. Use your MySQL login, not your Windows login.'
            elif exc.errno == 1049:
                message = 'Database not found. Run your schema and backend.sql and verify the database name.'
            elif exc.errno in (1146, 1305):
                message = 'A required table or stored procedure is missing. Run your schema and backend.sql.'
            elif exc.errno in (1451, 1452):
                message = 'A linked record is missing or in use. Refresh the screen and try again.'
            elif exc.errno in (1205, 1213):
                message = 'Another operation is using these records. Refresh and retry after it finishes.'
            elif exc.errno in (2002, 2003, 2006, 2013, 3024) or 'timeout' in type(exc).__name__.lower():
                message = ('MySQL is unreachable or the connection timed out. Check the server and connection settings. '
                           'If this happened while saving, refresh and check the records before retrying; '
                           'the server may already have saved the change.')
            else:
                message = f'MySQL error {exc.errno}: {exc.msg}'
            raise DatabaseError(message) from None
        finally:
            # Closing a failed connection must not hide the original error.
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def query(self, sql, params=()):
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def check_setup(self):
        with self.cursor() as cur:
            cur.execute('SELECT VERSION() AS version, @@lower_case_table_names AS name_mode')
            server = cur.fetchone()
            version = server['version']
            # Match the server's table-name rules (Windows normally uses mode 1).
            normalize = str.casefold if int(server['name_mode']) else (lambda name: name)
            cur.execute('SELECT TABLE_NAME AS name FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()')
            tables = {normalize(r['name']) for r in cur.fetchall()}
            needed = {'MechType', 'Garage', 'Staff', 'Client', 'Mech',
                      'DeploymentManifest', 'MaintenanceLog'}
            missing = sorted(name for name in needed if normalize(name) not in tables)
            if missing:
                raise DatabaseError('Missing tables: ' + ', '.join(missing) +
                                    '. Run your supplied CREATE TABLE statements, then refresh Workbench.')
            expected = {
                'MechType': 'mech_type_id,type_name',
                'Garage': 'garage_id,garage_name,grid_address,dispatch_phone',
                'Staff': 'staff_id,garage_id,full_name,phone,email',
                'Client': 'client_id,first_name,last_name,corporate_address,phone,email,license_token,license_expiry',
                'Mech': 'mech_id,chassis_serial,make,model,assembly_year,armor_color,daily_rate,combat_hours,status,mech_type_id,garage_id',
                'DeploymentManifest': 'serial_id,client_id,mech_id,deploy_garage_id,return_garage_id,scheduled_start,scheduled_end,actual_start,actual_end,estimated_cost,actual_cost,status',
                'MaintenanceLog': 'log_id,mech_id,client_id,staff_id,reported_at,issue_type,damage_description,status,resolved_at,engineering_notes',
            }
            for table, columns in expected.items():
                # Identifiers are constants defined above, never user input.
                cur.execute(f'SELECT {columns} FROM {table} LIMIT 0')
                cur.fetchall()
            cur.execute('SELECT TRIGGER_NAME AS name FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()')
            triggers = {r['name'].casefold() for r in cur.fetchall()}
            if {'trg_manifest_cancelled', 'trg_incident_created', 'trg_incident_updated'} - triggers:
                raise DatabaseError('Required triggers are missing or not visible. Run backend.sql.')
            cur.execute('SELECT ROUTINE_NAME AS name FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE()')
            routines = {r['name'].casefold() for r in cur.fetchall()}
            if {name.casefold() for name in PROCEDURES} - routines:
                raise DatabaseError('Required procedures are missing or not visible to this user. Run backend.sql or check EXECUTE permissions.')
            return version

    def lookups(self):
        """Load database IDs and readable labels for dropdowns."""
        queries = {
            'types': 'SELECT mech_type_id, type_name FROM MechType ORDER BY type_name',
            'garages': 'SELECT garage_id, garage_name FROM Garage ORDER BY garage_name',
            'clients': 'SELECT client_id, first_name, last_name, license_expiry FROM Client ORDER BY last_name,first_name',
            'chiefs': '''SELECT t.staff_id,t.garage_id,t.full_name,t.phone,t.email,g.garage_name
                         FROM Staff t JOIN Garage g ON g.garage_id=t.garage_id
                         ORDER BY t.full_name''',
            'mechs': '''SELECT m.mech_id,m.chassis_serial,m.model,m.daily_rate,m.combat_hours,
                        m.status,m.garage_id,g.garage_name,t.type_name
                        FROM Mech m JOIN Garage g ON g.garage_id=m.garage_id
                        JOIN MechType t ON t.mech_type_id=m.mech_type_id ORDER BY m.mech_id''',
        }
        with self.cursor() as cur:
            result = {}
            for key, sql in queries.items():
                cur.execute(sql)
                result[key] = cur.fetchall()
            return result

    def register_mech(self, data):
        sql = '''INSERT INTO Mech
                 (chassis_serial,make,model,assembly_year,armor_color,daily_rate,combat_hours,mech_type_id,garage_id)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
        with self.cursor() as cur:
            cur.execute(sql, data)
            return cur.lastrowid

    def manifests(self, client_id):
        client = self.query('SELECT client_id,first_name,last_name FROM Client WHERE client_id=%s', (client_id,))
        if not client:
            raise InputError('No client exists with that ID.')
        rows = self.query('''SELECT d.*,m.chassis_serial,g1.garage_name AS DepartureGarage,
                            g2.garage_name AS ReturnGarage
                            FROM DeploymentManifest d JOIN Mech m ON m.mech_id=d.mech_id
                            JOIN Garage g1 ON g1.garage_id=d.deploy_garage_id
                            JOIN Garage g2 ON g2.garage_id=d.return_garage_id
                            WHERE d.client_id=%s ORDER BY d.scheduled_start DESC,d.serial_id DESC''', (client_id,))
        return client[0], rows

    def schedule(self, mech_id):
        return self.query('''SELECT serial_id,client_id,scheduled_start,scheduled_end,status
                             FROM DeploymentManifest WHERE mech_id=%s
                             AND status IN ('Match Booked','Active in Arena')
                             ORDER BY scheduled_start''', (mech_id,))

    def incidents(self, show_repaired=False):
        sql = '''SELECT l.*,m.chassis_serial,t.full_name AS ChiefName
                 FROM MaintenanceLog l JOIN Mech m ON m.mech_id=l.mech_id
                 LEFT JOIN Staff t ON t.staff_id=l.staff_id'''
        if not show_repaired:
            sql += " WHERE l.status <> 'Repaired'"
        return self.query(sql + ' ORDER BY l.reported_at DESC,l.log_id DESC')

    def call(self, name, args):
        if name not in PROCEDURES:
            raise ValueError('Unknown procedure.')
        count, has_output = PROCEDURES[name]
        if len(args) != count:
            raise ValueError('Incorrect procedure argument count.')
        placeholders = ['%s'] * count
        with self.cursor() as cur:
            if has_output:
                cur.execute('SET @mechwar_output = NULL')
                placeholders.append('@mechwar_output')
            # autocommit=True: the stored procedure owns START TRANSACTION/COMMIT.
            cur.execute(f'CALL {name}({", ".join(placeholders)})', tuple(args))
            while True:
                if cur.with_rows:
                    cur.fetchall()
                if not cur.nextset():
                    break
            if has_output:
                cur.execute('SELECT @mechwar_output AS record_id')
                return cur.fetchone()['record_id']
            return None
