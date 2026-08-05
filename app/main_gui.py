import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from excel_manager import ExcelManager, clean_val

try:
    from services import order_card_service as card_svc
    from views.order_card_view import OrderCardView
    from lang import LANGUAGE_OPTIONS, ORDER_CARD_TRANSLATIONS, TRANSLATIONS
except ImportError:
    from app.services import order_card_service as card_svc
    from app.views.order_card_view import OrderCardView
    from app.lang import LANGUAGE_OPTIONS, ORDER_CARD_TRANSLATIONS, TRANSLATIONS

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A5
    REPORTLAB_INSTALLED = True
except ImportError:
    REPORTLAB_INSTALLED = False

# --- Theme Configuration ---
THEMES = {
    "light": {
        "bg_body": "#F5F5F7", "bg_header": "#FFFFFF", "bg_sidebar": "#FFFFFF",
        "bg_card": "#FFFFFF", "border": "#E5E5EA", "text_main": "#1D1D1F",
        "text_muted": "#86868B", "bg_chart": "#FAFAFC"
    },
    "dark": {
        "bg_body": "#121212", "bg_header": "#1E1E1E", "bg_sidebar": "#1E1E1E",
        "bg_card": "#1E1E1E", "border": "#333333", "text_main": "#F5F5F7",
        "text_muted": "#A1A1A6", "bg_chart": "#2C2C2E"
    }
}

PRIMARY = "#007AFF"
SUCCESS = "#34C759"
WARNING = "#FF9500"
DANGER = "#FF3B30"
FONT_FAMILY = "SF Pro Text" if sys.platform == "darwin" else "Segoe UI"


class CircularDonutChart(tk.Canvas):
    def __init__(self, parent, size=75, ring_color=PRIMARY, bg_color="#E5E5EA", stroke_width=8, theme_colors=None, **kwargs):
        bg = theme_colors["bg_chart"] if theme_colors else "#FAFAFC"
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, **kwargs)
        self.size = size
        self.ring_color = ring_color
        self.bg_color = bg_color
        self.stroke_width = stroke_width
        self.percentage = 0
        self.draw_chart()

    def draw_chart(self):
        self.delete("all")
        margin = self.stroke_width / 2 + 2
        x0, y0 = margin, margin
        x1, y1 = self.size - margin, self.size - margin

        self.create_oval(x0, y0, x1, y1, outline=self.bg_color, width=self.stroke_width)

        if self.percentage >= 100:
            self.create_oval(x0, y0, x1, y1, outline=self.ring_color, width=self.stroke_width)
        elif self.percentage > 0:
            extent = -(self.percentage / 100.0) * 360
            self.create_arc(x0, y0, x1, y1, start=90, extent=extent, style=tk.ARC, outline=self.ring_color, width=self.stroke_width)

    def set_percentage(self, pct):
        self.percentage = max(0, min(100, pct))
        self.draw_chart()


class AtelierERPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jhagra Textile & Clothing — Atelier Ledger")
        self.geometry("1350x850")

        if os.path.exists("icon.ico"):
            self.iconbitmap("icon.ico")

        self.current_theme = "light"
        self.current_lang = "en"
        # Destructive operations are available only after an administrator login.
        self.current_user_role = "Viewer"
        self.colors = THEMES[self.current_theme]

        self.excel_mgr = ExcelManager()

        # --- HEADERS MATCHING PHYSICAL FORM ---
        # Legacy columns first; order-card columns appended LAST so existing
        # .xlsx rows keep positional compatibility (no data shifting on read).
        self.cust_headers = card_svc.CUST_HEADERS
        self.emp_headers = ["id", "name", "phone", "role", "status", "current_task"]
        self.ord_headers = card_svc.ORD_HEADERS

        self.default_garments = ["Shalwar Kameez", "Waistcoat", "2-Piece Suit"]
        self.default_roles = ["Master Cutter", "Stitching Specialist"]

        self.withdraw()
        self.show_login_screen()

    # ==========================================
    # ID HELPERS
    # ==========================================
    def _next_id(self, prefix, records, start=101):
        """Generate the next sequential ID for a record set (e.g. C-102)."""
        nums = []
        for r in records:
            rid = clean_val(r.get("id"))
            if rid.startswith(prefix + "-"):
                try:
                    nums.append(int(rid.split("-", 1)[1]))
                except (ValueError, IndexError):
                    pass
        return f"{prefix}-{max(nums) + 1 if nums else start}"

    # ==========================================
    # AUTHENTICATION
    # ==========================================
    def show_login_screen(self):
        self.login_dlg = tk.Toplevel(self)
        self.login_dlg.title("System Authentication")
        self.login_dlg.geometry("400x250")
        self.login_dlg.configure(bg=self.colors["bg_card"])
        self.login_dlg.protocol("WM_DELETE_WINDOW", self.destroy)
        self.login_dlg.resizable(False, False)

        tk.Label(self.login_dlg, text="🔒 JTC Secure Login", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=(30, 10))
        tk.Label(self.login_dlg, text="Please enter your administrator password:", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack()

        self.ent_pwd = tk.Entry(self.login_dlg, show="*", font=(FONT_FAMILY, 12), justify="center")
        self.ent_pwd.pack(pady=15, padx=50, fill=tk.X)
        self.ent_pwd.bind("<Return>", lambda e: self.authenticate())

        tk.Button(self.login_dlg, text="Login to Dashboard", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, cursor="hand2", command=self.authenticate).pack(fill=tk.X, padx=50)

    def authenticate(self):
        pwd = self.ent_pwd.get()
        if pwd == "admin123":
            self.current_user_role = "Administrator"
            self.login_dlg.destroy()
            self.initialize_application()
        else:
            messagebox.showerror("Access Denied", "Incorrect password.", parent=self.login_dlg)
            self.ent_pwd.delete(0, tk.END)

    # ==========================================
    # APP LIFECYCLE / REFRESH
    # ==========================================
    def initialize_application(self):
        self.deiconify()
        self.reload_all_data()
        self.build_ui_layout()
        self.update_clock()
        self.auto_refresh_loop()

    def reload_all_data(self):
        self.customers = self.excel_mgr.read_records("customers.xlsx", self.cust_headers)
        self.employees = self.excel_mgr.read_records("employees.xlsx", self.emp_headers)
        self.orders = self.excel_mgr.read_records("orders.xlsx", self.ord_headers)
        self.garment_types = self.excel_mgr.load_settings_list("garment_type", self.default_garments)
        self.employee_roles = self.excel_mgr.load_settings_list("employee_role", self.default_roles)

    def auto_refresh_loop(self):
        self.reload_all_data()
        if hasattr(self, "tree_orders") and self.tree_orders.winfo_exists():
            self.update_graphics_and_stats()
        self.after(5000, self.auto_refresh_loop)

    # ==========================================
    # THEME / LAYOUT
    # ==========================================
    def change_theme(self, event=None):
        sel = self.cbo_theme.get()
        self.current_theme = "dark" if "Dark" in sel else "light"
        self.colors = THEMES[self.current_theme]
        self.header_frame.destroy()
        self.body_container.destroy()
        self.build_ui_layout()

    def build_ui_layout(self):
        self.configure(bg=self.colors["bg_body"])
        self.apply_ttk_styles()
        self.create_header()
        self.create_layout()
        self.show_section("dashboard")
        self.update_graphics_and_stats()

    def apply_ttk_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", background=self.colors["bg_card"], foreground=self.colors["text_main"], fieldbackground=self.colors["bg_card"], rowheight=34, font=(FONT_FAMILY, 9), borderwidth=0)
        self.style.configure("Treeview.Heading", background=self.colors["bg_body"], foreground=self.colors["text_muted"], font=(FONT_FAMILY, 8, "bold"), borderwidth=0)
        self.style.map("Treeview", background=[('selected', PRIMARY)], foreground=[('selected', 'white')])
        self.style.configure("TCombobox", font=(FONT_FAMILY, 9))

    def create_header(self):
        self.header_frame = tk.Frame(self, bg=self.colors["bg_header"], height=56, highlightbackground=self.colors["border"], highlightthickness=1)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.pack_propagate(False)

        logo_box = tk.Frame(self.header_frame, bg=self.colors["bg_header"])
        logo_box.pack(side=tk.LEFT, padx=20)
        tk.Label(logo_box, text="JTC", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), padx=8, pady=2).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(logo_box, text="JHAGRA CREATION & FABRICS", bg=self.colors["bg_header"], fg=self.colors["text_main"], font=(FONT_FAMILY, 11, "bold")).pack(side=tk.LEFT)
        self.lbl_clock = tk.Label(self.header_frame, text="", bg=self.colors["bg_header"], fg=self.colors["text_muted"], font=(FONT_FAMILY, 10))
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

    def create_layout(self):
        self.body_container = tk.Frame(self, bg=self.colors["bg_body"])
        self.body_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        sidebar = tk.Frame(self.body_container, bg=self.colors["bg_sidebar"], width=220, highlightbackground=self.colors["border"], highlightthickness=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
        sidebar.pack_propagate(False)

        self.nav_buttons = {}
        nav_keys = [("dashboard", "nav_dash"), ("customer", "nav_cust"),
                    ("order_card", "nav_order_card"),
                    ("employee", "nav_emp"), ("admin", "nav_admin")]

        for key, lang_key in nav_keys:
            btn = tk.Button(sidebar, text=TRANSLATIONS[self.current_lang][lang_key], anchor="w", font=(FONT_FAMILY, 10, "bold"),
                            bg=self.colors["bg_sidebar"], fg=self.colors["text_muted"], activebackground=PRIMARY, activeforeground="white",
                            bd=0, padx=16, pady=12, cursor="hand2", command=lambda k=key: self.show_section(k))
            btn.pack(fill=tk.X, pady=2, padx=6)
            self.nav_buttons[key] = (btn, lang_key)

        self.main_content = tk.Frame(self.body_container, bg=self.colors["bg_body"])
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.sections = {}
        self.build_dashboard_section()
        self.build_customer_section()
        self.build_order_card_section()
        self.build_employee_section()
        self.build_admin_section()

    def show_section(self, section_key):
        for key, frame in self.sections.items():
            frame.pack_forget()
            btn, _ = self.nav_buttons[key]
            btn.configure(bg=self.colors["bg_sidebar"], fg=self.colors["text_muted"])
        self.sections[section_key].pack(fill=tk.BOTH, expand=True)
        active_btn, _ = self.nav_buttons[section_key]
        active_btn.configure(bg=PRIMARY, fg="white")

    # ==========================================
    # DASHBOARD SECTION
    # ==========================================
    def build_dashboard_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["dashboard"] = sec

        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_dash_title = tk.Label(hdr, text="Dashboard", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_dash_title.pack(anchor="w")
        self.lbl_dash_sub = tk.Label(hdr, text="Live overview of tailoring work", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_dash_sub.pack(anchor="w")

        graphics_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        graphics_frame.pack(fill=tk.X, padx=24, pady=10)

        c1 = tk.Frame(graphics_frame, bg=self.colors["bg_chart"], highlightbackground=self.colors["border"], highlightthickness=1, padx=16, pady=12)
        c1.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
        i1 = tk.Frame(c1, bg=self.colors["bg_chart"]); i1.pack(side=tk.LEFT)
        self.lbl_done_title = tk.Label(i1, text="WORK DONE", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_done_title.pack(anchor="w")
        self.lbl_done_pct = tk.Label(i1, text="0%", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=SUCCESS); self.lbl_done_pct.pack(anchor="w")
        self.chart_done = CircularDonutChart(c1, size=70, ring_color=SUCCESS, theme_colors=self.colors); self.chart_done.pack(side=tk.RIGHT)

        c2 = tk.Frame(graphics_frame, bg=self.colors["bg_chart"], highlightbackground=self.colors["border"], highlightthickness=1, padx=16, pady=12)
        c2.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        i2 = tk.Frame(c2, bg=self.colors["bg_chart"]); i2.pack(side=tk.LEFT)
        self.lbl_prog_title = tk.Label(i2, text="IN PROGRESS", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_prog_title.pack(anchor="w")
        self.lbl_prog_pct = tk.Label(i2, text="0%", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=WARNING); self.lbl_prog_pct.pack(anchor="w")
        self.chart_prog = CircularDonutChart(c2, size=70, ring_color=WARNING, theme_colors=self.colors); self.chart_prog.pack(side=tk.RIGHT)

        c3 = tk.Frame(graphics_frame, bg=self.colors["bg_chart"], highlightbackground=self.colors["border"], highlightthickness=1, padx=16, pady=12)
        c3.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(8, 0))
        i3 = tk.Frame(c3, bg=self.colors["bg_chart"]); i3.pack(side=tk.LEFT)
        self.lbl_rem_title = tk.Label(i3, text="REMAINING", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_muted"]); self.lbl_rem_title.pack(anchor="w")
        self.lbl_rem_pct = tk.Label(i3, text="0%", font=(FONT_FAMILY, 20, "bold"), bg=self.colors["bg_chart"], fg=DANGER); self.lbl_rem_pct.pack(anchor="w")
        self.chart_rem = CircularDonutChart(c3, size=70, ring_color=DANGER, theme_colors=self.colors); self.chart_rem.pack(side=tk.RIGHT)

        tbl_bar = tk.Frame(sec, bg=self.colors["bg_card"])
        tbl_bar.pack(fill=tk.X, padx=24, pady=(16, 8))
        self.lbl_ledger_head = tk.Label(tbl_bar, text="Active Orders Ledger", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_ledger_head.pack(side=tk.LEFT)

        tk.Button(tbl_bar, text="✔ Mark Ready", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=lambda: self.quick_change_order_status("Ready")).pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        self.tree_orders = ttk.Treeview(table_frame, columns=self.ord_headers, show="headings")
        for c in self.ord_headers:
            self.tree_orders.heading(c, text=c.upper().replace("_", " "))
            self.tree_orders.column(c, width=90)
        self.tree_orders.pack(fill=tk.BOTH, expand=True)

        self.tree_orders.tag_configure("status_ready", foreground="#1B5E20" if self.current_theme == "light" else "#81C784")
        self.tree_orders.tag_configure("status_prog", foreground="#E65100" if self.current_theme == "light" else "#FFB74D")
        self.tree_orders.tag_configure("status_pending", foreground="#B71C1C" if self.current_theme == "light" else "#E57373")

        self.tree_orders.bind("<Button-3>", self.show_order_context_menu)

    def show_order_context_menu(self, event):
        row_id = self.tree_orders.identify_row(event.y)
        if row_id:
            self.tree_orders.selection_set(row_id)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="✔ Mark Ready", command=lambda: self.quick_change_order_status("Ready"))
            menu.add_command(label="⏳ Mark In Progress", command=lambda: self.quick_change_order_status("In Progress"))
            menu.add_separator()
            menu.add_command(label="📄 Print Order PDF", command=self.generate_order_pdf)
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def quick_change_order_status(self, new_status):
        sel = self.tree_orders.selection()
        if not sel:
            return
        ord_id = str(self.tree_orders.item(sel[0])["values"][0])
        rows_to_write = []
        for o in self.orders:
            curr_id = clean_val(o.get("id"))
            status = new_status if curr_id == ord_id else clean_val(o.get("status"))
            # Schema-aware rewrite: preserves every column (legacy + order-card).
            r = [clean_val(o.get(h)) for h in self.ord_headers]
            r[self.ord_headers.index("id")] = curr_id
            r[self.ord_headers.index("status")] = status
            rows_to_write.append(r)
        try:
            self.excel_mgr.write_all_records("orders.xlsx", self.ord_headers, rows_to_write)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))
            return
        self.reload_all_data()
        self.update_graphics_and_stats()

    # ==========================================
    # CUSTOMER SECTION
    # ==========================================
    def build_customer_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["customer"] = sec
        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_cust_title = tk.Label(hdr, text="Customer Hub", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_cust_title.pack(side=tk.LEFT)
        self.lbl_cust_sub = tk.Label(hdr, text="Manage customer profiles & measurements", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_cust_sub.pack(side=tk.LEFT, padx=12, pady=(6, 0))

        self.btn_cust_modal = tk.Button(hdr, text="➕ Add Customer", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.open_add_customer_modal)
        self.btn_cust_modal.pack(side=tk.RIGHT, padx=4)
        self.btn_new_card = tk.Button(hdr, text="🖨️ New Order Card", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=lambda: self.show_section("order_card"))
        self.btn_new_card.pack(side=tk.RIGHT, padx=4)
        self.btn_cust_receipt = tk.Button(hdr, text="Print Latest Receipt", bg=WARNING, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.print_selected_customer_receipt)
        self.btn_cust_receipt.pack(side=tk.RIGHT, padx=4)
        self.btn_cust_edit = tk.Button(hdr, text="Edit", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.edit_selected_customer)
        self.btn_cust_edit.pack(side=tk.RIGHT, padx=4)
        self.btn_cust_delete = tk.Button(hdr, text="Delete", bg=DANGER, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.delete_selected_customer)
        self.btn_cust_delete.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        self.tree_customers = ttk.Treeview(table_frame, columns=self.cust_headers, show="headings")
        for c in self.cust_headers:
            self.tree_customers.heading(c, text=c.upper())
            self.tree_customers.column(c, width=75)
        self.tree_customers.pack(fill=tk.BOTH, expand=True)

    # ==========================================
    # ORDER CARD SECTION  (digital JTQ paper slip)
    # ==========================================
    def build_order_card_section(self):
        """Mounts the reusable OrderCardView into the main content area."""
        sec = tk.Frame(self.main_content, bg=self.colors["bg_body"])
        self.sections["order_card"] = sec
        self.order_card = OrderCardView(sec, self, self.colors, FONT_FAMILY,
                                        PRIMARY, SUCCESS, WARNING, DANGER)
        self.order_card.pack(fill=tk.BOTH, expand=True)

    # ==========================================
    # EMPLOYEE SECTION
    # ==========================================
    def build_employee_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["employee"] = sec
        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_emp_title = tk.Label(hdr, text="Staff & Tailors", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_emp_title.pack(side=tk.LEFT)
        self.lbl_emp_sub = tk.Label(hdr, text="Manage staff, roles and daily tasks", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_emp_sub.pack(side=tk.LEFT, padx=12, pady=(6, 0))

        self.btn_task_modal = tk.Button(hdr, text="🛠️ Assign Task", bg=WARNING, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.open_assign_task_modal)
        self.btn_task_modal.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_modal = tk.Button(hdr, text="➕ Add Staff", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.open_add_employee_modal)
        self.btn_emp_modal.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_print = tk.Button(hdr, text="Print Task Slip", bg=WARNING, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.print_selected_employee_task)
        self.btn_emp_print.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_edit = tk.Button(hdr, text="Edit", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.edit_selected_employee)
        self.btn_emp_edit.pack(side=tk.RIGHT, padx=4)
        self.btn_emp_delete = tk.Button(hdr, text="Delete", bg=DANGER, fg="white", font=(FONT_FAMILY, 9, "bold"), bd=0, padx=12, pady=6, cursor="hand2", command=self.delete_selected_employee)
        self.btn_emp_delete.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)
        self.tree_employees = ttk.Treeview(table_frame, columns=self.emp_headers, show="headings")
        for c in self.emp_headers:
            self.tree_employees.heading(c, text=c.upper())
            self.tree_employees.column(c, width=120)
        self.tree_employees.pack(fill=tk.BOTH, expand=True)

    # ==========================================
    # ADMIN / SETTINGS SECTION
    # ==========================================
    def build_admin_section(self):
        sec = tk.Frame(self.main_content, bg=self.colors["bg_card"], highlightbackground=self.colors["border"], highlightthickness=1)
        self.sections["admin"] = sec
        hdr = tk.Frame(sec, bg=self.colors["bg_card"])
        hdr.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.lbl_admin_title = tk.Label(hdr, text="Settings", font=(FONT_FAMILY, 16, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self.lbl_admin_title.pack(anchor="w")
        self.lbl_admin_sub = tk.Label(hdr, text="Theme, language, garments & employee roles", font=(FONT_FAMILY, 9), bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self.lbl_admin_sub.pack(anchor="w")

        cards_frame = tk.Frame(sec, bg=self.colors["bg_card"])
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=10)

        # Row 1: Theme + Language
        row1 = tk.Frame(cards_frame, bg=self.colors["bg_card"])
        row1.pack(fill=tk.X, pady=(0, 10))

        c_theme = tk.Frame(row1, bg=self.colors["bg_chart"], highlightbackground=self.colors["border"], highlightthickness=1, padx=14, pady=14)
        c_theme.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.lbl_theme_label = tk.Label(c_theme, text="🛠️ System Theme", font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"])
        self.lbl_theme_label.pack(anchor="w", pady=(0, 8))
        self.cbo_theme = ttk.Combobox(c_theme, values=["Light Mode ☀️", "Dark Mode 🌙"], state="readonly")
        self.cbo_theme.current(0 if self.current_theme == "light" else 1)
        self.cbo_theme.pack(fill=tk.X, pady=(2, 4))
        self.cbo_theme.bind("<<ComboboxSelected>>", self.change_theme)

        c_lang = tk.Frame(row1, bg=self.colors["bg_chart"], highlightbackground=self.colors["border"], highlightthickness=1, padx=14, pady=14)
        c_lang.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self.lbl_language_label = tk.Label(c_lang, text="🌐 Language / زبان", font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"])
        self.lbl_language_label.pack(anchor="w", pady=(0, 8))
        self.cbo_lang = ttk.Combobox(c_lang, values=[label for _, label in LANGUAGE_OPTIONS], state="readonly")
        if self.current_lang in [code for code, _ in LANGUAGE_OPTIONS]:
            self.cbo_lang.current([code for code, _ in LANGUAGE_OPTIONS].index(self.current_lang))
        else:
            self.cbo_lang.current(0)
        self.cbo_lang.pack(fill=tk.X, pady=(2, 4))
        self.cbo_lang.bind("<<ComboboxSelected>>", self.on_language_change)

        # Row 2: Garment types + Employee roles
        row2 = tk.Frame(cards_frame, bg=self.colors["bg_card"])
        row2.pack(fill=tk.BOTH, expand=True)

        c_garments = tk.Frame(row2, bg=self.colors["bg_chart"], highlightbackground=self.colors["border"], highlightthickness=1, padx=14, pady=14)
        c_garments.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        tk.Label(c_garments, text="🧵 Garment Types", font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"]).pack(anchor="w", pady=(0, 8))

        list_wrap_g = tk.Frame(c_garments, bg=self.colors["bg_chart"])
        list_wrap_g.pack(fill=tk.BOTH, expand=True)
        self.lst_garments = tk.Listbox(list_wrap_g, bg=self.colors["bg_card"], fg=self.colors["text_main"], selectbackground=PRIMARY, selectforeground="white", highlightthickness=1, highlightbackground=self.colors["border"], font=(FONT_FAMILY, 9))
        sb_g = ttk.Scrollbar(list_wrap_g, orient=tk.VERTICAL, command=self.lst_garments.yview)
        self.lst_garments.configure(yscrollcommand=sb_g.set)
        self.lst_garments.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_g.pack(side=tk.RIGHT, fill=tk.Y)

        ent_row_g = tk.Frame(c_garments, bg=self.colors["bg_chart"])
        ent_row_g.pack(fill=tk.X, pady=(8, 0))
        self.ent_new_garment = tk.Entry(ent_row_g, font=(FONT_FAMILY, 9))
        self.ent_new_garment.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(ent_row_g, text="➕ Add", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.add_garment_type).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(ent_row_g, text="✖ Remove", bg=DANGER, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.remove_garment_type).pack(side=tk.LEFT)

        c_roles = tk.Frame(row2, bg=self.colors["bg_chart"], highlightbackground=self.colors["border"], highlightthickness=1, padx=14, pady=14)
        c_roles.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        tk.Label(c_roles, text="👔 Employee Roles", font=(FONT_FAMILY, 10, "bold"), bg=self.colors["bg_chart"], fg=self.colors["text_main"]).pack(anchor="w", pady=(0, 8))

        list_wrap_r = tk.Frame(c_roles, bg=self.colors["bg_chart"])
        list_wrap_r.pack(fill=tk.BOTH, expand=True)
        self.lst_roles = tk.Listbox(list_wrap_r, bg=self.colors["bg_card"], fg=self.colors["text_main"], selectbackground=PRIMARY, selectforeground="white", highlightthickness=1, highlightbackground=self.colors["border"], font=(FONT_FAMILY, 9))
        sb_r = ttk.Scrollbar(list_wrap_r, orient=tk.VERTICAL, command=self.lst_roles.yview)
        self.lst_roles.configure(yscrollcommand=sb_r.set)
        self.lst_roles.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_r.pack(side=tk.RIGHT, fill=tk.Y)

        ent_row_r = tk.Frame(c_roles, bg=self.colors["bg_chart"])
        ent_row_r.pack(fill=tk.X, pady=(8, 0))
        self.ent_new_role = tk.Entry(ent_row_r, font=(FONT_FAMILY, 9))
        self.ent_new_role.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(ent_row_r, text="➕ Add", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.add_employee_role).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(ent_row_r, text="✖ Remove", bg=DANGER, fg="white", font=(FONT_FAMILY, 8, "bold"), bd=0, padx=10, pady=4, cursor="hand2", command=self.remove_employee_role).pack(side=tk.LEFT)

        self.refresh_settings_ui()

    def refresh_settings_ui(self):
        self.lst_garments.delete(0, tk.END)
        for g in self.garment_types:
            self.lst_garments.insert(tk.END, g)
        self.lst_roles.delete(0, tk.END)
        for r in self.employee_roles:
            self.lst_roles.insert(tk.END, r)

    # --- Garment type management ---
    def add_garment_type(self):
        val = self.ent_new_garment.get().strip()
        if not val:
            return
        if val in self.garment_types:
            messagebox.showinfo("Already Exists", "This garment type is already in the list.")
            return
        self.garment_types.append(val)
        try:
            self.excel_mgr.save_settings_list("garment_type", self.garment_types)
            self.ent_new_garment.delete(0, tk.END)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_garment_type(self):
        sel = self.lst_garments.curselection()
        if not sel:
            return
        val = self.lst_garments.get(sel[0])
        self.garment_types.remove(val)
        try:
            self.excel_mgr.save_settings_list("garment_type", self.garment_types)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # --- Employee role management ---
    def add_employee_role(self):
        val = self.ent_new_role.get().strip()
        if not val:
            return
        if val in self.employee_roles:
            messagebox.showinfo("Already Exists", "This role is already in the list.")
            return
        self.employee_roles.append(val)
        try:
            self.excel_mgr.save_settings_list("employee_role", self.employee_roles)
            self.ent_new_role.delete(0, tk.END)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_employee_role(self):
        sel = self.lst_roles.curselection()
        if not sel:
            return
        val = self.lst_roles.get(sel[0])
        self.employee_roles.remove(val)
        try:
            self.excel_mgr.save_settings_list("employee_role", self.employee_roles)
            self.reload_all_data()
            self.refresh_settings_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ==========================================
    # MODALS MATCHING PHYSICAL RECEIPT FORM
    # ==========================================
    def open_add_customer_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Register Measurements")
        dlg.geometry("500x560")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text="Customer Profile & Measurements", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=12)

        info_frame = tk.Frame(dlg, bg=self.colors["bg_card"])
        info_frame.pack(fill=tk.X, padx=20)
        tk.Label(info_frame, text="Name:", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=0, column=0, sticky="w")
        e_name = tk.Entry(info_frame); e_name.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Label(info_frame, text="Phone:", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=1, column=0, sticky="w")
        e_phone = tk.Entry(info_frame); e_phone.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        info_frame.columnconfigure(1, weight=1)

        measure_frame = tk.LabelFrame(dlg, text=" 9 Core Measurements (inches) ", bg=self.colors["bg_card"], fg=PRIMARY, font=(FONT_FAMILY, 9, "bold"))
        measure_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        fields = [
            ("Length (لبادی)", "length"), ("Sleeve (چستین)", "sleeve"), ("Shoulder (تیرہ)", "shoulder"),
            ("Collar (کالر)", "collar"), ("Chest (چھاتاں)", "chest"), ("Waist (کمر)", "waist"),
            ("Daman (واشن)", "daman"), ("Shalwar Len (شلوار لیبا)", "shalwar_len"), ("Paancha (بائی پا)", "paancha")
        ]
        entries = {}
        for idx, (lbl, key) in enumerate(fields):
            r = idx // 2
            c = (idx % 2) * 2
            tk.Label(measure_frame, text=lbl, bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8)).grid(row=r, column=c, padx=5, pady=5, sticky="e")
            ent = tk.Entry(measure_frame, width=10)
            ent.grid(row=r, column=c + 1, padx=5, pady=5, sticky="w")
            entries[key] = ent

        def save():
            if not e_name.get():
                messagebox.showerror("Error", "Name required!")
                return
            c_id = self._next_id("C", self.customers, 101)
            row = [c_id, e_name.get(), e_phone.get()] + [entries[k].get() or "0" for k in [f[1] for f in fields]]
            try:
                self.excel_mgr.append_record("customers.xlsx", self.cust_headers, row)
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text="Save Customer", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=10)

    def open_add_order_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Create Style Order")
        dlg.geometry("520x660")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text="Garment Style Configuration", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=10)

        f1 = tk.Frame(dlg, bg=self.colors["bg_card"])
        f1.pack(fill=tk.X, padx=20)
        cbo_cust = ttk.Combobox(f1, values=[f"{c['id']} - {c['name']}" for c in self.customers if c.get("name")], state="readonly")
        if cbo_cust["values"]:
            cbo_cust.current(0)
        tk.Label(f1, text="Customer:", bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w"); cbo_cust.pack(fill=tk.X, pady=(0, 5))

        cbo_garment = ttk.Combobox(f1, values=self.garment_types, state="readonly")
        if cbo_garment["values"]:
            cbo_garment.current(0)
        tk.Label(f1, text="Garment:", bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w"); cbo_garment.pack(fill=tk.X, pady=(0, 5))

        cbo_tailor = ttk.Combobox(f1, values=[e["name"] for e in self.employees if e.get("name")], state="readonly")
        if cbo_tailor["values"]:
            cbo_tailor.current(0)
        tk.Label(f1, text="Assign Tailor:", bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w"); cbo_tailor.pack(fill=tk.X, pady=(0, 5))

        style_frame = tk.LabelFrame(dlg, text=" Visual Form Styles (as per JTQ slip) ", bg=self.colors["bg_card"], fg=PRIMARY, font=(FONT_FAMILY, 9, "bold"))
        style_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Exact groups from the physical JTQ slip
        style_options = {
            "Button Style": ["Baz Button (باز بٹن)", "Karh Button (کڑ بٹن)"],
            "Collar Type": ["Half Ban", "Cut Ban", "Normal Ban", "Collar (کالر)"],
            "Cuff Type": ["Round Cuff (گول کف)", "Square Cuff (چورس کف)", "Round Sleeve Cut (گول بازو)", "Round Sleeve"],
            "Pocket Type": ["Side Pocket (سائن با کٹ)", "Round Pocket (گول جیب)", "Shalwar Pocket (شلوار جیب)", "Simple Patti (سادہ پٹی)", "Patti (پٹی)"],
            "Daman Type": ["Square Daman (چورس واشن)", "Round Daman (گول واشن)"],
            "Stitching": ["1. Single Stitch", "2. Double Stitch", "3. Choka Stitch", "4. Triple Stitch"]
        }

        combos = {}
        rows = list(style_options.items())

        # Left column: button/placket styles (باز بٹن / کڑ بٹن)
        label, opts = rows[0]
        tk.Label(style_frame, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8, "bold")).grid(row=0, column=0, padx=8, pady=8, sticky="e")
        cb = ttk.Combobox(style_frame, values=opts, state="readonly", width=26)
        cb.current(0)
        cb.grid(row=0, column=1, padx=8, pady=8, sticky="w")
        combos[label] = cb

        # Center column: Collar, Cuff, Pocket, Daman
        for r, (label, opts) in enumerate(rows[1:5], start=0):
            tk.Label(style_frame, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8, "bold")).grid(row=r, column=2, padx=8, pady=8, sticky="e")
            cb = ttk.Combobox(style_frame, values=opts, state="readonly", width=26)
            cb.current(0)
            cb.grid(row=r, column=3, padx=8, pady=8, sticky="w")
            combos[label] = cb

        # Bottom of the center column: Stitching (the 4 numbered options on the slip)
        label, opts = rows[5]
        tk.Label(style_frame, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"], font=(FONT_FAMILY, 8, "bold")).grid(row=5, column=2, padx=8, pady=8, sticky="e")
        cb = ttk.Combobox(style_frame, values=opts, state="readonly", width=26)
        cb.current(0)
        cb.grid(row=5, column=3, padx=8, pady=8, sticky="w")
        combos[label] = cb

        style_frame.columnconfigure(1, weight=1)
        style_frame.columnconfigure(3, weight=1)

        def save():
            if not cbo_cust.get() or not cbo_tailor.get():
                messagebox.showerror("Error", "Customer & Tailor needed!")
                return
            c_name = cbo_cust.get().split(" - ")[-1]
            o_id = self._next_id("ORD", self.orders, 101)

            row = [
                o_id, c_name, cbo_garment.get() or "Shalwar Kameez", "In Progress", cbo_tailor.get(),
                combos["Collar Type"].get(), combos["Cuff Type"].get(),
                combos["Pocket Type"].get(), combos["Daman Type"].get(), combos["Stitching"].get(),
                combos["Button Style"].get()
            ]
            try:
                self.excel_mgr.append_record("orders.xlsx", self.ord_headers, row)
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text="Place Order", bg=SUCCESS, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=20, pady=10)

    def open_add_employee_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add Staff Member")
        dlg.geometry("400x260")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text="Register Staff Member", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=(14, 10))

        f = tk.Frame(dlg, bg=self.colors["bg_card"])
        f.pack(fill=tk.X, padx=24)
        tk.Label(f, text="Full Name:", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=0, column=0, sticky="w", pady=4)
        e_name = tk.Entry(f); e_name.grid(row=0, column=1, padx=8, pady=4, sticky="ew")
        tk.Label(f, text="Phone:", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=1, column=0, sticky="w", pady=4)
        e_phone = tk.Entry(f); e_phone.grid(row=1, column=1, padx=8, pady=4, sticky="ew")
        tk.Label(f, text="Role:", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(row=2, column=0, sticky="w", pady=4)
        cbo_role = ttk.Combobox(f, values=self.employee_roles, state="readonly")
        if cbo_role["values"]:
            cbo_role.current(0)
        cbo_role.grid(row=2, column=1, padx=8, pady=4, sticky="ew")
        f.columnconfigure(1, weight=1)

        def save():
            if not e_name.get():
                messagebox.showerror("Error", "Name required!")
                return
            e_id = self._next_id("E", self.employees, 1)
            row = [e_id, e_name.get(), e_phone.get(), cbo_role.get() or "Tailor", "On Duty", "None"]
            try:
                self.excel_mgr.append_record("employees.xlsx", self.emp_headers, row)
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                return
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text="Save Staff", bg=PRIMARY, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=24, pady=(14, 10))

    def open_assign_task_modal(self):
        dlg = tk.Toplevel(self)
        dlg.title("Assign Task")
        dlg.geometry("400x220")
        dlg.configure(bg=self.colors["bg_card"])
        dlg.grab_set()

        tk.Label(dlg, text="Assign Daily Task", font=(FONT_FAMILY, 12, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(pady=(14, 10))

        f = tk.Frame(dlg, bg=self.colors["bg_card"])
        f.pack(fill=tk.X, padx=24)
        tk.Label(f, text="Staff Member:", font=(FONT_FAMILY, 8, "bold"), bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(0, 2))
        cbo_emp = ttk.Combobox(f, values=[f"{e['id']} - {e['name']}" for e in self.employees if e.get("name")], state="readonly")
        if cbo_emp["values"]:
            cbo_emp.current(0)
        cbo_emp.pack(fill=tk.X, pady=(0, 8))
        if not cbo_emp["values"]:
            tk.Label(f, text="No staff registered yet.", bg=self.colors["bg_card"], fg=DANGER, font=(FONT_FAMILY, 8)).pack(anchor="w")

        e_task = tk.Entry(f)
        e_task.insert(0, "e.g. Cut ORD-101")
        e_task.pack(fill=tk.X, pady=(0, 10))

        def save():
            if not cbo_emp.get() or e_task.get().strip() in ("", "e.g. Cut ORD-101"):
                messagebox.showerror("Error", "Select staff and enter a task!")
                return
            emp_id = cbo_emp.get().split(" - ")[0]
            self.update_employee_task(emp_id, e_task.get().strip())
            self.reload_all_data()
            self.update_graphics_and_stats()
            dlg.destroy()

        tk.Button(dlg, text="Assign Task", bg=WARNING, fg="white", font=(FONT_FAMILY, 10, "bold"), bd=0, pady=8, command=save).pack(fill=tk.X, padx=24, pady=(0, 10))

    def update_employee_task(self, emp_id, task_text):
        rows_to_write = []
        for e in self.employees:
            curr_id = clean_val(e.get("id"))
            is_target = curr_id == emp_id
            status = "On Task" if is_target else clean_val(e.get("status"))
            current_task = task_text if is_target else clean_val(e.get("current_task"))
            rows_to_write.append([curr_id, clean_val(e.get("name")), clean_val(e.get("phone")),
                                  clean_val(e.get("role")), status, current_task])
        try:
            self.excel_mgr.write_all_records("employees.xlsx", self.emp_headers, rows_to_write)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    # ==========================================
    # RESTRICTED CUSTOMER / EMPLOYEE ACTIONS
    # ==========================================
    def _require_admin(self):
        if self.current_user_role == "Administrator":
            return True
        messagebox.showerror("Restricted", "Only an Administrator may edit or delete records.")
        return False

    def _selected_record(self, tree, records):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Select a record", "Select a row first.")
            return None
        record_id = str(tree.item(selection[0])["values"][0])
        return next((r for r in records if clean_val(r.get("id")) == record_id), None)

    def _replace_records(self, filename, headers, records):
        self.excel_mgr.write_all_records(filename, headers,
                                         [[clean_val(record.get(h)) for h in headers] for record in records])
        self.reload_all_data()
        self.update_graphics_and_stats()

    def edit_selected_customer(self):
        if not self._require_admin():
            return
        customer = self._selected_record(self.tree_customers, self.customers)
        if not customer:
            return
        dlg = tk.Toplevel(self); dlg.title("Edit Customer"); dlg.geometry("400x260"); dlg.configure(bg=self.colors["bg_card"]); dlg.grab_set()
        fields = {}
        for row, (key, label) in enumerate((("name", "Name"), ("phone", "Phone"), ("address", "Address"))):
            tk.Label(dlg, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"]).grid(row=row, column=0, padx=18, pady=10, sticky="w")
            entry = tk.Entry(dlg, width=35); entry.insert(0, clean_val(customer.get(key))); entry.grid(row=row, column=1, padx=8, pady=10); fields[key] = entry
        def save():
            if not fields["name"].get().strip():
                messagebox.showerror("Validation", "Customer name is required.", parent=dlg); return
            customer.update({key: entry.get().strip() for key, entry in fields.items()})
            self._replace_records("customers.xlsx", self.cust_headers, self.customers); dlg.destroy()
        tk.Button(dlg, text="Save Changes", command=save, bg=PRIMARY, fg="white", bd=0, padx=14, pady=7).grid(row=4, column=0, columnspan=2, pady=18)

    def delete_selected_customer(self):
        if not self._require_admin():
            return
        customer = self._selected_record(self.tree_customers, self.customers)
        if not customer:
            return
        customer_id = clean_val(customer.get("id"))
        if not messagebox.askyesno("Delete Customer", f"Delete {clean_val(customer.get('name'))}? Existing orders are kept for audit history."):
            return
        self._replace_records("customers.xlsx", self.cust_headers, [c for c in self.customers if clean_val(c.get("id")) != customer_id])

    def print_selected_customer_receipt(self):
        customer = self._selected_record(self.tree_customers, self.customers)
        if not customer:
            return
        name = clean_val(customer.get("name"))
        order = next((o for o in reversed(self.orders) if clean_val(o.get("customer")) == name), None)
        if not order:
            messagebox.showinfo("No Receipt", "This customer has no order to print yet.")
            return
        self.generate_order_pdf(clean_val(order.get("id")))

    def edit_selected_employee(self):
        if not self._require_admin():
            return
        employee = self._selected_record(self.tree_employees, self.employees)
        if not employee:
            return
        dlg = tk.Toplevel(self); dlg.title("Edit Staff Member"); dlg.geometry("410x330"); dlg.configure(bg=self.colors["bg_card"]); dlg.grab_set()
        fields = {}
        specs = (("name", "Name"), ("phone", "Phone"), ("role", "Role"), ("status", "Status"), ("current_task", "Current Task"))
        for row, (key, label) in enumerate(specs):
            tk.Label(dlg, text=label + ":", bg=self.colors["bg_card"], fg=self.colors["text_main"]).grid(row=row, column=0, padx=18, pady=8, sticky="w")
            entry = tk.Entry(dlg, width=34); entry.insert(0, clean_val(employee.get(key))); entry.grid(row=row, column=1, padx=8, pady=8); fields[key] = entry
        def save():
            if not fields["name"].get().strip():
                messagebox.showerror("Validation", "Employee name is required.", parent=dlg); return
            employee.update({key: entry.get().strip() for key, entry in fields.items()})
            self._replace_records("employees.xlsx", self.emp_headers, self.employees); dlg.destroy()
        tk.Button(dlg, text="Save Changes", command=save, bg=PRIMARY, fg="white", bd=0, padx=14, pady=7).grid(row=6, column=0, columnspan=2, pady=16)

    def delete_selected_employee(self):
        if not self._require_admin():
            return
        employee = self._selected_record(self.tree_employees, self.employees)
        if not employee:
            return
        employee_id = clean_val(employee.get("id"))
        if not messagebox.askyesno("Delete Employee", f"Delete {clean_val(employee.get('name'))}? This cannot be undone."):
            return
        self._replace_records("employees.xlsx", self.emp_headers, [e for e in self.employees if clean_val(e.get("id")) != employee_id])

    def print_selected_employee_task(self):
        employee = self._selected_record(self.tree_employees, self.employees)
        if not employee:
            return
        if not REPORTLAB_INSTALLED:
            messagebox.showerror("Missing Library", "Install reportlab to print task slips."); return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"Task_{clean_val(employee.get('id'))}.pdf", filetypes=[("PDF Files", "*.pdf")])
        if not path:
            return
        pdf = canvas.Canvas(path, pagesize=A5); width, height = A5
        pdf.setFont("Helvetica-Bold", 18); pdf.drawString(40, height - 55, "JTQ EMPLOYEE TASK SLIP")
        pdf.setFont("Helvetica", 12)
        for index, (label, key) in enumerate((("Employee", "name"), ("Role", "role"), ("Status", "status"), ("Task", "current_task"))):
            pdf.drawString(40, height - 105 - index * 30, f"{label}: {clean_val(employee.get(key))}")
        pdf.drawString(40, height - 250, f"Printed: {datetime.now().strftime('%Y-%m-%d %H:%M')}"); pdf.save()
        messagebox.showinfo("Task Slip Saved", f"Saved to:\n{path}")

    # ==========================================
    # PDF GENERATOR LOGIC
    # ==========================================
    def generate_order_pdf(self, order_id=None):
        if not REPORTLAB_INSTALLED:
            messagebox.showerror("Missing Library", "To print PDF files, open your terminal/command prompt and run:\n\npip install reportlab")
            return

        if order_id:
            ord_id = order_id
        else:
            sel = self.tree_orders.selection()
            if not sel:
                messagebox.showwarning("Select Order", "Select an order from the active ledger first!")
                return
            ord_id = str(self.tree_orders.item(sel[0])["values"][0])

        # Get Full Order Data
        order_data = next((o for o in self.orders if clean_val(o.get("id")) == ord_id), None)
        if not order_data:
            return

        # Get Full Customer Data
        cust_name = clean_val(order_data.get("customer"))
        cust_data = next((c for c in self.customers if clean_val(c.get("name")) == cust_name), {})

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"Receipt_{ord_id}.pdf", title="Save Order PDF as...", filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            return

        try:
            c = canvas.Canvas(file_path, pagesize=A5)
            width, height = A5

            # Header
            c.setFont("Helvetica-Bold", 18)
            c.drawString(40, height - 50, "JHAGRA CREATION & FABRICS")
            c.setFont("Helvetica", 10)
            c.drawString(40, height - 65, "The Name Of Quality - JTQ")

            c.line(40, height - 75, width - 40, height - 75)

            # Info
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, height - 100, f"No: {ord_id}")
            c.drawString(150, height - 100, f"Name: {cust_name}")
            c.drawString(40, height - 120, f"Contact: {clean_val(cust_data.get('phone', 'N/A'))}")
            c.drawString(40, height - 140, f"Date: {datetime.now().strftime('%Y-%m-%d')}")

            # 9 Measurements (right column of the physical slip)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, height - 170, "Measurements (Inches)")
            c.setFont("Helvetica", 11)

            meas_y = height - 190
            m_list = [
                ("Length (لبادی)", cust_data.get("length")), ("Sleeve (چستین)", cust_data.get("sleeve")),
                ("Shoulder (تیرہ)", cust_data.get("shoulder")), ("Collar (کالر)", cust_data.get("collar")),
                ("Chest (چھاتاں)", cust_data.get("chest")), ("Waist (کمر)", cust_data.get("waist")),
                ("Daman (واشن)", cust_data.get("daman")), ("Shalwar Length (شلوار لیبا)", cust_data.get("shalwar_len")),
                ("Paancha (بائی پا)", cust_data.get("paancha"))
            ]

            for name, val in m_list:
                c.drawString(50, meas_y, f"{name}:")
                c.drawString(150, meas_y, str(clean_val(val)))
                c.line(145, meas_y - 2, 250, meas_y - 2)
                meas_y -= 20

            # Style selections (center/left visual elements of the physical slip)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(280, height - 170, "Selected Styles")
            c.setFont("Helvetica", 11)

            style_y = height - 190
            s_list = [
                ("Button", order_data.get("button_style")),
                ("Collar", order_data.get("collar_style")),
                ("Cuffs", order_data.get("cuff_style")),
                ("Pocket", order_data.get("pocket_style")),
                ("Daman", order_data.get("daman_style")),
                ("Stitch", order_data.get("stitching"))
            ]

            for name, val in s_list:
                c.drawString(280, style_y, f"{name}:")
                c.drawString(330, style_y, str(clean_val(val)))
                style_y -= 25

            c.save()
            messagebox.showinfo("Success", f"PDF Form generated successfully at:\n{file_path}")

        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    # ==========================================
    # LIVE STATS / TABLES
    # ==========================================
    def update_graphics_and_stats(self):
        valid_orders = [o for o in self.orders if o.get("id")]
        total = len(valid_orders)

        ready = sum(1 for o in valid_orders if "ready" in clean_val(o.get("status")).lower())
        prog = sum(1 for o in valid_orders if "progress" in clean_val(o.get("status")).lower())
        rem = total - ready - prog

        done_pct = int((ready / total) * 100) if total > 0 else 0
        prog_pct = int((prog / total) * 100) if total > 0 else 0
        rem_pct = int((rem / total) * 100) if total > 0 else 0

        self.chart_done.set_percentage(done_pct)
        self.chart_prog.set_percentage(prog_pct)
        self.chart_rem.set_percentage(rem_pct)

        self.lbl_done_pct.configure(text=f"{done_pct}%")
        self.lbl_prog_pct.configure(text=f"{prog_pct}%")
        self.lbl_rem_pct.configure(text=f"{rem_pct}%")

        self.tree_orders.delete(*self.tree_orders.get_children())
        for o in valid_orders:
            st = clean_val(o.get("status")).lower()
            tag = "status_ready" if "ready" in st else "status_prog" if "progress" in st else "status_pending"
            self.tree_orders.insert("", tk.END, values=list(o.values()), tags=(tag,))

        self.tree_customers.delete(*self.tree_customers.get_children())
        for c in self.customers:
            if c.get("id"):
                self.tree_customers.insert("", tk.END, values=list(c.values()))

        self.tree_employees.delete(*self.tree_employees.get_children())
        for e in self.employees:
            if e.get("id"):
                self.tree_employees.insert("", tk.END, values=list(e.values()))

    def update_clock(self):
        self.lbl_clock.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self.update_clock)

    # ==========================================
    # LANGUAGE ENGINE
    # ==========================================
    def on_language_change(self, event):
        selected_label = self.cbo_lang.get()
        label_to_code = {label: code for code, label in LANGUAGE_OPTIONS}
        self.current_lang = label_to_code.get(selected_label, self.current_lang)
        self.apply_language_pack()

    def apply_language_pack(self):
        # Some language packs are intentionally partial; preserve English labels
        # for any key that has not been translated yet.
        t = {**TRANSLATIONS["en"], **TRANSLATIONS.get(self.current_lang, {})}
        label_to_code = {label: code for code, label in LANGUAGE_OPTIONS}
        code_to_label = {code: label for code, label in LANGUAGE_OPTIONS}
        self.cbo_lang.set(code_to_label.get(self.current_lang, code_to_label[LANGUAGE_OPTIONS[0][0]]))

        for _, (btn, lang_key) in self.nav_buttons.items():
            btn.configure(text=t[lang_key])

        self.lbl_dash_title.configure(text=t["dash_title"])
        self.lbl_dash_sub.configure(text=t["dash_sub"])
        self.lbl_done_title.configure(text=t["work_done"])
        self.lbl_prog_title.configure(text=t["in_prog"])
        self.lbl_rem_title.configure(text=t["work_rem"])
        self.lbl_ledger_head.configure(text=t["active_ledger"])

        self.lbl_cust_title.configure(text=t["cust_title"])
        self.lbl_cust_sub.configure(text=t["cust_sub"])
        self.btn_cust_modal.configure(text=t["btn_add_cust"])
        self.btn_new_card.configure(text=t["btn_new_card"])
        if hasattr(self, "order_card"):
            self.order_card.set_language(self.current_lang)

        self.lbl_emp_title.configure(text=t["emp_title"])
        self.lbl_emp_sub.configure(text=t["emp_sub"])
        self.btn_task_modal.configure(text=t["btn_assign_task"])
        self.btn_emp_modal.configure(text=t["btn_add_emp"])

        self.lbl_admin_title.configure(text=t["admin_title"])
        self.lbl_admin_sub.configure(text=t["admin_sub"])
        self.lbl_theme_label.configure(text=t.get("theme_label", self.lbl_theme_label.cget("text")))
        self.lbl_language_label.configure(text=t.get("language_label", self.lbl_language_label.cget("text")))

        self.tree_orders.heading("id", text=t["tbl_ord_id"])
        self.tree_orders.heading("customer", text=t["tbl_cust"])
        self.tree_orders.heading("garment", text=t["tbl_garment"])
        self.tree_orders.heading("status", text=t["tbl_status"])
        self.tree_orders.heading("tailor", text=t["tbl_tailor"])


if __name__ == "__main__":
    app = AtelierERPApp()
    app.mainloop()
