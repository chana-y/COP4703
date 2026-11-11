# AI DISCLOSURE
# Tool: OpenAI ChatGPT.
# AI generated main.py, database.py, mech_registration.py,
# manifest_dashboard.py, booking.py and maintenance.py, including the Tkinter
# layouts, MySQL connection code, validation and stored-procedure integration.
# The group is responsible for reviewing and testing these files before use.
"""Run this file: python main.py. All six Python files must share one folder."""
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal

from database import DBConfig, Database, DatabaseError, InputError, positive_int, required, utc_now


class MechWarXApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('MechWar-X | Arena & Garage Management')
        self.geometry('1220x800')
        self.minsize(1000, 700)
        self.configure(background='#edf2f7')
        self.db = None
        self.busy = False
        self.results = queue.Queue()
        self.disabled = []
        self.active_tab = None
        self.pages = []
        self.notebook = None
        self.status = tk.StringVar(value='Connect to your MySQL database to begin.')
        self.clock = tk.StringVar()
        self._style()
        self.body = ttk.Frame(self, padding=22)
        self.body.pack(fill='both', expand=True)
        footer = ttk.Frame(self, padding=(22, 8))
        footer.pack(fill='x')
        ttk.Label(footer, textvariable=self.status).pack(side='left')
        ttk.Label(footer, textvariable=self.clock).pack(side='right')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self._login()
        self.after(100, self._poll)
        self._tick()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('TFrame', background='#edf2f7')
        style.configure('TLabel', background='#edf2f7', foreground='#203247')
        style.configure('Heading.TLabel', font=('Segoe UI', 21, 'bold'))
        style.configure('Subheading.TLabel', font=('Segoe UI', 13, 'bold'))
        style.configure('TButton', padding=(12, 7))
        style.configure('Accent.TButton', background='#1f5d86', foreground='white')
        style.map('Accent.TButton', background=[('active', '#164765'), ('disabled', '#8298a8')])
        style.configure('Treeview', rowheight=29, background='white', fieldbackground='white')
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), padding=6)
        style.configure('TNotebook.Tab', padding=(16, 10))
        style.configure('TLabelframe', background='#edf2f7')
        style.configure('TLabelframe.Label', background='#edf2f7', font=('Segoe UI', 11, 'bold'))

    def _tick(self):
        self.clock.set(utc_now().strftime('UTC  %Y-%m-%d %H:%M:%S'))
        self.after(1000, self._tick)

    def _login(self):
        panel = ttk.Frame(self.body, padding=30)
        panel.place(relx=.5, rely=.45, anchor='center')
        self.login_panel = panel
        ttk.Label(panel, text='MECHWAR-X', style='Heading.TLabel').grid(row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(panel, text='Connect to your arena database', style='Subheading.TLabel').grid(row=1, column=0, columnspan=2, sticky='w', pady=(4, 20))
        self.login = {}
        defaults = [('Host', os.getenv('MECHWAR_DB_HOST', '127.0.0.1')),
                    ('Port', os.getenv('MECHWAR_DB_PORT', '3306')),
                    ('Username', os.getenv('MECHWAR_DB_USER', 'root')),
                    ('Password', ''), ('Database', os.getenv('MECHWAR_DB_NAME', 'mechwarx'))]
        for i, (label, value) in enumerate(defaults, 2):
            self.login[label] = tk.StringVar(value=value)
            self.field(panel, i, label, self.login[label], show='*' if label == 'Password' else '')
        ttk.Label(panel, text='Use the same MySQL login as Workbench.\nRun your schema, then backend.sql first. Password is kept only in memory.',
                  wraplength=460).grid(row=7, column=0, columnspan=2, sticky='w', pady=14)
        ttk.Button(panel, text='Connect', style='Accent.TButton', command=self.guard(self.connect)).grid(row=8, column=0, columnspan=2, sticky='ew')

    def connect(self):
        config = DBConfig(required(self.login['Host'].get(), 'Host'),
                          positive_int(self.login['Port'].get(), 'Port', 65535),
                          required(self.login['Username'].get(), 'Username'),
                          self.login['Password'].get(), required(self.login['Database'].get(), 'Database'))
        db = Database(config)
        self.run(db.check_setup, lambda version: self._connected(db, version), 'Connecting to MySQL...')

    def _connected(self, db, version):
        self.db = db
        self.login['Password'].set('')
        self.login_panel.destroy()
        ttk.Label(self.body, text='MECHWAR-X', style='Heading.TLabel').pack(anchor='w')
        ttk.Label(self.body, text=f'Arena operations  |  {db.config.database}  |  All dates and times are UTC').pack(anchor='w', pady=(2, 16))
        self.notebook = ttk.Notebook(self.body)
        self.notebook.pack(fill='both', expand=True)
        from mech_registration import MechRegistration
        from manifest_dashboard import ManifestDashboard
        from booking import BookingScreen
        from maintenance import MaintenanceScreen
        for cls, label in [(MechRegistration, '1  Fleet Registration'),
                           (ManifestDashboard, '2  Sponsor Manifests'),
                           (BookingScreen, '3  Hangar Scheduling'),
                           (MaintenanceScreen, '4  Maintenance')]:
            page = cls(self.notebook, self)
            self.pages.append(page)
            self.notebook.add(page, text=label)
        self.notebook.bind('<<NotebookTabChanged>>', self._tab_changed)
        self.notebook.bind('<Button-1>', lambda event: 'break' if self.busy else None)
        self.notebook.bind('<KeyPress>', lambda event: 'break' if self.busy else None)
        self.status.set(f'Connected to MySQL {version}.')
        self.pages[0].refresh()

    def _tab_changed(self, _event):
        if self.busy:
            if self.active_tab and self.notebook.select() != self.active_tab:
                self.notebook.select(self.active_tab)
            return
        if self.pages and self.notebook.select():
            self.pages[self.notebook.index('current')].refresh()

    def guard(self, function):
        def callback(*args):
            if self.busy:
                return
            try:
                return function(*args)
            except (InputError, DatabaseError) as exc:
                messagebox.showerror('Please check', str(exc), parent=self)
        return callback

    def run(self, work, on_success, status='Loading...'):
        """Run DB work off the UI thread; all Tk calls stay on the main thread."""
        if self.busy:
            return
        self.busy = True
        self.status.set(status)
        self._disable(self.body)
        if self.notebook is not None:
            self.active_tab = self.notebook.select()
        def worker():
            try:
                self.results.put((True, work(), on_success))
            except Exception as exc:
                self.results.put((False, exc, on_success))
        threading.Thread(target=worker, daemon=True).start()

    def _disable(self, parent):
        for widget in parent.winfo_children():
            if isinstance(widget, (ttk.Button, ttk.Entry, ttk.Combobox, ttk.Checkbutton, ttk.Treeview)):
                self.disabled.append((widget, widget.state()))
                widget.state(['disabled'])
            elif isinstance(widget, tk.Text):
                self.disabled.append((widget, widget.cget('state')))
                widget.configure(state='disabled')
            self._disable(widget)

    def _restore(self):
        for widget, state in self.disabled:
            if widget.winfo_exists():
                if isinstance(widget, tk.Text):
                    widget.configure(state=state)
                else:
                    widget.state(['!disabled'])
                    widget.state(state)
        self.disabled.clear()
        self.active_tab = None

    def _poll(self):
        try:
            ok, value, callback = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self._restore()
            self.busy = False
            if ok:
                self.status.set('Ready.')
                try:
                    callback(value)
                except (InputError, DatabaseError) as exc:
                    messagebox.showerror('Please check', str(exc), parent=self)
            else:
                self.status.set('Operation did not finish successfully. See the message.')
                messagebox.showerror('Operation unsuccessful', str(value), parent=self)
        self.after(100, self._poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('Operation in progress', 'Wait for the database operation to finish before closing.', parent=self)
            return
        self.destroy()

    def field(self, parent, row, label, variable, width=30, show=''):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=(0, 12), pady=5)
        entry = ttk.Entry(parent, textvariable=variable, width=width, show=show)
        entry.grid(row=row, column=1, sticky='ew', pady=5)
        parent.columnconfigure(1, weight=1)
        return entry

    def choice(self, parent, row, label, width=35):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=(0, 12), pady=5)
        combo = ttk.Combobox(parent, state='readonly', width=width)
        combo.grid(row=row, column=1, sticky='ew', pady=5)
        combo.record_ids = {}
        return combo

    def set_choices(self, combo, rows, id_key, formatter, optional=False):
        previous = combo.record_ids.get(combo.get())
        values = {'(None)': None} if optional else {}
        values.update({formatter(row): row[id_key] for row in rows})
        combo.record_ids = values
        combo.configure(values=list(values))
        selected = next((label for label, key in values.items() if key == previous), None)
        combo.set(selected if selected is not None else next(iter(values), ''))

    def selected_id(self, combo, label, optional=False):
        if combo.get() not in combo.record_ids:
            raise InputError(f'Select {label}. If the list is empty, add sample data and refresh.')
        result = combo.record_ids[combo.get()]
        if result is None and not optional:
            raise InputError(f'Select {label}.')
        return result

    def select_id(self, combo, record_id):
        combo.set(next((label for label, key in combo.record_ids.items() if key == record_id), ''))

    def table(self, parent, columns, height=10):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show='headings', selectmode='browse', height=height)
        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=65, stretch=False)
        vertical = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return frame, tree

    def render(self, tree, rows, id_key):
        tree.delete(*tree.get_children())
        for row in rows:
            values = [self.display(row.get(key)) for key in tree['columns']]
            tree.insert('', 'end', iid=str(row[id_key]), values=values)

    @staticmethod
    def display(value):
        if value is None:
            return '—'
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, Decimal):
            return f'{value:.2f}'
        return str(value)

    def selected_row(self, tree, rows):
        selection = tree.selection()
        if not selection:
            raise InputError('Select a row in the table first.')
        return rows[int(selection[0])]


if __name__ == '__main__':
    MechWarXApp().mainloop()
