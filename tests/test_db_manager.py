import os
import tempfile

from database.db_manager import DBManager


def make_db():
    tmp_dir = tempfile.mkdtemp()
    return DBManager(os.path.join(tmp_dir, 'test.db'))


def test_insert_and_count():
    db = make_db()
    assert db.count_all() == 0
    db.insert_record("Live Camera", "defect", "MISSING", 900, 0.35, 500)
    assert db.count_all() == 1


def test_fetch_history_most_recent_first():
    db = make_db()
    db.insert_record("cam", "defect", "GOOD", 10, 0.35, 500)
    db.insert_record("cam", "defect", "MISSING", 999, 0.35, 500)
    rows = db.fetch_history()
    assert rows[0][3] == "MISSING"  # most recent (status column) comes first


def test_unsynced_workflow():
    db = make_db()
    id1 = db.insert_record("cam", "defect", "MISSING", 900, 0.35, 500)
    id2 = db.insert_record("cam", "defect", "GOOD", 10, 0.35, 500)

    unsynced = db.fetch_unsynced()
    assert len(unsynced) == 2
    assert db.count_unsynced() == 2

    db.mark_synced([id1])
    assert db.count_unsynced() == 1

    remaining_ids = [row[0] for row in db.fetch_unsynced()]
    assert remaining_ids == [id2]


def test_export_csv(tmp_path):
    db = make_db()
    db.insert_record("cam", "defect", "MISSING", 900, 0.35, 500)
    out_file = tmp_path / "out.csv"
    db.export_csv(str(out_file))
    content = out_file.read_text(encoding="utf-8-sig")
    assert "MISSING" in content
    assert "Timestamp" in content
