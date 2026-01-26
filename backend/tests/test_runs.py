from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_create_run_and_confirm_subtasks_smoke():
    # Use context manager so startup events run (DB tables created).
    with TestClient(app) as client:
        r = client.post("/api/runs", json={"query": "search: milvus mcp; build ui"})
        assert r.status_code == 200
        body = r.json()
        assert body["run_id"]
        assert body["status"] == "waiting_confirm"
        assert isinstance(body["subtasks"], list)
        assert len(body["subtasks"]) >= 1

        run_id = body["run_id"]
        subtasks = body["subtasks"]
        # confirm
        r2 = client.post(f"/api/runs/{run_id}/subtasks/confirm", json={"subtasks": subtasks})
        assert r2.status_code == 200
        assert r2.json()["ok"] is True
