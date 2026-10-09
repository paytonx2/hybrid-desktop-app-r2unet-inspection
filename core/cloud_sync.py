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
import threading
from datetime import datetime

import requests
from PySide6.QtCore import QThread, Signal


def to_iso_with_tz(local_ts):
    """
    SQLite stores local wall-clock time without a timezone ("2026-08-29 08:31:31").
    Postgres timestamptz would read that as UTC (7 hours off in Thailand),
    so attach this machine's UTC offset before sending.
    """
    return datetime.strptime(local_ts, '%Y-%m-%d %H:%M:%S').astimezone().isoformat()


class CloudSyncWorker(QThread):
    status_changed = Signal(str)   # human readable status for the UI/log
    synced_batch = Signal(int)     # number of rows successfully synced

    def __init__(self, db_manager, device_id, supabase_url=None, supabase_key=None,
                 interval_seconds=15, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.device_id = device_id
        self.supabase_url = (supabase_url or os.environ.get("SUPABASE_URL") or "").rstrip("/")
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_ANON_KEY")
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._offline = False
        # Sent so Supabase can drop duplicates (unique device_id + local_id).
        # Turned off automatically if the migration has not been run yet.
        self._send_local_id = True

    def is_configured(self):
        return bool(self.supabase_url and self.supabase_key)

    def run(self):
        if not self.is_configured():
            self.status_changed.emit("Cloud sync disabled (no SUPABASE_URL / SUPABASE_ANON_KEY set)")
            return

        self._stop_event.clear()
        self.status_changed.emit("Cloud sync enabled — syncing in the background")

        while not self._stop_event.is_set():
            try:
                self._sync_once()
            except Exception as e:
                self.status_changed.emit(f"Sync error (will retry): {e}")

            # Event.wait instead of sleep so stop() returns immediately
            self._stop_event.wait(self.interval_seconds)

    def _build_payload(self, rows):
        payload = []
        ids = []
        for (row_id, timestamp, source, model_type, status, pixel_count,
             conf_threshold, px_threshold) in rows:
            item = {
                "device_id": self.device_id,
                "ts": to_iso_with_tz(timestamp),
                "source": source,
                "model_type": model_type,
                "status": status,
                "pixel_count": pixel_count,
                "conf_threshold": conf_threshold,
                "px_threshold": px_threshold,
            }
            if self._send_local_id:
                item["local_id"] = row_id
            payload.append(item)
            ids.append(row_id)
        return payload, ids

    def _post(self, payload):
        url = f"{self.supabase_url}/rest/v1/inspections"
        prefer = "return=minimal"
        if self._send_local_id:
            url += "?on_conflict=device_id,local_id"
            prefer += ",resolution=ignore-duplicates"
        return requests.post(
            url,
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": prefer,
            },
            json=payload,
            timeout=10,
        )

    def _sync_once(self):
        rows = self.db.fetch_unsynced(limit=200)
        if not rows:
            return

        payload, ids = self._build_payload(rows)
        try:
            resp = self._post(payload)
        except (requests.ConnectionError, requests.Timeout):
            # No internet / Supabase unreachable: expected offline behaviour,
            # log once and stay quiet until it comes back.
            if not self._offline:
                self._offline = True
                self.status_changed.emit("Cloud sync: offline, will retry automatically")
            return
        self._offline = False

        if self._send_local_id and resp.status_code in (400, 404) and "local_id" in resp.text:
            # Supabase table has no local_id column / unique constraint yet
            self._send_local_id = False
            self.status_changed.emit(
                "Cloud sync: duplicate protection is off — run supabase/migrations/001_local_id_dedup.sql"
            )
            payload, ids = self._build_payload(rows)
            resp = self._post(payload)

        if resp.status_code in (200, 201):
            self.db.mark_synced(ids)
            self.synced_batch.emit(len(ids))
        else:
            self.status_changed.emit(f"Sync failed ({resp.status_code}): {resp.text[:200]}")

    def stop(self):
        self._stop_event.set()
        self.wait(15000)  # at most one in-flight request (10 s timeout)
