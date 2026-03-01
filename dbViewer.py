import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from sqlalchemy import create_engine, inspect, text, Table, MetaData, insert
from sqlalchemy.exc import SQLAlchemyError
import logging
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
# Accessing the Dockerized Postgres via port 5433 (mapped to 5432)
DB_URL = "postgresql://cafeteria:cafeteria_pass@localhost:5433/cafeteria_db"

class UniversalDBViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal DB Viewer - All Services")
        self.root.geometry("1200x700")

        self.setup_db_connection()
        self.setup_ui()
        
    def setup_db_connection(self):
        try:
            self.engine = create_engine(DB_URL)
            self.metadata = MetaData()
            self.metadata.reflect(bind=self.engine)
            self.inspector = inspect(self.engine)
            self.connected = True
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to database:\n{e}\n\nMake sure the Docker containers are running.")
            self.connected = False
            self.root.destroy()

    def setup_ui(self):
        if not self.connected:
            return

        # Main Layout using PanedWindow
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # --- Sidebar (Left) ---
        sidebar_frame = ttk.Frame(main_paned, padding="5", width=250)
        main_paned.add(sidebar_frame, weight=1)
        
        # Sidebar Header
        ttk.Label(sidebar_frame, text="All Tables", font=("Segoe UI", 12, "bold")).pack(pady=(5, 10), fill=tk.X)
        
        # Table Listbox
        self.table_listbox = tk.Listbox(sidebar_frame, selectmode=tk.SINGLE, font=("Segoe UI", 10), activestyle='none', relief=tk.FLAT, borderwidth=1)
        self.table_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for listbox
        sb = ttk.Scrollbar(sidebar_frame, orient="vertical", command=self.table_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.table_listbox.config(yscrollcommand=sb.set)
        
        # Populate Listbox
        self.refresh_tables()
            
        self.table_listbox.bind("<<ListboxSelect>>", self.on_table_select)
        
        # Refresh Tables Button
        ttk.Button(sidebar_frame, text="Refresh Tables", command=self.refresh_tables).pack(pady=5, fill=tk.X)

        # --- Content Area (Right) ---
        content_frame = ttk.Frame(main_paned, padding="5")
        main_paned.add(content_frame, weight=5)

        # Top Control Panel
        control_frame = ttk.LabelFrame(content_frame, text="Actions", padding="10")
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Buttons
        ttk.Button(control_frame, text="Refresh Data", command=self.load_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Add New Tuple", command=self.add_tuple).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        # Search/Filter
        ttk.Label(control_frame, text="Search:").pack(side=tk.LEFT, padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda name, index, mode: self.filter_data())
        ttk.Entry(control_frame, textvariable=self.search_var).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Treeview for Data
        self.tree_frame = ttk.Frame(content_frame, padding="5")
        self.tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(self.tree_frame, show='headings', selectmode='extended')
        
        # Scrollbars
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')

        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)
        
        self.current_table = None

    def refresh_tables(self):
        self.table_listbox.delete(0, tk.END)
        # Refresh metadata to get new tables if any
        self.metadata.reflect(bind=self.engine)
        tables = sorted(self.metadata.tables.keys())
        for table in tables:
            self.table_listbox.insert(tk.END, table)

    def on_table_select(self, event):
        selection = self.table_listbox.curselection()
        if selection:
            table_name = self.table_listbox.get(selection[0])
            self.current_table = table_name
            self.load_data()

    def get_columns(self, table_name):
        return [c['name'] for c in self.inspector.get_columns(table_name)]

    def load_data(self, event=None):
        if not self.current_table:
            return

        table_name = self.current_table
        
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            columns = self.get_columns(table_name)
            self.tree['columns'] = columns
            
            for col in columns:
                self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
                self.tree.column(col, width=150, anchor=tk.W)

            # Fetch data using raw SQL for simplicity in viewer
            with self.engine.connect() as connection:
                # Use text() for safe execution
                query = text(f"SELECT * FROM {table_name}")
                result = connection.execute(query)
                
                self.all_data = [] # Store for filtering
                for row in result:
                    # Convert row to list of strings
                    values = [str(v) if v is not None else "NULL" for v in row]
                    self.all_data.append(values)
                    self.tree.insert('', tk.END, values=values)
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            logger.error(f"Error loading data: {e}")

    def filter_data(self):
        query = self.search_var.get().lower()
        # Clear view
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not hasattr(self, 'all_data'):
            return

        for values in self.all_data:
            if any(query in str(v).lower() for v in values):
                self.tree.insert('', tk.END, values=values)

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected")
            return

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected_items)} items?"):
            return

        if not self.current_table:
            return
            
        table_name = self.current_table
        
        # We need to identify the primary key to delete correctly
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        pks = pk_constraint['constrained_columns']
        
        if not pks:
            messagebox.showerror("Error", "Table has no primary key, cannot delete safely.")
            return
            
        # For simplicity, handle single PK
        pk_col = pks[0]
        
        # Find index of PK in columns
        columns = self.get_columns(table_name)
        try:
            pk_index = columns.index(pk_col)
        except ValueError:
             messagebox.showerror("Error", f"Primary key column '{pk_col}' not found in display.")
             return

        try:
            with self.engine.begin() as connection:
                table = self.metadata.tables[table_name]
                ids_to_delete = []
                for item in selected_items:
                    values = self.tree.item(item, 'values')
                    ids_to_delete.append(values[pk_index])
                
                # Delete one by one or using IN clause
                delete_stmt = table.delete().where(table.c[pk_col].in_(ids_to_delete))
                connection.execute(delete_stmt)
                
            messagebox.showinfo("Success", "Records deleted successfully")
            self.load_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")
            logger.error(f"Error deleting: {e}")

    def add_tuple(self):
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table first.")
            return

        table_name = self.current_table
        columns_info = self.inspector.get_columns(table_name)
        
        # Filter out auto-increment PKs usually (often 'id')
        # But for generic viewer, better to show all and let user decide or leave empty
        
        AddTupleDialog(self.root, table_name, columns_info, self.save_tuple)

    def save_tuple(self, table_name, data):
        try:
            with self.engine.begin() as connection:
                table = self.metadata.tables[table_name]
                stmt = insert(table).values(**data)
                connection.execute(stmt)
            
            messagebox.showinfo("Success", "Record added successfully")
            self.load_data()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add record: {e}")
            logger.error(f"Error adding record: {e}")
            return False

class AddTupleDialog(tk.Toplevel):
    def __init__(self, parent, table_name, columns_info, on_save_callback):
        super().__init__(parent)
        self.title(f"Add New Record - {table_name}")
        self.geometry("500x600")
        self.columns_info = columns_info
        self.on_save_callback = on_save_callback
        self.table_name = table_name
        
        self.entries = {}
        
        # Buttons (Create first to ensure they are at bottom)
        btn_frame = ttk.Frame(self, padding="10")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.RIGHT, padx=5)
        
        # Canvas for scrolling if many columns
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Form Generation
        ttk.Label(scrollable_frame, text="Leave fields empty for NULL/Auto-Increment", font=("Segoe UI", 9, "italic")).pack(pady=10)

        for col in columns_info:
            col_name = col['name']
            col_type = str(col['type'])
            
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(frame, text=f"{col_name} ({col_type}):", width=25, anchor="w").pack(side=tk.LEFT)
            
            entry = ttk.Entry(frame)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Default value if any (simplified)
            if col.get('default'):
                pass # Don't prefill default, let DB handle it if empty

            self.entries[col_name] = entry

    def save(self):
        data = {}
        for col_name, entry in self.entries.items():
            val = entry.get().strip()
            if val:
                # Basic type conversion could go here, 
                # but SQLAlchemy/Driver handles strings well for most types
                data[col_name] = val
            else:
                # Treat empty string as None/NULL (or let DB use default)
                # If we don't include it in the insert dict, DB uses default/null
                pass 
        
        if self.on_save_callback(self.table_name, data):
            self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = UniversalDBViewerApp(root)
    root.mainloop()
