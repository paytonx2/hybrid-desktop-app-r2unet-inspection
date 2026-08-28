"""
Cloud sync module.

Design goal: the desktop app must keep working perfectly with NO internet
connection at all (offline-first). This worker only ever *adds* data to
Supabase in the background; if it fails (no wifi, Supabase down, bad key),
it silently retries on the next cycle. It never blocks or crashes the
camera/AI thread.

Requires two environment variables (see .env.example):
    SUPABASE_URL
    SUPABASE_ANON_KEY
If they are not set, sync is simply disabled and the app behaves exactly
like the fully-offline version.
"""

import os
import socket
import requests
from PySide6.QtCore import QThread, Signal


class CloudSyncWorker(QThread):
    status_changed = Signal(str)   # human readable status for the UI/log
    synced_batch = Signal(int)     # number of rows successfully synced

    def __init__(self, db_manager, device_id, supabase_url=None, supabase_key=None,
                 interval_seconds=15, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.device_id = device_id
        self.supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_ANON_KEY")
        self.interval_seconds = interval_seconds
        self._running = False

    def is_configured(self):
        return bool(self.supabase_url and self.supabase_key)

    @staticmethod
    def _has_internet(timeout=2):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except OSError:
            return False

    def run(self):
        if not self.is_configured():
            self.status_changed.emit("Cloud sync disabled (no SUPABASE_URL / SUPABASE_ANON_KEY set)")
            return

        self._running = True
        self.status_changed.emit("Cloud sync enabled — syncing in the background")

        while self._running:
            try:
                self._sync_once()
            except Exception as e:
                self.status_changed.emit(f"Sync error (will retry): {e}")

            self.sleep(self.interval_seconds)

    def _sync_once(self):
        if not self._has_internet():
            return  # stay quiet, this is expected/normal offline behaviour

        rows = self.db.fetch_unsynced(limit=50)
        if not rows:
            return

        payload = []
        ids = []
        for (row_id, timestamp, source, model_type, status, pixel_count,
             conf_threshold, px_threshold) in rows:
            payload.append({
                "device_id": self.device_id,
                "ts": timestamp,
                "source": source,
                "model_type": model_type,
                "status": status,
                "pixel_count": pixel_count,
                "conf_threshold": conf_threshold,
                "px_threshold": px_threshold,
            })
            ids.append(row_id)

        resp = requests.post(
            f"{self.supabase_url}/rest/v1/inspections",
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=payload,
            timeout=10,
        )

        if resp.status_code in (200, 201):
            self.db.mark_synced(ids)
            self.synced_batch.emit(len(ids))
            self.status_changed.emit(f"☁️ Synced {len(ids)} record(s) to Supabase")
        else:
            self.status_changed.emit(f"Sync failed ({resp.status_code}): {resp.text[:200]}")

    def stop(self):
        self._running = False
        self.wait(3000)
