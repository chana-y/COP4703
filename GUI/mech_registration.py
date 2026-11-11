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
        names = ['Chassis serial', 'make', 'model', 'Assembly year', 'Armor color', 'Daily rate', 'Combat hours']
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
        columns = [('mech_id', 'ID', 65), ('chassis_serial', 'Chassis serial', 175), ('model', 'model', 120),
                   ('type_name', 'Type', 140), ('status', 'status', 115), ('daily_rate', 'Daily rate', 95),
                   ('combat_hours', 'Combat hours', 110), ('garage_name', 'Garage', 170)]
        frame, self.tree = app.table(panel, columns)
        frame.grid(row=1, column=0, sticky='nsew')
        self.contacts = tk.StringVar(value='Select a mech to see its garage pit crew.')
        ttk.Label(panel, textvariable=self.contacts, wraplength=540, justify='left').grid(row=2, column=0, sticky='w', pady=(12, 0))
        self.tree.bind('<<TreeviewSelect>>', app.guard(self.show_contacts))

    def refresh(self):
        self.app.run(self.app.db.lookups, self.loaded, 'Loading fleet and garages...')

    def loaded(self, data):
        self.data = data
        self.app.set_choices(self.mech_type, data['types'], 'mech_type_id', lambda r: f"{r['mech_type_id']} — {r['type_name']}")
        self.app.set_choices(self.garage, data['garages'], 'garage_id', lambda r: f"{r['garage_id']} — {r['garage_name']}")
        self.app.render(self.tree, data['mechs'], 'mech_id')
        self.contacts.set(f"{len(data['mechs'])} mechs. Select one to see garage contacts.")

    def show_contacts(self, _event=None):
        if not self.tree.selection():
            return
        selected = int(self.tree.selection()[0])
        mech = next(r for r in self.data['mechs'] if r['mech_id'] == selected)
        crew = [r for r in self.data['chiefs'] if r['garage_id'] == mech['garage_id']]
        details = '\n'.join(f"{r['full_name']} | {r['phone']} | {r['email']}" for r in crew)
        self.contacts.set(f"{mech['garage_name']} — pit crew\n{details or 'No technicians registered.'}")

    def save(self):
        get = lambda name: self.values[name].get()
        data = (
            required(get('Chassis serial'), 'Chassis serial', 50),
            required(get('make'), 'make', 50), required(get('model'), 'model', 50),
            positive_int(get('Assembly year'), 'Assembly year', 32767),
            required(get('Armor color'), 'Armor color', 30),
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
