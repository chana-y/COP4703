"""Screen 1: register mechs and inspect the fleet.
AI disclosure: OpenAI ChatGPT generated this module.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from database import required, positive_int, decimal_value


class MechRegistration(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.data = {}
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='Register a combat mech', style='Subheading.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        form = ttk.LabelFrame(self, text='New asset', padding=12)
        form.grid(row=1, column=0, sticky='ns', padx=(0, 18))
        names = ['Chassis serial', 'Make', 'Model', 'Assembly year', 'Armor color', 'Daily rate', 'Combat hours']
        self.values = {name: tk.StringVar(value='0.00' if name == 'Combat hours' else '') for name in names}
        for row, name in enumerate(names):
            app.field(form, row, name, self.values[name], width=22)
        self.mech_type = app.choice(form, 7, 'Mech type', width=24)
        self.garage = app.choice(form, 8, 'Garage', width=24)
        ttk.Button(form, text='Register mech', style='Accent.TButton', command=app.guard(self.save)).grid(row=9, column=0, columnspan=2, sticky='ew', pady=(12, 5))
        ttk.Label(form, text='All fields are required.\nNew assets start as Available.\nRates and hours: up to 2 decimals.', wraplength=300).grid(row=10, column=0, columnspan=2, sticky='w', pady=8)
        panel = ttk.Frame(self)
        panel.grid(row=1, column=1, sticky='nsew')
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        ttk.Button(panel, text='Refresh fleet & lists', command=self.refresh).grid(row=0, column=0, sticky='e', pady=(0, 8))
        columns = [('MechID', 'ID', 65), ('ChassisSerial', 'Chassis serial', 175), ('Model', 'Model', 120),
                   ('TypeName', 'Type', 140), ('OperationalStatus', 'Status', 115), ('DailyRate', 'Daily rate', 95),
                   ('CombatHours', 'Combat hours', 110), ('GarageName', 'Garage', 170)]
        frame, self.tree = app.table(panel, columns)
        frame.grid(row=1, column=0, sticky='nsew')
        self.contacts = tk.StringVar(value='Select a mech to see its garage pit crew.')
        ttk.Label(panel, textvariable=self.contacts, wraplength=540, justify='left').grid(row=2, column=0, sticky='w', pady=(12, 0))
        self.tree.bind('<<TreeviewSelect>>', app.guard(self.show_contacts))

    def refresh(self):
        self.app.run(self.app.db.lookups, self.loaded, 'Loading fleet and garages...')

    def loaded(self, data):
        self.data = data
        self.app.set_choices(self.mech_type, data['types'], 'MechTypeID', lambda r: f"{r['MechTypeID']} — {r['TypeName']}")
        self.app.set_choices(self.garage, data['garages'], 'GarageID', lambda r: f"{r['GarageID']} — {r['GarageName']}")
        self.app.render(self.tree, data['mechs'], 'MechID')
        self.contacts.set(f"{len(data['mechs'])} mechs. Select one to see garage contacts.")

    def show_contacts(self, _event=None):
        if not self.tree.selection():
            return
        selected = int(self.tree.selection()[0])
        mech = next(r for r in self.data['mechs'] if r['MechID'] == selected)
        crew = [r for r in self.data['chiefs'] if r['GarageID'] == mech['GarageID']]
        details = '\n'.join(f"{r['FullName']} | {r['Phone']} | {r['CorporateEmail']}" for r in crew)
        self.contacts.set(f"{mech['GarageName']} — pit crew\n{details or 'No technicians registered.'}")

    def save(self):
        get = lambda name: self.values[name].get()
        data = (
            required(get('Chassis serial'), 'Chassis serial', 80),
            required(get('Make'), 'Make', 80), required(get('Model'), 'Model', 80),
            positive_int(get('Assembly year'), 'Assembly year', 32767),
            required(get('Armor color'), 'Armor color', 50),
            decimal_value(get('Daily rate'), 'Daily rate'),
            decimal_value(get('Combat hours'), 'Combat hours', allow_zero=True),
            self.app.selected_id(self.mech_type, 'a mech type'), self.app.selected_id(self.garage, 'a garage'),
        )
        self.app.run(lambda: self.app.db.register_mech(data), self.saved, 'Registering mech...')

    def saved(self, mech_id):
        for key, variable in self.values.items():
            variable.set('0.00' if key == 'Combat hours' else '')
        messagebox.showinfo('Mech registered', f'Mech {mech_id} was saved successfully.', parent=self)
        self.refresh()
