"""Screen 3: reserve a mech using sp_BookDeployment.
AI disclosure: OpenAI ChatGPT generated this module.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import timedelta
from decimal import Decimal
from database import parse_time, validate_window, utc_now


class BookingScreen(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.data = {}
        self.preview = tk.StringVar(value='Choose a mech and enter a future match window.')
        self.start_time = tk.StringVar(value=(utc_now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'))
        self.return_time = tk.StringVar(value=(utc_now() + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='Reserve a deployment window', style='Subheading.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        form = ttk.LabelFrame(self, text='New manifest', padding=12)
        form.grid(row=1, column=0, sticky='ns', padx=(0, 18))
        self.client = app.choice(form, 0, 'Client', width=35)
        self.mech = app.choice(form, 1, 'Mech', width=35)
        self.mech.bind('<<ComboboxSelected>>', app.guard(self.mech_changed))
        app.field(form, 2, 'Start (UTC)', self.start_time)
        app.field(form, 3, 'Return (UTC)', self.return_time)
        self.departure = app.choice(form, 4, 'Departure garage', width=35)
        self.return_garage = app.choice(form, 5, 'Return garage', width=35)
        ttk.Label(form, text='Format: YYYY-MM-DD HH:MM:SS\nUse the UTC clock at the bottom of the app.').grid(row=6, column=0, columnspan=2, sticky='w', pady=10)
        ttk.Button(form, text='Preview estimated cost', command=app.guard(self.estimate)).grid(row=7, column=0, columnspan=2, sticky='ew', pady=5)
        ttk.Button(form, text='Create booking', style='Accent.TButton', command=app.guard(self.book)).grid(row=8, column=0, columnspan=2, sticky='ew', pady=5)
        ttk.Label(form, textvariable=self.preview, wraplength=420, justify='left').grid(row=9, column=0, columnspan=2, sticky='w', pady=12)
        panel = ttk.Frame(self)
        panel.grid(row=1, column=1, sticky='nsew')
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        ttk.Button(panel, text='Refresh lists & schedule', command=self.refresh).grid(row=0, column=0, sticky='e')
        ttk.Label(panel, text='Selected mech: open reservations').grid(row=1, column=0, sticky='w', pady=10)
        cols = [('SerialID', 'Manifest', 85), ('ClientID', 'Client', 70), ('ScheduledStart', 'Start (UTC)', 170),
                ('ScheduledReturn', 'Return (UTC)', 170), ('Status', 'Status', 135)]
        frame, self.tree = app.table(panel, cols)
        frame.grid(row=2, column=0, sticky='nsew')
        ttk.Label(panel, text='The database performs the final conflict check.\nAdjacent bookings are allowed; overlapping ones are rejected.\nUnavailable or currently deployed mechs cannot be booked.',
                  wraplength=430, justify='left').grid(row=3, column=0, sticky='w', pady=12)

    def refresh(self):
        self.app.run(self.app.db.lookups, self.loaded, 'Loading scheduling options...')

    def loaded(self, data):
        self.data = data
        app = self.app
        app.set_choices(self.client, data['clients'], 'ClientID', lambda r: f"{r['ClientID']} — {r['FirstName']} {r['LastName']}")
        app.set_choices(self.mech, data['mechs'], 'MechID', lambda r: f"{r['MechID']} — {r['ChassisSerial']} ({r['OperationalStatus']})")
        for combo in (self.departure, self.return_garage):
            app.set_choices(combo, data['garages'], 'GarageID', lambda r: f"{r['GarageID']} — {r['GarageName']}")
        if data['mechs']:
            self.mech_changed()
        else:
            app.render(self.tree, [], 'SerialID')
            self.preview.set('No mechs found. Register a mech or run SQL sample data first.')

    def mech_changed(self, _event=None):
        mech_id = self.app.selected_id(self.mech, 'a mech')
        mech = next(r for r in self.data['mechs'] if r['MechID'] == mech_id)
        self.app.select_id(self.departure, mech['GarageID'])
        self.preview.set(f"Current garage: {mech['GarageName']}\nDaily rate: {mech['DailyRate']:.2f} | Status: {mech['OperationalStatus']}")
        self.app.render(self.tree, [], 'SerialID')
        self.app.run(lambda: self.app.db.schedule(mech_id), lambda rows: self.app.render(self.tree, rows, 'SerialID'), 'Loading selected mech schedule...')

    def window(self):
        start = parse_time(self.start_time.get(), 'Start')
        end = parse_time(self.return_time.get(), 'Return')
        validate_window(start, end)
        return start, end

    def estimate(self):
        start, end = self.window()
        mech_id = self.app.selected_id(self.mech, 'a mech')
        mech = next(r for r in self.data['mechs'] if r['MechID'] == mech_id)
        seconds = int((end - start).total_seconds())
        days = max(1, (seconds + 86399) // 86400)
        amount = Decimal(str(mech['DailyRate'])) * days
        self.preview.set(f'Estimate: {amount:.2f}\n{days} commenced 24-hour day(s).\nThe database confirms the rate and availability when saved.')

    def book(self):
        start, end = self.window()
        args = (self.app.selected_id(self.client, 'a client'), self.app.selected_id(self.mech, 'a mech'),
                start, end, self.app.selected_id(self.departure, 'a departure garage'),
                self.app.selected_id(self.return_garage, 'a return garage'))
        def saved(serial):
            messagebox.showinfo('Booking created', f'Manifest {serial} was saved.\nSearch Client ID {args[0]} in Sponsor Manifests to manage it.', parent=self)
            self.refresh()
        self.app.run(lambda: self.app.db.call('sp_BookDeployment', args), saved, 'Checking conflicts and creating booking...')
