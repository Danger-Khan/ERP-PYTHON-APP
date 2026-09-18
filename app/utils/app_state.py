"""Tiny JSON-backed "remember what the user left it on" cache.

Not a database — just a small cache file (app_state_cache.json, in the
data dir's cache/ subfolder) holding the handful of UI preferences that
should survive closing and reopening the app: theme, language, which
sidebar section was open, and the window's last size/position. Read once
on startup, written on every change that matters and again on close, so a
crash mid-session loses at most the very latest tweak, never everything.
"""
import json
import os

DEFAULTS = {
    "theme": "light",
    "lang": "en",
    "last_section": "dashboard",
    "geometry": "1350x850",
}


class AppStateCache:
    def __init__(self, data_dir):
        # Deliberately does NOT create the cache/ directory here (or in
        # load()) -- only save() touches the filesystem. main_gui.py binds
        # this against self.excel_mgr's data dir at app startup, before a
        # test (or anything else) has a chance to point excel_mgr somewhere
        # else; if construction/loading created directories eagerly, that
        # first bind would always leave a stray cache/ folder behind in the
        # real data dir even when nothing was ever actually saved there.
        self.path = os.path.join(data_dir, "cache", "app_state_cache.json")

    def load(self):
        """Returns the saved state merged over DEFAULTS. Never raises —
        a missing, corrupt, or partially-written cache file just falls
        back to defaults instead of blocking startup."""
        state = dict(DEFAULTS)
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    state.update({k: v for k, v in saved.items() if k in DEFAULTS})
        except Exception as e:
            print(f"[AppStateCache] load failed, using defaults: {e}")
        return state

    def save(self, **fields):
        """Merges the given fields into the cache and writes it out.
        Non-fatal on failure (e.g. disk briefly locked) -- losing the
        cache write never crashes the app or blocks the caller."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            state = self.load()
            state.update({k: v for k, v in fields.items() if k in DEFAULTS})
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_path, self.path)
        except Exception as e:
            print(f"[AppStateCache] save failed: {e}")
