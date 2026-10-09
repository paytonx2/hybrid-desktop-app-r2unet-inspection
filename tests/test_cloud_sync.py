import os
import tempfile
from unittest import mock

import requests

from core.cloud_sync import CloudSyncWorker, to_iso_with_tz
from database.db_manager import DBManager


def make_db():
    return DBManager(os.path.join(tempfile.mkdtemp(), 'test.db'))


def make_worker(db):
    return CloudSyncWorker(db, "test-pc", supabase_url="https://x.supabase.co/", supabase_key="key")


def fake_response(status_code, text=""):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.text = text
    return resp


def test_timestamp_gets_timezone_offset():
    iso = to_iso_with_tz("2026-08-29 08:31:31")
    assert iso.startswith("2026-08-29T08:31:31")
    assert iso[-6] in "+-"  # e.g. +07:00


def test_not_configured_without_keys():
    with mock.patch.dict(os.environ, {}, clear=True):
        assert not CloudSyncWorker(make_db(), "pc").is_configured()


def test_successful_sync_marks_rows_and_sends_local_id():
    db = make_db()
    row_id = db.insert_record("cam", "defect", "MISSING", 900, 0.35, 500)
    worker = make_worker(db)

    with mock.patch("core.cloud_sync.requests.post", return_value=fake_response(201)) as post:
        worker._sync_once()

    assert db.count_unsynced() == 0
    url = post.call_args.args[0]
    assert url == "https://x.supabase.co/rest/v1/inspections?on_conflict=device_id,local_id"
    sent = post.call_args.kwargs["json"][0]
    assert sent["local_id"] == row_id
    assert sent["device_id"] == "test-pc"


def test_failed_sync_keeps_rows_for_retry():
    db = make_db()
    db.insert_record("cam", "defect", "MISSING", 900, 0.35, 500)
    worker = make_worker(db)

    with mock.patch("core.cloud_sync.requests.post", return_value=fake_response(500, "boom")):
        worker._sync_once()

    assert db.count_unsynced() == 1


def test_offline_keeps_rows_and_does_not_raise():
    db = make_db()
    db.insert_record("cam", "defect", "MISSING", 900, 0.35, 500)
    worker = make_worker(db)

    with mock.patch("core.cloud_sync.requests.post", side_effect=requests.ConnectionError):
        worker._sync_once()

    assert db.count_unsynced() == 1


def test_falls_back_when_supabase_has_no_local_id_column():
    db = make_db()
    db.insert_record("cam", "defect", "MISSING", 900, 0.35, 500)
    worker = make_worker(db)
    responses = [
        fake_response(400, "Could not find the 'local_id' column of 'inspections'"),
        fake_response(201),
    ]

    with mock.patch("core.cloud_sync.requests.post", side_effect=responses) as post:
        worker._sync_once()

    assert db.count_unsynced() == 0
    assert "local_id" not in post.call_args.kwargs["json"][0]
