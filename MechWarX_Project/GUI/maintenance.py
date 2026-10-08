"""Screen 4: report, inspect and resolve maintenance incidents.
AI disclosure: OpenAI ChatGPT generated this module.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from database import text_value, InputError


class MaintenanceScreen(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.rows = {}
        self.data = {}
        self.selected_log = None
        self.show_repaired = tk.BooleanVar(value=False)
        self.detail = tk.StringVar(value='Select a log in the table below.')
        self.contact = tk.StringVar(value='Select a pit-crew chief to see contact details.')
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        ttk.Label(toolbar, text='Incident Command & Diagnostics', style='Subheading.TLabel').pack(side='left')
        ttk.Button(toolbar, text='Refresh', command=self.refresh).pack(side='right')
        ttk.Checkbutton(toolbar, text='Include repaired', variable=self.show_repaired, command=self.refresh).pack(side='right', padx=15)
        report = ttk.LabelFrame(self, text='Report a new incident', padding=10)
        report.grid(row=1, column=0, sticky='nsew', padx=(0, 12))
        report.columnconfigure(1, weight=1)
        self.mech = app.choice(report, 0, 'Mech', width=29)
        self.client = app.choice(report, 1, 'Reporting client', width=29)
        self.issue_type = app.choice(report, 2, 'Issue type', width=29)
        self.issue_type.configure(values=['Routine', 'Critical'])
        self.issue_type.set('Routine')
        self.new_chief = app.choice(report, 3, 'Pit-crew chief', width=29)
        ttk.Label(report, text='Damage description').grid(row=4, column=0, sticky='nw', pady=5)
        self.description = tk.Text(report, height=3, width=30, wrap='word', font=('Segoe UI', 10))
        self.description.grid(row=4, column=1, sticky='ew', pady=5)
        ttk.Button(report, text='Report incident', style='Accent.TButton', command=app.guard(self.report)).grid(row=5, column=0, columnspan=2, sticky='ew', pady=(5, 0))
        edit = ttk.LabelFrame(self, text='Update selected incident', padding=10)
        edit.grid(row=1, column=1, sticky='nsew')
        edit.columnconfigure(1, weight=1)
        ttk.Label(edit, textvariable=self.detail, wraplength=440, justify='left').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 5))
        self.status_choice = app.choice(edit, 1, 'Status', width=27)
        self.status_choice.configure(values=['Reported', 'In-Progress', 'Awaiting Parts', 'Repaired'])
        self.status_choice.set('In-Progress')
        self.chief = app.choice(edit, 2, 'Pit-crew chief', width=27)
        self.chief.bind('<<ComboboxSelected>>', app.guard(self.show_contact))
        ttk.Label(edit, text='Engineering notes').grid(row=3, column=0, sticky='nw', pady=5)
        self.notes = tk.Text(edit, height=3, width=30, wrap='word', font=('Segoe UI', 10))
        self.notes.grid(row=3, column=1, sticky='ew', pady=5)
        ttk.Button(edit, text='Save status / repair', style='Accent.TButton', command=app.guard(self.update_log)).grid(row=4, column=0, columnspan=2, sticky='ew', pady=(5, 0))
        ttk.Label(self, textvariable=self.contact, wraplength=1050).grid(row=2, column=0, columnspan=2, sticky='w', pady=10)
        columns = [('LogID', 'Log', 65), ('ChassisSerial', 'Chassis serial', 165), ('IssueType', 'Type', 80),
                   ('Status', 'Status', 115), ('Description', 'Description', 260), ('ReportedAt', 'Reported (UTC)', 165),
                   ('ChiefName', 'Pit-crew chief', 135), ('ResolvedAt', 'Resolved (UTC)', 165)]
        frame, self.tree = app.table(self, columns, height=6)
        frame.grid(row=3, column=0, columnspan=2, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', app.guard(self.select))
        ttk.Button(self, text='View full selected log', command=app.guard(self.view_details)).grid(row=4, column=0, columnspan=2, sticky='w', pady=(8, 0))

    def refresh(self):
        include = self.show_repaired.get()
        def work():
            return self.app.db.lookups(), self.app.db.incidents(include)
        self.app.run(work, self.loaded, 'Loading maintenance records...')

    def loaded(self, result):
        data, logs = result
        self.data = data
        self.rows = {r['LogID']: r for r in logs}
        app = self.app
        app.set_choices(self.mech, data['mechs'], 'MechID', lambda r: f"{r['MechID']} — {r['ChassisSerial']}")
        app.set_choices(self.client, data['clients'], 'ClientID', lambda r: f"{r['ClientID']} — {r['FirstName']} {r['LastName']}", optional=True)
        for combo in (self.chief, self.new_chief):
            app.set_choices(combo, data['chiefs'], 'StaffID', lambda r: f"{r['StaffID']} — {r['FullName']}", optional=True)
        app.render(self.tree, logs, 'LogID')
        self.selected_log = None
        self.detail.set(f'{len(logs)} incident(s). Select a row below to update it.')
        self.notes.delete('1.0', 'end')
        self.contact.set('Select a pit-crew chief to see contact details.')

    def select(self, _event=None):
        if not self.tree.selection():
            return
        row = self.app.selected_row(self.tree, self.rows)
        self.selected_log = row['LogID']
        self.detail.set(f"Log {row['LogID']} | {row['ChassisSerial']} | {row['IssueType']}\nReported (UTC): {self.app.display(row['ReportedAt'])}")
        self.status_choice.set(row['Status'])
        self.app.select_id(self.chief, row['PitCrewChiefID'])
        self.notes.delete('1.0', 'end')
        self.notes.insert('1.0', row['EngineeringNotes'] or '')
        self.show_contact()

    def show_contact(self, _event=None):
        chief_id = self.app.selected_id(self.chief, 'a pit-crew chief', optional=True)
        chief = next((r for r in self.data.get('chiefs', []) if r['StaffID'] == chief_id), None)
        if chief:
            self.contact.set(f"{chief['FullName']} | {chief['GarageName']} | {chief['Phone']} | {chief['CorporateEmail']}")
        else:
            self.contact.set('No pit-crew chief assigned. A chief and notes are required to mark an incident Repaired.')

    def report(self):
        description = text_value(self.description.get('1.0', 'end-1c'), 'Damage description')
        args = (self.app.selected_id(self.mech, 'a mech'),
                self.app.selected_id(self.client, 'a reporting client', optional=True), self.issue_type.get(),
                description, self.app.selected_id(self.new_chief, 'a pit-crew chief', optional=True))
        def saved(log_id):
            self.description.delete('1.0', 'end')
            message = f'Incident {log_id} was saved.'
            if args[2] == 'Critical':
                message += '\nThe database marked the mech Unavailable.'
            messagebox.showinfo('Incident reported', message, parent=self)
            self.refresh()
        self.app.run(lambda: self.app.db.call('sp_ReportMaintenance', args), saved, 'Recording maintenance incident...')

    def update_log(self):
        row = self.app.selected_row(self.tree, self.rows)
        if row['Status'] == 'Repaired':
            raise InputError('This incident is closed. Report a new incident for a new failure.')
        status = self.status_choice.get()
        chief = self.app.selected_id(self.chief, 'a pit-crew chief', optional=True)
        notes = text_value(self.notes.get('1.0', 'end-1c'), 'Engineering notes', mandatory=(status == 'Repaired'))
        if status == 'Repaired' and chief is None:
            raise InputError('Assign a pit-crew chief before marking the incident Repaired.')
        args = (row['LogID'], status, chief, notes)
        def saved(_result):
            messagebox.showinfo('Maintenance updated', 'The log was updated and mech availability recalculated.', parent=self)
            self.refresh()
        self.app.run(lambda: self.app.db.call('sp_UpdateMaintenance', args), saved, 'Updating maintenance status...')

    def view_details(self):
        row = self.app.selected_row(self.tree, self.rows)
        dialog = tk.Toplevel(self)
        dialog.title(f"Maintenance log {row['LogID']}")
        dialog.geometry('700x460')
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        text = tk.Text(dialog, wrap='word', font=('Segoe UI', 11), padx=14, pady=14)
        scroll = ttk.Scrollbar(dialog, orient='vertical', command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        text.pack(fill='both', expand=True)
        text.insert('1.0', '\n'.join(f'{key}: {self.app.display(value)}' for key, value in row.items()))
        text.configure(state='disabled')
        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=8)
