"""Reusable Tkinter view: the digital New Customer / Order Card screen.

Digitizes the physical JTQ paper slip into a form with six sections:
Customer Info, Garment Type, Style Options, Special Notes, Delivery,
Payment, and the action buttons row. All business logic lives in
app/services/order_card_service.py so the desktop GUI and Flask API
share it.

Measurements are not entered OR displayed here — the Customer Hub /
New Customer card is the single place they're recorded, to avoid two
screens showing the same numbers. Saving an order still snapshots the
selected customer's current measurements into measurements.xlsx behind
the scenes (see _customer_measurements), so per-order history is kept
without duplicating the data entry.

Full language switching: every label/heading/button on this screen, and
every garment/style chip, re-renders in the active language (see
set_language / TRANSLATIONS). Values that get WRITTEN to the spreadsheet
(garment names, style choices, order/delivery status) always stay their
canonical English string internally — only the on-screen text changes —
so status-based logic elsewhere in the app (dashboard charts, row
coloring, "Mark Ready" etc., which compare against literal English
strings) never breaks just because the UI is shown in Urdu.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from services import order_card_service as svc
    from lang import ORDER_CARD_TRANSLATIONS, TRANSLATIONS
except ImportError:
    from app.services import order_card_service as svc
    from app.lang import ORDER_CARD_TRANSLATIONS, TRANSLATIONS

# Maps a customers.xlsx column to the order-card measurement key it feeds
# (mirrors the reverse of order_card_service.customer_row's "legacy" map)
# as (customer_field, order_card_key, display_label).
CUSTOMER_MEASUREMENT_FIELDS = [
    ("length", "lambai", "Lambai (Length)"),
    ("chest", "chest", "Chest"),
    ("waist", "waist", "Waist"),
    ("shoulder", "shoulder", "Shoulder"),
    ("sleeve", "sleeve", "Sleeve"),
    ("collar", "collar", "Collar"),
    ("daman", "daman", "Daman"),
    ("shalwar_len", "shalwar_length", "Shalwar Length"),
    ("paancha", "paancha", "Paancha"),
]

# --- i18n lookup tables: canonical English value (stored/persisted) -> ----
# --- TRANSLATIONS key (displayed). Positional lists line up 1:1 with the ---
# --- order_card_service constants they translate.                       ---
GARMENT_LABEL_KEYS = [
    "garment_kameez", "garment_shalwar", "garment_coat", "garment_waistcoat",
    "garment_pant", "garment_shirt", "garment_others",
]  # matches svc.GARMENT_OPTIONS order

STYLE_GROUP_LABEL_KEYS = {
    "button_style": "style_button_style_label",
    "collar_style": "style_collar_type_label",
    "cuff_style": "style_cuff_type_label",
    "pocket_style": "style_pocket_type_label",
    "daman_style": "style_daman_type_label",
    "stitching": "style_stitching_label",
    "sleeve_type": "style_sleeve_style_label",
    "shalwar_type": "style_shalwar_style_label",
}

STYLE_OPTION_LABEL_KEYS = {
    "button_style": ["style_button_baz", "style_button_karh", "style_normal", "style_none"],
    "collar_style": ["style_normal", "style_collar_chinese", "style_collar_sherwani", "style_collar_round"],
    "cuff_style": ["style_cuff_round", "style_cuff_square", "style_normal", "style_none"],
    "pocket_style": ["style_pocket_one", "style_pocket_two", "style_pocket_hidden", "style_none"],
    "daman_style": ["style_daman_square", "style_daman_round", "style_normal", "style_none"],
    "stitching": ["style_stitch_single", "style_stitch_double", "style_stitch_choka", "style_stitch_triple"],
    "sleeve_type": ["style_sleeve_full", "style_sleeve_half", "style_sleeve_short", "style_none"],
    "shalwar_type": ["style_normal", "style_shalwar_churidar", "style_shalwar_patiala", "style_shalwar_simple"],
}  # each list is positional to svc.STYLE_GROUPS[key][1]

ORDER_STATUS_LABEL_KEYS = ["status_pending", "status_in_progress", "status_ready", "status_delivered"]
DELIVERY_STATUS_LABEL_KEYS = ["status_not_delivered", "status_delivered", "status_partial"]


def translate(lang, key):
    """English-first lookup so a partial language pack never KeyErrors."""
    return TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)


# ---------------------------------------------------------------------------
# Segmented / chip widgets (Material-style selectable pills)
#
# Each chip's underlying VALUE (used by .get()/.selected(), and ultimately
# written to the spreadsheet) is always the canonical English string from
# order_card_service. Only the button's displayed LABEL changes with
# relabel() on a language switch — the two are deliberately decoupled.
# ---------------------------------------------------------------------------

class ChipGroup:
    """Single-select segmented button group (radio behavior)."""
    __slots__ = ('colors', 'accent', 'font', 'value', 'options', 'buttons')

    def __init__(self, parent, options, labels, colors, font, accent, font_size=9):
        self.colors = colors
        self.accent = accent
        self.font = font
        self.options = list(options)
        self.value = tk.StringVar(value=self.options[0] if self.options else "")
        self.buttons = {}
        for opt, label in zip(self.options, labels):
            btn = tk.Button(parent, text=label, bd=0, cursor="hand2", padx=12, pady=5,
                            font=(font, font_size, "bold"),
                            command=lambda o=opt: self.select(o))
            btn.pack(side=tk.LEFT, padx=3, pady=3)
            self.buttons[opt] = btn
        self.refresh()

    def select(self, value):
        self.value.set(value)
        self.refresh()

    def refresh(self):
        selected = self.value.get()
        for opt, btn in self.buttons.items():
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
        if value in self.buttons:
            self.select(value)

    def relabel(self, labels):
        """Updates each button's displayed text in place; the canonical
        value (and current selection) is untouched."""
        for opt, label in zip(self.options, labels):
            self.buttons[opt].configure(text=label)


class ChipCheckGroup:
    """Multi-select toggle chip group (checkbox behavior)."""
    __slots__ = ('colors', 'accent', 'font', 'vars', 'options', 'labels', 'buttons')

    def __init__(self, parent, options, labels, colors, font, accent, font_size=9):
        self.colors = colors
        self.accent = accent
        self.font = font
        self.options = list(options)
        self.vars = {opt: tk.BooleanVar(value=False) for opt in self.options}
        self.labels = dict(zip(self.options, labels))
        self.buttons = {}
        for opt in self.options:
            btn = tk.Button(parent, text="☐ " + self.labels[opt], bd=0, cursor="hand2", padx=12, pady=5,
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
            label = self.labels[opt]
            if self.vars[opt].get():
                btn.configure(text="✔ " + label, bg=self.accent, fg="white",
                              activebackground=self.accent, activeforeground="white")
            else:
                btn.configure(text="☐ " + label, bg=self.colors["bg_card"], fg=self.colors["text_main"],
                              activebackground=self.colors["bg_body"],
                              activeforeground=self.colors["text_main"])

    def selected(self):
        return [opt for opt, var in self.vars.items() if var.get()]

    def toggle_all_off(self):
        for var in self.vars.values():
            var.set(False)
        self.refresh()

    def relabel(self, labels):
        """Updates each button's displayed text in place; canonical values
        and the current checked/unchecked state are untouched."""
        self.labels = dict(zip(self.options, labels))
        self.refresh()


class TranslatedCombobox:
    """A readonly ttk.Combobox whose selectable VALUES stay a fixed set of
    canonical English strings (used for storage/business logic elsewhere in
    the app — order/delivery status is compared literally in several
    places), while the text shown to the user can be relabeled to another
    language without changing which canonical value is selected."""
    __slots__ = ('values', 'combo')

    def __init__(self, parent, values, labels, **kwargs):
        self.values = list(values)
        self.combo = ttk.Combobox(parent, values=list(labels), state="readonly", **kwargs)

    def pack(self, *a, **k):
        self.combo.pack(*a, **k)

    def current(self, index=None):
        if index is None:
            return self.combo.current()
        self.combo.current(index)

    def get(self):
        idx = self.combo.current()
        if 0 <= idx < len(self.values):
            return self.values[idx]
        return self.values[0] if self.values else ""

    def relabel(self, labels):
        idx = self.combo.current()
        self.combo["values"] = list(labels)
        if 0 <= idx < len(labels):
            self.combo.current(idx)


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
                 'garment_group', 'style_groups', 'txt_notes',
                 'ent_delivery_date', 'ent_delivery_time', 'ent_delivered_by',
                 'cbo_delivery_status', 'ent_total', 'ent_advance', 'lbl_remaining',
                 'btn_save_order', 'btn_print', 'btn_clear',
                 '_section_labels', '_field_labels', '_style_row_labels')

    def __init__(self, parent, app, colors, font_family, primary, success, warning, danger):
        super().__init__(parent, bg=colors["bg_body"])
        self.app = app
        self.colors = colors
        self.font = font_family
        self.primary = primary
        self.success = success
        self.warning = warning
        self.danger = danger

        self._section_labels = {}   # translation key -> (number, Label widget)
        self._field_labels = {}     # translation key -> Label widget
        self._style_row_labels = {}  # style group key -> Label widget

        self._build()

    # ------------------------------------------------------------------ i18n
    def _t(self, key):
        lang = getattr(self.app, "current_lang", "en")
        return translate(lang, key)

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
        card = self._card(body, 1, "oc_sec_customer")
        grid = tk.Frame(card, bg=self.colors["bg_card"])
        grid.pack(fill=tk.X)

        self._field_labels["oc_lbl_registered_customer"] = tk.Label(
            grid, text=self._t("oc_lbl_registered_customer"), font=(self.font, 8, "bold"),
            bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self._field_labels["oc_lbl_registered_customer"].grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.cbo_customer = ttk.Combobox(grid, state="readonly", width=28)
        self.cbo_customer.grid(row=0, column=1, sticky="ew", pady=4)
        self.cbo_customer.bind("<<ComboboxSelected>>", self.on_customer_selected)
        self.ent_customer_id = self._row_entry(grid, 1, "oc_lbl_customer_id", read_only=True)
        self.ent_name = self._row_entry(grid, 2, "oc_lbl_name", read_only=True)
        self.ent_phone = self._row_entry(grid, 3, "oc_lbl_mobile", read_only=True)
        self.ent_date = self._row_entry(grid, 4, "oc_lbl_date")
        self.ent_address = self._row_entry(grid, 5, "oc_lbl_address", read_only=True)
        self.ent_tailor = self._row_entry(grid, 6, "oc_lbl_tailor")

        row_status = tk.Frame(card, bg=self.colors["bg_card"])
        row_status.pack(fill=tk.X, pady=(4, 0))
        self._field_labels["oc_lbl_order_status"] = tk.Label(
            row_status, text=self._t("oc_lbl_order_status"), font=(self.font, 8, "bold"),
            bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self._field_labels["oc_lbl_order_status"].pack(side=tk.LEFT, padx=(0, 8))
        self.cbo_status = TranslatedCombobox(row_status, svc.ORDER_STATUSES,
                                             self._labels_for(ORDER_STATUS_LABEL_KEYS), width=18)
        self.cbo_status.current(0)
        self.cbo_status.pack(side=tk.LEFT)

        # Measurements aren't shown or re-entered here — the Customer card
        # (Customer Hub) is the single place they're recorded. Saving an
        # order still snapshots them into measurements.xlsx by looking the
        # selected customer's values up directly (see _customer_measurements).

        # --- Section 2: Garment Type ---
        card = self._card(body, 2, "oc_sec_garment")
        wrap_g = tk.Frame(card, bg=self.colors["bg_card"])
        wrap_g.pack(fill=tk.X)
        self.garment_group = ChipCheckGroup(wrap_g, svc.GARMENT_OPTIONS,
                                            self._labels_for(GARMENT_LABEL_KEYS),
                                            self.colors, self.font, self.primary)

        # --- Section 3: Style Options ---
        card = self._card(body, 3, "oc_sec_style")
        self.style_groups = {}
        for key, (_, options) in svc.STYLE_GROUPS.items():
            rowf = tk.Frame(card, bg=self.colors["bg_card"])
            rowf.pack(fill=tk.X, pady=2)
            row_lbl = tk.Label(rowf, text=self._t(STYLE_GROUP_LABEL_KEYS[key]) + ":", width=16, anchor="w",
                               font=(self.font, 8, "bold"),
                               bg=self.colors["bg_card"], fg=self.colors["text_main"])
            row_lbl.pack(side=tk.LEFT)
            self._style_row_labels[key] = row_lbl
            wrap = tk.Frame(rowf, bg=self.colors["bg_card"])
            wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)
            group = ChipGroup(wrap, options, self._labels_for(STYLE_OPTION_LABEL_KEYS[key]),
                              self.colors, self.font, self.primary)
            self.style_groups[key] = group

        # --- Section 4: Special Notes ---
        card = self._card(body, 4, "oc_sec_notes")
        self.txt_notes = tk.Text(card, height=5, wrap=tk.WORD, font=(self.font, 10),
                                 bg=self.colors["bg_card"], fg=self.colors["text_main"],
                                 insertbackground=self.colors["text_main"],
                                 highlightthickness=1, highlightbackground=self.colors["border"])
        self.txt_notes.pack(fill=tk.X, pady=(0, 4))

        # --- Section 5: Delivery ---
        card = self._card(body, 5, "oc_sec_delivery")
        grid = tk.Frame(card, bg=self.colors["bg_card"])
        grid.pack(fill=tk.X)
        self.ent_delivery_date = self._row_entry(grid, 0, "oc_lbl_delivery_date")
        self.ent_delivery_time = self._row_entry(grid, 1, "oc_lbl_delivery_time")
        self.ent_delivered_by = self._row_entry(grid, 2, "oc_lbl_delivered_by")

        row_del_status = tk.Frame(card, bg=self.colors["bg_card"])
        row_del_status.pack(fill=tk.X, pady=(4, 0))
        self._field_labels["oc_lbl_delivery_status"] = tk.Label(
            row_del_status, text=self._t("oc_lbl_delivery_status"), font=(self.font, 8, "bold"),
            bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self._field_labels["oc_lbl_delivery_status"].pack(side=tk.LEFT, padx=(0, 8))
        self.cbo_delivery_status = TranslatedCombobox(
            row_del_status, svc.DELIVERY_STATUSES,
            self._labels_for(DELIVERY_STATUS_LABEL_KEYS), width=18)
        self.cbo_delivery_status.current(0)
        self.cbo_delivery_status.pack(side=tk.LEFT)

        # --- Section 6: Payment ---
        card = self._card(body, 6, "oc_sec_payment")
        pay = tk.Frame(card, bg=self.colors["bg_card"])
        pay.pack(fill=tk.X)
        self._field_labels["oc_lbl_total"] = tk.Label(
            pay, text=self._t("oc_lbl_total"), font=(self.font, 9),
            bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self._field_labels["oc_lbl_total"].pack(side=tk.LEFT, padx=(0, 8))
        self.ent_total = tk.Entry(pay, width=12, justify="right", font=(self.font, 10),
                                  bg=self.colors["bg_body"], fg=self.colors["text_main"],
                                  insertbackground=self.colors["text_main"], relief="flat",
                                  highlightthickness=1, highlightbackground=self.colors["border"])
        self.ent_total.pack(side=tk.LEFT, padx=(0, 16))
        self._field_labels["oc_lbl_advance"] = tk.Label(
            pay, text=self._t("oc_lbl_advance"), font=(self.font, 9),
            bg=self.colors["bg_card"], fg=self.colors["text_main"])
        self._field_labels["oc_lbl_advance"].pack(side=tk.LEFT, padx=(0, 8))
        self.ent_advance = tk.Entry(pay, width=12, justify="right", font=(self.font, 10),
                                    bg=self.colors["bg_body"], fg=self.colors["text_main"],
                                    insertbackground=self.colors["text_main"], relief="flat",
                                    highlightthickness=1, highlightbackground=self.colors["border"])
        self.ent_advance.pack(side=tk.LEFT, padx=(0, 16))

        self._field_labels["oc_lbl_remaining"] = tk.Label(
            pay, text=self._t("oc_lbl_remaining"), font=(self.font, 9, "bold"),
            bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        self._field_labels["oc_lbl_remaining"].pack(side=tk.LEFT, padx=(0, 8))
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
        self.btn_save_order = self._action_button(actions, self._t("oc_btn_save"), self.success, self.on_save_order)
        self.btn_print = self._action_button(actions, self._t("oc_btn_print"), self.warning, self.on_print_receipt)
        self.btn_clear = self._action_button(actions, self._t("oc_btn_clear"), self.danger, self.on_clear)

        self.reset_form()

    # ------------------------------------------------------------- helpers
    def _labels_for(self, keys):
        return [self._t(k) for k in keys]

    def _card(self, parent, number, title_key):
        # Soft-glass card: frosted shell + soft border + a thin light-catching
        # strip along the top edge, wrapping an inner frame that holds the
        # actual padding/content. Returns the inner frame — every existing
        # caller keeps adding children to it exactly as before.
        shell = tk.Frame(parent, bg=self.colors["bg_card"],
                         highlightbackground=self.colors["border"], highlightthickness=1)
        shell.pack(fill=tk.X, padx=20, pady=6)
        tk.Frame(shell, bg=self.colors["glass_highlight"], height=2).pack(side=tk.TOP, fill=tk.X)
        card = tk.Frame(shell, bg=self.colors["bg_card"], padx=16, pady=12)
        card.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        lbl = tk.Label(card, text=f"{number} · {self._t(title_key)}", font=(self.font, 10, "bold"),
                       bg=self.colors["bg_card"], fg=self.colors["text_main"])
        lbl.pack(anchor="w", pady=(0, 6))
        self._section_labels[title_key] = (number, lbl)
        return card

    def _row_entry(self, grid, row, label_key, read_only=False):
        lbl = tk.Label(grid, text=self._t(label_key), font=(self.font, 8, "bold"),
                       bg=self.colors["bg_card"], fg=self.colors["text_muted"])
        lbl.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        self._field_labels[label_key] = lbl
        state = "readonly" if read_only else "normal"
        entry = tk.Entry(grid, width=26, font=(self.font, 10), state=state,
                         bg=self.colors["bg_card"] if read_only else self.colors["bg_body"],
                         fg=self.colors["text_main"], insertbackground=self.colors["text_main"],
                         relief="flat", highlightthickness=1, highlightbackground=self.colors["border"],
                         readonlybackground=self.colors["bg_card"])
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

        for group in self.style_groups.values():
            group.set(group.options[0])  # default = first option

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

    def _customer_measurements(self):
        """Looks up the selected customer's saved measurements (Customer Hub
        is the single source for these) and maps them onto order-card keys."""
        customer_id = self.ent_customer_id.get().strip()
        customer = next((c for c in self.app.customers if str(c.get("id") or "") == customer_id), None)
        if not customer:
            return {}
        return {ord_key: str(customer.get(cust_key) or "")
                for cust_key, ord_key, _ in CUSTOMER_MEASUREMENT_FIELDS}

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
            **self._customer_measurements(),
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

        def t(key):
            return translate(lang, key)

        # Section headers
        for title_key, (number, lbl) in self._section_labels.items():
            lbl.configure(text=f"{number} · {t(title_key)}")

        # Field labels
        for label_key, lbl in self._field_labels.items():
            lbl.configure(text=t(label_key))

        # Style group row labels ("Button Style:" etc.)
        for key, lbl in self._style_row_labels.items():
            lbl.configure(text=t(STYLE_GROUP_LABEL_KEYS[key]) + ":")

        # Chips: relabel without touching the underlying stored value
        self.garment_group.relabel([t(k) for k in GARMENT_LABEL_KEYS])
        for key, group in self.style_groups.items():
            group.relabel([t(k) for k in STYLE_OPTION_LABEL_KEYS[key]])

        # Status dropdowns: relabel without touching the stored value
        self.cbo_status.relabel([t(k) for k in ORDER_STATUS_LABEL_KEYS])
        self.cbo_delivery_status.relabel([t(k) for k in DELIVERY_STATUS_LABEL_KEYS])

        # Action buttons
        self.btn_save_order.configure(text=t("oc_btn_save"))
        self.btn_print.configure(text=t("oc_btn_print"))
        self.btn_clear.configure(text=t("oc_btn_clear"))
