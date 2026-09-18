"""Permanent GUI smoke test for the Atelier ERP Tkinter app.

Launches the real AtelierERPApp pointed at a throwaway temp data dir,
then verifies: login -> dashboard, section navigation, theme/language
switches, modal dialogs, Excel persistence, PDF generation and charts.

Run directly:
    python app/tests/gui_smoke_test.py

Exits non-zero if any check fails.
"""
import sys
import os
import shutil
import tempfile
import traceback

from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT.parent
PROJECT_ROOT = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(1, str(APP_DIR))

from app import main_gui as gui

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name)


def hook(level, *args, **kwargs):
    print(f"[msgbox:{level}]", args)


# Neutralize blocking dialogs
gui.messagebox.showerror = lambda *a, **k: hook("error", *a)
gui.messagebox.showwarning = lambda *a, **k: hook("warning", *a)
gui.messagebox.showinfo = lambda *a, **k: hook("info", *a)

SKIP_PDF = False
try:
    import reportlab  # noqa
except ImportError:
    SKIP_PDF = True

tmpdir = tempfile.mkdtemp(prefix="atelier_gui_smoke_")
pdf_path = None

def run_gui_smoke_test():
    try:
        app = gui.AtelierERPApp()
        app.update()
        check("login dialog shows", hasattr(app, "login_dlg") and app.login_dlg.winfo_exists())

        # --- Point the app at a throwaway data dir and seed it ---
        temp_mgr = gui.ExcelManager(data_dir=tmpdir)
        app.excel_mgr = temp_mgr
        temp_mgr.append_record("customers.xlsx", app.cust_headers,
                               ["C-101", "Test Customer", "03001234567", "42", "19", "17", "15", "38", "34", "46", "36", "22"])
        temp_mgr.append_record("orders.xlsx", app.ord_headers,
                               ["ORD-101", "Test Customer", "Shalwar Kameez", "In Progress", "Tailor One",
                                "Half Ban", "Round Cuff", "Side Pocket", "Square Daman", "1. Single Stitch", "Baz Button"])
        # Second order, fully populated (incl. finance columns) and already
        # Delivered with an unpaid balance -- exercises the finance ledger's
        # "debt" bucket (delivered + unpaid) distinctly from "remaining".
        temp_mgr.append_record("orders.xlsx", app.ord_headers,
                               ["ORD-102", "C-101", "Waistcoat", "Delivered", "Tailor One",
                                "Chinese", "Round Cuff", "One", "Square Daman", "1. Single Stitch", "Karh Button",
                                "2026-01-01", "2026-01-05", "17:00", "Tailor One",
                                "Delivered", "", "5000.00", "2000.00", "3000.00"])
        # Third order, fully paid (total == advance, remaining 0, not
        # delivered) -- exercises the finance ledger's "Done" tab distinctly
        # from "Due" (ORD-102) and plain "All" (ORD-101, no total/advance).
        temp_mgr.append_record("orders.xlsx", app.ord_headers,
                               ["ORD-103", "C-101", "Pant", "Ready", "Tailor One",
                                "Normal", "Normal", "One", "Normal", "1. Single Stitch", "Normal",
                                "2026-01-02", "2026-01-08", "", "", "Not Delivered", "", "2000.00", "2000.00", "0.00"])
        temp_mgr.append_record("employees.xlsx", app.emp_headers,
                               ["E-1", "Tailor One", "0300", "Master Cutter", "On Duty", ""])

        # --- Login ---
        app.ent_pwd.insert(0, "admin123")
        app.authenticate()
        app.update()
        check("login -> dashboard builds", hasattr(app, "tree_orders") and app.tree_orders.winfo_exists())
        check("seeded orders shown", len(app.tree_orders.get_children()) == 3)
        check("seeded customers shown", len(app.tree_customers.get_children()) == 1)
        check("seeded employees shown", len(app.tree_employees.get_children()) == 1)

        # --- Section navigation ---
        for key in ["customer", "employee", "finance", "admin", "dashboard"]:
            app.show_section(key)
            app.update()
            check(f"section '{key}' visible", bool(app.sections[key].winfo_viewable()))

        # --- Theme switch ---
        app.show_section("admin")
        app.update()
        app.cbo_theme.set("Dark Mode \u263e")
        app.change_theme()
        app.update()
        # Compares against THEMES directly rather than a hardcoded hex value,
        # so retuning the palette (e.g. the soft-glass colors) never stales
        # this test out.
        check("dark theme applied", app.current_theme == "dark" and app.colors["bg_body"] == gui.THEMES["dark"]["bg_body"])
        app.cbo_theme.set("Light Mode \u2600\ufe0f")
        app.change_theme()
        app.update()
        check("light theme restored", app.current_theme == "light" and app.colors["bg_body"] == gui.THEMES["light"]["bg_body"])

        # --- Language switch ---
        app.show_section("admin")
        app.update()
        app.cbo_lang.set("Urdu \U0001F1F5\U0001F1F0")
        app.on_language_change(None)
        app.update()
        check("urdu nav applied", "ڈیش بورڈ" in app.nav_buttons["dashboard"][0].cget("text"))
        app.cbo_lang.set("English \U0001F1EC\U0001F1E7")
        app.on_language_change(None)
        app.update()
        check("english nav restored", "Dashboard" in app.nav_buttons["dashboard"][0].cget("text"))

        # --- Modals open without error (grab may fail on unmapped windows; tolerated) ---
        def open_and_destroy(method, name):
            try:
                method()
                app.update()
                toplevels = [w for w in app.winfo_children() if isinstance(w, gui.tk.Toplevel) and w.winfo_exists()]
                check(f"modal '{name}' opens", len(toplevels) == 1)
                for w in toplevels:
                    try:
                        w.grab_release()
                    except Exception:
                        pass
                    w.destroy()
                app.update()
            except Exception as e:
                check(f"modal '{name}' opens", False)
                print("   !!", repr(e))

        open_and_destroy(app.open_add_customer_modal, "add customer")
        open_and_destroy(app.open_add_order_modal, "add order")
        open_and_destroy(app.open_add_employee_modal, "add employee")
        open_and_destroy(app.open_assign_task_modal, "assign task")

        # --- Settings lists seeded ---
        app.show_section("admin")
        app.update()
        check("settings lists populated",
              app.lst_garments.size() == len(app.garment_types) and app.lst_roles.size() == len(app.employee_roles)
              and app.lst_garments.size() > 0 and app.lst_roles.size() > 0)

        # --- Order status change persists to Excel ---
        app.show_section("dashboard")
        app.update()
        children = app.tree_orders.get_children()
        app.tree_orders.selection_set(children[0])
        app.quick_change_order_status("Ready")
        app.update()
        persisted = temp_mgr.read_records("orders.xlsx", app.ord_headers)
        check("status change persisted", any(gui.clean_val(o.get("id")) == "ORD-101" and "ready" in gui.clean_val(o.get("status")).lower() for o in persisted))
        check("button_style preserved", any(gui.clean_val(o.get("button_style")) == "Baz Button" for o in persisted))

        # --- Task assignment persists to Excel ---
        app.update_employee_task("E-1", "Cut ORD-101")
        persisted_emp = temp_mgr.read_records("employees.xlsx", app.emp_headers)
        check("task assignment persisted", any(gui.clean_val(e.get("id")) == "E-1" and gui.clean_val(e.get("current_task")) == "Cut ORD-101" for e in persisted_emp))

        # --- Finance ledger (SQLite): paid/remaining/debt computed from the
        # two seeded orders. ORD-101 has no total/advance -> contributes 0
        # everywhere. ORD-102 is Delivered with total 5000/advance 2000, so
        # its 3000 balance must land in "debt" (delivered+unpaid), not
        # "remaining" (which is reserved for undelivered orders).
        app.show_section("finance")
        app.update()
        check("finance section visible", bool(app.sections["finance"].winfo_viewable()))
        totals = app._finance_db_for_current_data().get_totals()
        check("finance total paid correct", totals["paid"] == 4000.0)
        check("finance total debt correct (delivered+unpaid)", totals["debt"] == 3000.0)
        check("finance total remaining correct (excludes delivered)", totals["remaining"] == 0.0)

        # --- Finance tabs: All / Done / Due filter the ledger table ---
        app.set_finance_tab("all")
        app.update()
        check("finance 'all' tab shows every order", len(app.tree_finance.get_children()) == 3)
        app.set_finance_tab("done")
        app.update()
        check("finance 'done' tab shows only fully-paid orders", len(app.tree_finance.get_children()) == 1)
        app.set_finance_tab("due")
        app.update()
        check("finance 'due' tab shows only orders with a balance", len(app.tree_finance.get_children()) == 1)

        # --- Add Payment tab: pay down ORD-102's remaining debt ---
        app.set_finance_tab("add")
        app.update()
        check("add-payment picker lists the due order", "ORD-102" in app.cbo_fin_pay_order.get())
        app.ent_fin_pay_amount.insert(0, "1000")
        app.record_finance_payment()
        app.update()
        persisted_ord = temp_mgr.read_records("orders.xlsx", app.ord_headers)
        ord102 = next((o for o in persisted_ord if gui.clean_val(o.get("id")) == "ORD-102"), {})
        check("payment updated advance on ORD-102", gui.clean_val(ord102.get("advance")) == "3000.00")
        new_totals = app._finance_db_for_current_data().get_totals()
        check("finance totals reflect the recorded payment", new_totals["paid"] == 5000.0 and new_totals["debt"] == 2000.0)
        app.set_finance_tab("all")
        app.update()

        # --- Settings/session cache: theme, language, and last open section
        # should have been written to <tmpdir>/cache/app_state_cache.json by
        # the show_section()/change_theme()/on_language_change() calls above
        # (all of which happened after excel_mgr was pointed at tmpdir), and
        # a fresh AppStateCache reading the same path should see them --
        # this is the mechanism that lets the real app reopen where the
        # user left off. reload_all_data() also must never have skipped
        # touching the real app/data dir at any point above.
        cache_path = os.path.join(tmpdir, "cache", "app_state_cache.json")
        check("session cache file written to the active data dir", os.path.exists(cache_path))
        saved_state = gui.AppStateCache(tmpdir).load()
        check("session cache remembers last open section", saved_state["last_section"] == "finance")
        check("session cache remembers theme", saved_state["theme"] == "light")
        check("session cache remembers language", saved_state["lang"] == "en")
        check("session cache round-trips via a fresh instance", gui.AppStateCache(tmpdir).load() == saved_state)

        # --- PDF generation (if reportlab available) ---
        if SKIP_PDF:
            print("SKIP  pdf generation (reportlab not installed)")
        else:
            app.show_section("dashboard")
            app.update()
            app.tree_orders.selection_set(app.tree_orders.get_children()[0])
            pdf_path = os.path.join(tmpdir, "Receipt_ORD-101.pdf")
            gui.filedialog.asksaveasfilename = lambda **k: pdf_path
            app.generate_order_pdf()
            check("pdf generated", pdf_path and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0)

        # --- Donut chart percentages render ---
        app.update_graphics_and_stats()
        app.update()
        check("charts updated", app.chart_done.percentage >= 0 and app.chart_prog.percentage >= 0 and app.chart_rem.percentage >= 0)

    except Exception:
        traceback.print_exc()
        results.append(("no exceptions during flow", False))

    finally:
        try:
            app.destroy()
        except Exception:
            pass
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass

    failed = [n for n, ok in results if not ok]
    print("\n===== SUMMARY =====")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:", ", ".join(failed))
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    run_gui_smoke_test()
