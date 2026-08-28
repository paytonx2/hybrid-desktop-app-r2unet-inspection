import sqlite3
import os
import csv
from datetime import datetime


class DBManager:
    """
    จัดการฐานขอ้มลู SQLite ภายในเครอื่ง สำ หรับเกบ็ ประวตั กิ ารตรวจสอบทงั้หมด
    (ไมต่ อ้ งใช ้internet / server ภายนอกใด ๆ)
    """

    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT,
                model_type TEXT,
                status TEXT,
                pixel_count INTEGER,
                conf_threshold REAL,
                px_threshold INTEGER,
                synced_at TEXT
            )
        ''')
        # Backfill the synced_at column for DBs created before cloud sync existed
        c.execute("PRAGMA table_info(inspections)")
        cols = [row[1] for row in c.fetchall()]
        if 'synced_at' not in cols:
            c.execute("ALTER TABLE inspections ADD COLUMN synced_at TEXT")
        conn.commit()
        conn.close()

    def insert_record(self, source, model_type, status, pixel_count, conf_threshold, px_threshold):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO inspections
                (timestamp, source, model_type, status, pixel_count, conf_threshold, px_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            source, model_type, status, pixel_count, conf_threshold, px_threshold
        ))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return new_id

    def fetch_unsynced(self, limit=50):
        """Rows that have not yet been pushed to Supabase (synced_at IS NULL)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, source, model_type, status, pixel_count, conf_threshold, px_threshold
            FROM inspections
            WHERE synced_at IS NULL
            ORDER BY id ASC
            LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        conn.close()
        return rows

    def mark_synced(self, ids):
        if not ids:
            return
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.executemany(
            'UPDATE inspections SET synced_at = ? WHERE id = ?',
            [(now, i) for i in ids]
        )
        conn.commit()
        conn.close()

    def count_unsynced(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM inspections WHERE synced_at IS NULL')
        n = c.fetchone()[0]
        conn.close()
        return n

    def fetch_history(self, limit=300):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT timestamp, source, model_type, status, pixel_count
            FROM inspections ORDER BY id DESC LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        conn.close()
        return rows

    def count_all(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM inspections')
        n = c.fetchone()[0]
        conn.close()
        return n

    def export_csv(self, out_path):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT timestamp, source, model_type, status, pixel_count, conf_threshold, px_threshold
            FROM inspections ORDER BY id
        ''')
        rows = c.fetchall()
        conn.close()

        with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Source', 'Model', 'Status', 'Pixels', 'Confidence', 'PxThreshold'])
            writer.writerows(rows)

        return out_path
