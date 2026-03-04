import tkinter as tk
from tkinter import ttk, messagebox
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.models.inventory import Item, Inventory
from app.models.transaction import StockTransaction
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
# Using localhost because the script runs on the host machine, accessing the Dockerized Postgres via port 5433
DB_URL = "postgresql://cafeteria:cafeteria_pass@localhost:5433/cafeteria_db"

class DBViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Service DB Viewer")
        self.root.geometry("1100x600")

        self.engine = create_engine(DB_URL)
        self.Session = sessionmaker(bind=self.engine)
        
        # Map table names to Model classes
        self.models_map = {
            'items': Item,
            'inventory': Inventory,
            'stock_transactions': StockTransaction
        }
        
        self.current_table = None
        self.setup_ui()
        
    def setup_ui(self):
        # Main Layout using PanedWindow
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # --- Sidebar (Left) ---
        sidebar_frame = ttk.Frame(main_paned, padding="5", width=200)
        main_paned.add(sidebar_frame, weight=1)
        
        # Sidebar Header
        ttk.Label(sidebar_frame, text="Tables", font=("Segoe UI", 12, "bold")).pack(pady=(5, 10), fill=tk.X)
        
        # Table Listbox
        self.table_listbox = tk.Listbox(sidebar_frame, selectmode=tk.SINGLE, font=("Segoe UI", 10), activestyle='none', relief=tk.FLAT, borderwidth=1)
        self.table_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for listbox
        sb = ttk.Scrollbar(sidebar_frame, orient="vertical", command=self.table_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.table_listbox.config(yscrollcommand=sb.set)
        
        # Populate Listbox
        for table in self.models_map.keys():
            self.table_listbox.insert(tk.END, table)
            
        self.table_listbox.bind("<<ListboxSelect>>", self.on_table_select)

        # --- Content Area (Right) ---
        content_frame = ttk.Frame(main_paned, padding="5")
        main_paned.add(content_frame, weight=5)

        # Top Control Panel
        control_frame = ttk.LabelFrame(content_frame, text="Actions", padding="10")
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Buttons
        ttk.Button(control_frame, text="Refresh", command=self.load_data).pack(side=tk.LEFT, padx=5)
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
        
        # Initial selection
        if self.models_map:
            self.table_listbox.selection_set(0)
            self.on_table_select(None)

    def on_table_select(self, event):
        selection = self.table_listbox.curselection()
        if selection:
            table_name = self.table_listbox.get(selection[0])
            self.current_table = table_name
            self.load_data()

    def get_columns(self, model_class):
        inspector = inspect(self.engine)
        return [c['name'] for c in inspector.get_columns(model_class.__tablename__)]

    def load_data(self, event=None):
        if not self.current_table:
            return

        table_name = self.current_table
        
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if table_name not in self.models_map:
             return

        model_class = self.models_map[table_name]
        
        # Setup columns
        try:
            columns = self.get_columns(model_class)
            self.tree['columns'] = columns
            
            for col in columns:
                self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
                self.tree.column(col, width=150, anchor=tk.W)

            # Fetch data
            session = self.Session()
            try:
                self.all_data = [] # Store for filtering
                records = session.query(model_class).all()
                for record in records:
                    # Use getattr to get column values dynamically
                    values = [getattr(record, col) for col in columns]
                    # Convert to string for display
                    values = [str(v) if v is not None else "" for v in values]
                    self.all_data.append(values)
                    self.tree.insert('', tk.END, values=values)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load data: {e}")
                logger.error(f"Error loading data: {e}")
            finally:
                session.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to setup columns: {e}")
            logger.error(f"Error setup columns: {e}")

    def filter_data(self):
        query = self.search_var.get().lower()
        # Clear view
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not hasattr(self, 'all_data'):
            return

        for values in self.all_data:
            # Simple search: check if query string exists in any column
            if any(query in str(v).lower() for v in values):
                self.tree.insert('', tk.END, values=values)

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Try to convert to appropriate type for sorting
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
        model_class = self.models_map[table_name]
        session = self.Session()
        
        try:
            # Assuming 'id' is the primary key and is the first column
            # We need to find the ID index in the columns
            columns = self.tree['columns']
            id_index = -1
            for i, col in enumerate(columns):
                if col == 'id':
                    id_index = i
                    break
            
            if id_index == -1:
                messagebox.showerror("Error", "Could not find 'id' column for deletion")
                return

            ids_to_delete = []
            for item in selected_items:
                values = self.tree.item(item, 'values')
                ids_to_delete.append(values[id_index])

            # Perform deletion
            for record_id in ids_to_delete:
                session.query(model_class).filter(model_class.id == record_id).delete()
            
            session.commit()
            messagebox.showinfo("Success", "Records deleted successfully")
            self.load_data() # Refresh
            
        except Exception as e:
            session.rollback()
            messagebox.showerror("Error", f"Failed to delete: {e}")
            logger.error(f"Error deleting: {e}")
        finally:
            session.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = DBViewerApp(root)
    root.mainloop()
