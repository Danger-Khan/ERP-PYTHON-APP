"""Reusable Tkinter view: the digital New Customer / Order Card screen.

Digitizes the physical JTQ paper slip into a form with seven sections:
Customer Info, Garment Type, Measurements, Style Options, Special Notes,
Delivery, Payment, and the action buttons row. All business logic lives in
app/services/order_card_service.py so the desktop GUI and Flask API share it.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from app.services import order_card_service as svc
    from app.lang import ORDER_CARD_TRANSLATIONS
except ImportError:
    from services import order_card_service as svc
    from lang import ORDER_CARD_TRANSLATIONS


# ---------------------------------------------------------------------------
# Segmented / chip widgets (Material-style selectable pills)
# ---------------------------------------------------------------------------

class ChipGroup:
    """Single-select segmented button group (radio behavior)."""
    __slots__ = ('colors', 'accent', 'font', 'value', 'buttons')

    def __init__(self, parent, options, colors, font, accent, font_size=9):
        self.colors = colors
        self.accent = accent
        self.font = font
        self.value = tk.StringVar(value=options[0] if options else "")
        self.buttons = []
        for opt in options:
            btn = tk.Button(parent, text=opt, bd=0, cursor="hand2", padx=12, pady=5,
                            font=(font, font_size, "bold"),
                            command=lambda o=opt: self.select(o))
            btn.pack(side=tk.LEFT, padx=3, pady=3)
            self.buttons.append((opt, btn))
        self.refresh()

    def select(self, value):
        self.value.set(value)
        self.refresh()

    def refresh(self):
        selected = self.value.get()
        for opt, btn in self.buttons:
            if opt == selected:
                btn.configure(bg=self.accent, fg="white",
                              activebackground=self.accent, activeforeground="white")
            else:
                btn.configure(bg=self.colors["bg_card"], fg=self.colors["text_main"],
                              activebackground=self.colors["bg_body"],
                              activeforeground=self.colors["text_main"])

    def get(self):
        return self.value.get()

    def set(self, value):
        for opt, _ in self.buttons:
            if opt == value:
                self.select(value)
                return


class ChipCheckGroup:
    """Multi-select toggle chip group (checkbox behavior)."""
    __slots__ = ('colors', 'accent', 'font', 'vars', 'buttons')

    def __init__(self, parent, options, colors, font, accent, font_size=9):
        self.colors = colors
        self.accent = accent
        self.font = font
        self.vars = {opt: tk.BooleanVar(value=False) for opt in options}
        self.buttons = {}
        for opt in options:
            btn = tk.Button(parent, text="☐ " + opt, bd=0, cursor="hand2", padx=12, pady=5,
                            font=(font, font_size),
                            command=lambda o=opt: self.toggle(o))
            btn.pack(side=tk.LEFT, padx=3, pady=3)
            self.buttons[opt] = btn
        self.refresh()

    def toggle(self, opt):
        self.vars[opt].set(not self.vars[opt].get())
        self.refresh()

    def refresh(self):
        for opt, btn in self.buttons.items():
            if self.vars[opt].get():
                btn.configure(text="✔ " + opt, bg=self.accent, fg="white",
                              activebackground=self.accent, activeforeground="white")
            else:
                btn.configure(text="☐ " + opt, bg=self.colors["bg_card"], fg=self.colors["text_main"],
                              activebackground=self.colors["bg_body"],
                              activeforeground=self.colors["text_main"])

    def selected(self):
        return [opt for opt, var in self.vars.items() if var.get()]

    def toggle_all_off(self):
        for var in self.vars.values():
            var.set(False)
        self.refresh()


class ScrollableCardSection(tk.Frame):
    """Vertical scroll container with a styled inner frame."""
    __slots__ = ('colors', 'canvas', 'scrollbar', 'inner', '_window_id')

    def __init__(self, parent, colors):
        super().__init__(parent, bg=colors["bg_body"])
        self.colors = colors
        self.canvas = tk.Canvas(self, bg=colors["bg_body"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=colors["bg_body"])

        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling (bound to this widget, not globally, so theme
        # rebuilds never leave stale handlers behind).
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.inner.bind("<MouseWheel>", self._on_mousewheel)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self._window_id, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ---------------------------------------------------------------------------
# Order Card View
# ---------------------------------------------------------------------------

class OrderCardView(tk.Frame):
    """Full order-card form screen, mounted into the ERP main content area."""
    __slots__ = ('app', 'colors', 'font', 'primary', 'success', 'warning', 'danger',
                 'lbl_title', 'lbl_sub', 'cbo_customer', 'ent_customer_id', 'ent_name', 
                 'ent_phone', 'ent_date', 'ent_address', 'ent_tailor', 'cbo_status',
                 'garment_group', 'meas_entries', 'style_groups', 'txt_notes',
                 'ent_delivery_date', 'ent_delivery_time', 'ent_delivered_by',
                 'cbo_delivery_status', 'ent_total', 'ent_advance', 'lbl_remaining',
                 'btn_save_order', 'btn_print', 'btn_clear')

    def __init__(self, parent, app, colors, font_family, primary, success, warning, danger):
        super().__init__(parent, bg=colors["bg_body"])
        self.app = app
        self.colors = colors
        self.font = font_family
        self.primary = primary
        self.success = success
        self.warning = warning
        self.danger = danger

        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self):
        scroll = ScrollableCardSection(self, self.colors)
        scroll.pack(fill=tk.BOTH, expand=True)
        body = scroll.inner

        # --- Header ---
        hdr = tk.Frame(body, bg=self.colors["bg_body"])
        hdr.pack(fill=tk.X, padx=20, pady=(14, 4))
        self.lbl_title = tk.Label(hdr, text="New Order", font=(self.font, 18, "bold"),
                                  bg=self.colors["bg_body"], fg=self.colors["text_main"])
        self.lbl_title.pack(anchor="w")
        self.lbl_sub = tk.Label(hdr, text="Digital order card — mirroring the JTQ paper slip",
                                font=(self.font, 9),
                                bg=self.colors["bg_body"], fg=self.colors["text_muted"])
        self.lbl_sub.pack(anchor="w")

        # --- Section 1: Customer Information ---
        card = self._card(body, "1 · Customer Information")
        grid = tk.Frame(card, bg=self.colors["bg_card"])
        grid.pack(fill=tk.X)

        tk.Label(grid, text="Registered Customer *", font=(self.font, 8, "bold"),
                 bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(
                     row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.cbo_customer = ttk.Combobox(grid, state="readonly", width=28)
        self.cbo_customer.grid(row=0, column=1, sticky="ew", pady=4)
        self.cbo_customer.bind("<<ComboboxSelected>>", self.on_customer_selected)
        self.ent_customer_id = self._row_entry(grid, 1, "Customer ID", read_only=True)
        self.ent_name = self._row_entry(grid, 2, "Name", read_only=True)
        self.ent_phone = self._row_entry(grid, 3, "Mobile Number", read_only=True)
        self.ent_date = self._row_entry(grid, 4, "Date")
        self.ent_address = self._row_entry(grid, 5, "Address", read_only=True)
        self.ent_tailor = self._row_entry(grid, 6, "Assign Tailor")

        row_status = tk.Frame(card, bg=self.colors["bg_card"])
        row_status.pack(fill=tk.X, pady=(4, 0))
        tk.Label(row_status, text="Order Status:", font=(self.font, 8, "bold"),
                 bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(side=tk.LEFT, padx=(0, 8))
        self.cbo_status = ttk.Combobox(row_status, values=svc.ORDER_STATUSES,
                                       state="readonly", width=18)
        self.cbo_status.current(0)
        self.cbo_status.pack(side=tk.LEFT)

        # --- Section 2: Garment Type ---
        card = self._card(body, "2 · Garment Type  (select one or more)")
        wrap_g = tk.Frame(card, bg=self.colors["bg_card"])
        wrap_g.pack(fill=tk.X)
        self.garment_group = ChipCheckGroup(wrap_g, svc.GARMENT_OPTIONS, self.colors,
                                            self.font, self.primary)

        # --- Section 3: Measurements ---
        card = self._card(body, "3 · Measurements  (inches — two-column grid)")
        meas_grid = tk.Frame(card, bg=self.colors["bg_card"])
        meas_grid.pack(fill=tk.X)
        self.meas_entries = {}
        for idx, (key, label) in enumerate(svc.MEASUREMENT_FIELDS):
            row = idx // 2
            col = (idx % 2) * 2
            tk.Label(meas_grid, text=label, font=(self.font, 9),
                     bg=self.colors["bg_card"], fg=self.colors["text_main"]).grid(
                         row=row, column=col, padx=(6, 8), pady=5, sticky="e")
            entry = tk.Entry(meas_grid, width=16, justify="center", font=(self.font, 10))
            entry.grid(row=row, column=col + 1, padx=(0, 12), pady=5, sticky="w")
            self.meas_entries[key] = entry
        meas_grid.columnconfigure(1, weight=1)
        meas_grid.columnconfigure(3, weight=1)

        # --- Section 4: Style Options ---
        card = self._card(body, "4 · Style Options")
        self.style_groups = {}
        for key, (label, options) in svc.STYLE_GROUPS.items():
            rowf = tk.Frame(card, bg=self.colors["bg_card"])
            rowf.pack(fill=tk.X, pady=2)
            tk.Label(rowf, text=label + ":", width=16, anchor="w",
                     font=(self.font, 8, "bold"),
                     bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(side=tk.LEFT)
            wrap = tk.Frame(rowf, bg=self.colors["bg_card"])
            wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)
            group = ChipGroup(wrap, options, self.colors, self.font, self.primary)
            self.style_groups[key] = group

        # --- Section 5: Special Notes ---
        card = self._card(body, "5 · Special Notes")
        self.txt_notes = tk.Text(card, height=5, wrap=tk.WORD, font=(self.font, 10),
                                 bg=self.colors["bg_card"], fg=self.colors["text_main"],
                                 insertbackground=self.colors["text_main"],
                                 highlightthickness=1, highlightbackground=self.colors["border"])
        self.txt_notes.pack(fill=tk.X, pady=(0, 4))

        # --- Section 6: Delivery ---
        card = self._card(body, "6 · Delivery")
        grid = tk.Frame(card, bg=self.colors["bg_card"])
        grid.pack(fill=tk.X)
        self.ent_delivery_date = self._row_entry(grid, 0, "Delivery Date")
        self.ent_delivery_time = self._row_entry(grid, 1, "Delivery Time")
        self.ent_delivered_by = self._row_entry(grid, 2, "Delivered By")

        row_del_status = tk.Frame(card, bg=self.colors["bg_card"])
        row_del_status.pack(fill=tk.X, pady=(4, 0))
        tk.Label(row_del_status, text="Delivery Status:", font=(self.font, 8, "bold"),
                 bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(side=tk.LEFT, padx=(0, 8))
        self.cbo_delivery_status = ttk.Combobox(row_del_status, values=svc.DELIVERY_STATUSES,
                                                state="readonly", width=18)
        self.cbo_delivery_status.current(0)
        self.cbo_delivery_status.pack(side=tk.LEFT)

        # --- Section 7: Payment ---
        card = self._card(body, "7 · Payment")
        pay = tk.Frame(card, bg=self.colors["bg_card"])
        pay.pack(fill=tk.X)
        tk.Label(pay, text="Total Amount (PKR):", font=(self.font, 9),
                 bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(side=tk.LEFT, padx=(0, 8))
        self.ent_total = tk.Entry(pay, width=12, justify="right", font=(self.font, 10))
        self.ent_total.pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(pay, text="Advance Paid (PKR):", font=(self.font, 9),
                 bg=self.colors["bg_card"], fg=self.colors["text_main"]).pack(side=tk.LEFT, padx=(0, 8))
        self.ent_advance = tk.Entry(pay, width=12, justify="right", font=(self.font, 10))
        self.ent_advance.pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(pay, text="Remaining:", font=(self.font, 9, "bold"),
                 bg=self.colors["bg_card"], fg=self.colors["text_muted"]).pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_remaining = tk.Label(pay, text="PKR 0.00", font=(self.font, 12, "bold"),
                                      bg=self.colors["bg_card"], fg=self.primary)
        self.lbl_remaining.pack(side=tk.LEFT)

        self.ent_total.bind("<KeyRelease>", lambda e: self.update_remaining())
        self.ent_advance.bind("<KeyRelease>", lambda e: self.update_remaining())
        self.ent_total.bind("<FocusOut>", lambda e: self.update_remaining())
        self.ent_advance.bind("<FocusOut>", lambda e: self.update_remaining())

        # --- Section 8: Action buttons ---
        actions = tk.Frame(body, bg=self.colors["bg_body"])
        actions.pack(fill=tk.X, padx=20, pady=(16, 24))
        self.btn_save_order = self._action_button(actions, "Save Order", self.success, self.on_save_order)
        self.btn_print = self._action_button(actions, "Print Receipt", self.warning, self.on_print_receipt)
        self.btn_clear = self._action_button(actions, "Clear Form", self.danger, self.on_clear)

        self.reset_form()

    # ------------------------------------------------------------- helpers
    def _card(self, parent, title):
        card = tk.Frame(parent, bg=self.colors["bg_card"],
                        highlightbackground=self.colors["border"], highlightthickness=1,
                        padx=16, pady=12)
        card.pack(fill=tk.X, padx=20, pady=6)
        lbl = tk.Label(card, text=title, font=(self.font, 10, "bold"),
                       bg=self.colors["bg_card"], fg=self.colors["text_main"])
        lbl.pack(anchor="w", pady=(0, 6))
        return card

    def _row_entry(self, grid, row, label_text, read_only=False):
        tk.Label(grid, text=label_text, font=(self.font, 8, "bold"),
                 bg=self.colors["bg_card"], fg=self.colors["text_muted"]).grid(
                     row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        state = "readonly" if read_only else "normal"
        entry = tk.Entry(grid, width=26, font=(self.font, 10), state=state,
                         bg=self.colors["bg_card"] if read_only else "white",
                         fg=self.colors["text_main"])
        entry.grid(row=row, column=1, sticky="ew", pady=4)
        grid.columnconfigure(1, weight=1)
        return entry

    def _action_button(self, parent, text, color, command):
        btn = tk.Button(parent, text=text, bg=color, fg="white",
                        font=(self.font, 10, "bold"), bd=0, padx=16, pady=8,
                        cursor="hand2", command=command)
        btn.pack(side=tk.LEFT, padx=(0, 10))
        return btn

    # -------------------------------------------------------- form behavior
    def reset_form(self):
        """Clears order-only fields; customers are selected from Customer Hub."""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")

        customers = [f"{c.get('id', '')} - {c.get('name', '')}" for c in self.app.customers
                     if str(c.get('id') or '').strip() and str(c.get('name') or '').strip()]
        self.cbo_customer["values"] = customers
        self.cbo_customer.set("")
        self._set_entry(self.ent_customer_id, "")

        self._set_entry(self.ent_name, "")
        self._set_entry(self.ent_phone, "")
        self.ent_date.delete(0, tk.END)
        self.ent_date.insert(0, today)
        self._set_entry(self.ent_address, "")
        self.ent_tailor.delete(0, tk.END)
        self.cbo_status.current(0)

        self.garment_group.toggle_all_off()

        for entry in self.meas_entries.values():
            entry.delete(0, tk.END)

        for group in self.style_groups.values():
            group.set(group.buttons[0][0])  # default = first option

        self.txt_notes.delete("1.0", tk.END)

        self.ent_delivery_date.delete(0, tk.END)
        self.ent_delivery_time.delete(0, tk.END)
        self.ent_delivered_by.delete(0, tk.END)
        self.cbo_delivery_status.current(0)

        self.ent_total.delete(0, tk.END)
        self.ent_advance.delete(0, tk.END)
        self.update_remaining()

    def _set_entry(self, entry, value):
        state = str(entry.cget("state"))
        if state == "readonly":
            entry.configure(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, value)
        if state == "readonly":
            entry.configure(state="readonly")

    def on_customer_selected(self, event=None):
        customer_id = self.cbo_customer.get().split(" - ", 1)[0]
        customer = next((c for c in self.app.customers if str(c.get("id") or "") == customer_id), None)
        if not customer:
            return
        self._set_entry(self.ent_customer_id, customer_id)
        self._set_entry(self.ent_name, str(customer.get("name") or ""))
        self._set_entry(self.ent_phone, str(customer.get("phone") or ""))
        self._set_entry(self.ent_address, str(customer.get("address") or ""))

    def update_remaining(self):
        total = svc.clean_num(self.ent_total.get())
        advance = svc.clean_num(self.ent_advance.get())
        remaining = svc.compute_remaining(total, advance)
        self.lbl_remaining.configure(text=f"PKR {remaining:.2f}")

    def collect_form(self):
        """Builds the flat form dict consumed by the order card service."""
        return {
            "name": self.ent_name.get(),
            "phone": self.ent_phone.get(),
            "date": self.ent_date.get(),
            "address": self.ent_address.get(),
            "garments": self.garment_group.selected(),
            **{key: entry.get() for key, entry in self.meas_entries.items()},
            **{key: group.get() for key, group in self.style_groups.items()},
            "status": self.cbo_status.get(),
            "tailor": self.ent_tailor.get(),
            "notes": self.txt_notes.get("1.0", tk.END).strip(),
            "delivery_date": self.ent_delivery_date.get(),
            "delivery_time": self.ent_delivery_time.get(),
            "delivered_by": self.ent_delivered_by.get(),
            "delivery_status": self.cbo_delivery_status.get(),
            "total": self.ent_total.get(),
            "advance": self.ent_advance.get(),
        }

    def validate_and_show(self, form):
        errors = svc.validate(form)
        if errors:
            messagebox.showerror("Validation Error",
                                 "\n".join(f"• {e}" for e in errors), parent=self)
        return not errors

    # ----------------------------------------------------------- actions
    def on_save_order(self):
        """Persists customer + order + measurements + styles together."""
        form = self.collect_form()
        if not self.validate_and_show(form):
            return
        try:
            customer_id, order_id = svc.save_order_for_customer(
                self.app.excel_mgr, self.app.customers, self.app.orders, form,
                customer_id=self.ent_customer_id.get())
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
            return
        except Exception as e:
            messagebox.showerror("Save Error", str(e), parent=self)
            return
        self.app.reload_all_data()
        messagebox.showinfo("Order Saved",
                            f"Order {order_id} saved for customer {customer_id}.",
                            parent=self)
        self.reset_form()
        self.app.show_section("dashboard")

    def on_print_receipt(self):
        """Saves the order first, then writes an A5 PDF receipt."""
        form = self.collect_form()
        if not self.validate_and_show(form):
            return
        try:
            customer_id, order_id = svc.save_order_for_customer(
                self.app.excel_mgr, self.app.customers, self.app.orders, form,
                customer_id=self.ent_customer_id.get())
        except Exception as e:
            messagebox.showerror("Save Error", str(e), parent=self)
            return

        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".pdf",
            initialfile=f"Receipt_{order_id}.pdf", title="Save Order Receipt as...",
            filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            return

        try:
            svc.write_receipt_pdf(file_path, form, customer_id, order_id)
        except ImportError:
            messagebox.showerror(
                "Missing Library",
                "To print PDF files, run:  pip install reportlab", parent=self)
            return
        except Exception as e:
            messagebox.showerror("PDF Error", str(e), parent=self)
            return

        self.app.reload_all_data()
        self.reset_form()
        messagebox.showinfo("Receipt Saved",
                            f"Receipt generated at:\n{file_path}", parent=self)

    def on_clear(self):
        self.reset_form()

    # ----------------------------------------------------------- language
    def set_language(self, lang):
        title, sub = ORDER_CARD_TRANSLATIONS.get(lang, ORDER_CARD_TRANSLATIONS["en"])
        self.lbl_title.configure(text=title)
        self.lbl_sub.configure(text=sub)
