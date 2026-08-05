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
        temp_mgr.append_record("employees.xlsx", app.emp_headers,
                               ["E-1", "Tailor One", "0300", "Master Cutter", "On Duty", ""])

        # --- Login ---
        app.ent_pwd.insert(0, "admin123")
        app.authenticate()
        app.update()
        check("login -> dashboard builds", hasattr(app, "tree_orders") and app.tree_orders.winfo_exists())
        check("seeded orders shown", len(app.tree_orders.get_children()) == 1)
        check("seeded customers shown", len(app.tree_customers.get_children()) == 1)
        check("seeded employees shown", len(app.tree_employees.get_children()) == 1)

        # --- Section navigation ---
        for key in ["customer", "employee", "admin", "dashboard"]:
            app.show_section(key)
            app.update()
            check(f"section '{key}' visible", bool(app.sections[key].winfo_viewable()))

        # --- Theme switch ---
        app.show_section("admin")
        app.update()
        app.cbo_theme.set("Dark Mode \u263e")
        app.change_theme()
        app.update()
        check("dark theme applied", app.current_theme == "dark" and app.colors["bg_body"] == "#121212")
        app.cbo_theme.set("Light Mode \u2600\ufe0f")
        app.change_theme()
        app.update()
        check("light theme restored", app.current_theme == "light" and app.colors["bg_body"] == "#F5F5F7")

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
        check("english nav restored", app.nav_buttons["dashboard"][0].cget("text") == "Dashboard")

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
