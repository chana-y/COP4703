"""Screen 2: search by ClientID and manage deployment lifecycle.
AI disclosure: OpenAI ChatGPT generated this module.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database import positive_int, decimal_value, InputError


class ManifestDashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.rows = {}
        self.client_id = tk.StringVar()
        self.heading = tk.StringVar(value='Enter a ClientID, or choose a client from the list.')
        self.details = tk.StringVar(value='Select a manifest to inspect its deployment details.')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky='ew')
        ttk.Label(toolbar, text='Client ID').pack(side='left')
        entry = ttk.Entry(toolbar, textvariable=self.client_id, width=10)
        entry.pack(side='left', padx=8)
        entry.bind('<Return>', app.guard(lambda _event: self.search()))
        ttk.Button(toolbar, text='Search manifests', style='Accent.TButton', command=app.guard(self.search)).pack(side='left', padx=(0, 12))
        self.client_choice = ttk.Combobox(toolbar, width=36, state='readonly')
        self.client_choice.record_ids = {}
        self.client_choice.pack(side='left', fill='x', expand=True)
        self.client_choice.bind('<<ComboboxSelected>>', app.guard(self.pick_client))
        ttk.Button(toolbar, text='Refresh', command=self.refresh).pack(side='right', padx=(12, 0))
        ttk.Label(self, textvariable=self.heading, style='Subheading.TLabel').grid(row=1, column=0, sticky='w', pady=12)
        columns = [('SerialID', 'Manifest', 85), ('ChassisSerial', 'Chassis serial', 170), ('Status', 'Status', 135),
                   ('ScheduledStart', 'Scheduled start (UTC)', 170), ('ScheduledReturn', 'Scheduled return (UTC)', 175),
                   ('EstimatedCost', 'Estimated cost', 115), ('FinalCost', 'Final cost', 100)]
        frame, self.tree = app.table(self, columns)
        frame.grid(row=2, column=0, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', app.guard(self.select))
        ttk.Label(self, textvariable=self.details, wraplength=1050, justify='left').grid(row=3, column=0, sticky='w', pady=12)
        actions = ttk.Frame(self)
        actions.grid(row=4, column=0, sticky='w')
        for label, command in [('Cancel booking', self.cancel), ('Start deployment', self.start), ('Complete deployment', self.complete)]:
            ttk.Button(actions, text=label, command=app.guard(command)).pack(side='left', padx=(0, 10))
        ttk.Label(self, text='Start is allowed only during the reserved window, with the mech at its departure garage.').grid(row=5, column=0, sticky='w', pady=(12, 0))

    def refresh(self):
        query_id = None
        text = self.client_id.get().strip()
        if text:
            try:
                query_id = positive_int(text, 'Client ID')
            except InputError:
                pass
        def work():
            choices = self.app.db.lookups()['clients']
            result = self.app.db.manifests(query_id) if query_id is not None else None
            return choices, result
        def loaded(result):
            choices, manifests = result
            self.app.set_choices(self.client_choice, choices, 'ClientID', lambda r: f"{r['ClientID']} — {r['FirstName']} {r['LastName']}")
            if manifests is not None:
                self.show(manifests)
        self.app.run(work, loaded, 'Loading clients and manifests...')

    def pick_client(self, _event=None):
        client_id = self.app.selected_id(self.client_choice, 'a client')
        self.client_id.set(str(client_id))
        self.search()

    def search(self):
        client_id = positive_int(self.client_id.get(), 'Client ID')
        # Clear old results so a failed search never displays another client's data.
        self.rows.clear()
        self.app.render(self.tree, [], 'SerialID')
        self.heading.set(f'Searching client {client_id}...')
        self.details.set('')
        self.app.run(lambda: self.app.db.manifests(client_id), self.show, 'Searching manifests...')

    def show(self, result):
        client, rows = result
        self.rows = {r['SerialID']: r for r in rows}
        self.app.render(self.tree, rows, 'SerialID')
        self.app.select_id(self.client_choice, client['ClientID'])
        self.heading.set(f"{client['FirstName']} {client['LastName']} — {len(rows)} manifest(s)")
        self.details.set('Select a manifest for details.' if rows else 'This client has no deployment manifests.')

    def select(self, _event=None):
        if not self.tree.selection():
            return
        row = self.app.selected_row(self.tree, self.rows)
        fmt = self.app.display
        self.details.set(
            f"Departure: {row['DepartureGarage']}   |   Return: {row['ReturnGarage']}\n"
            f"Actual start (UTC): {fmt(row['ActualStart'])}   |   Actual return (UTC): {fmt(row['ActualReturn'])}\n"
            f"Booked daily rate: {fmt(row['BookedDailyRate'])}   |   Combat hours used: {fmt(row['CombatHoursUsed'])}"
        )

    def chosen(self, required_status):
        row = self.app.selected_row(self.tree, self.rows)
        if row['Status'] != required_status:
            raise InputError(f'This action requires status: {required_status}. Refresh if the record changed.')
        return row['SerialID']

    def cancel(self):
        serial = self.chosen('Match Booked')
        if messagebox.askyesno('Cancel booking', f'Cancel manifest {serial}? Its record will be retained.', parent=self):
            self.action('sp_CancelDeployment', (serial,), 'Booking cancelled.')

    def start(self):
        serial = self.chosen('Match Booked')
        if messagebox.askyesno('Start deployment', f'Start manifest {serial} now?', parent=self):
            self.action('sp_StartDeployment', (serial,), 'Deployment started.')

    def complete(self):
        serial = self.chosen('Active in Arena')
        value = simpledialog.askstring('Complete deployment',
            'Enter actual combat hours used (up to 2 decimals).\nUse 0 for a brief demonstration with no combat.\nHours cannot exceed elapsed deployment time.', parent=self)
        if value is None:
            return
        hours = decimal_value(value, 'Combat hours', allow_zero=True)
        self.action('sp_CompleteDeployment', (serial, hours), 'Deployment completed; final cost, combat hours and return garage updated.')

    def action(self, procedure, args, message):
        def done(_result):
            messagebox.showinfo('Saved', message, parent=self)
            self.search()
        self.app.run(lambda: self.app.db.call(procedure, args), done, 'Updating manifest...')
