from __future__ import annotations

import os
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_create_run_and_confirm_subtasks_smoke():
    if not (os.getenv("NVIDIA_API_KEY") or settings.nvidia_api_key):
        pytest.skip("NVIDIA_API_KEY not set")
    settings.nvidia_api_key = os.getenv("NVIDIA_API_KEY") or settings.nvidia_api_key
    # Use context manager so startup events run (DB tables created).
    with TestClient(app) as client:
        r = client.post("/api/runs", json={"query": "search: milvus mcp; build ui"})
        assert r.status_code == 200
        body = cast(dict[str, object], r.json())

        run_id_obj = body.get("run_id")
        assert isinstance(run_id_obj, str) and run_id_obj

        assert body.get("status") == "waiting_confirm"

        subtasks_obj = body.get("subtasks")
        assert isinstance(subtasks_obj, list) and subtasks_obj

        run_id = run_id_obj
        subtasks = cast(list[object], subtasks_obj)
        # confirm
        r2 = client.post(f"/api/runs/{run_id}/subtasks/confirm", json={"subtasks": subtasks})
        assert r2.status_code == 200
        body2 = cast(dict[str, object], r2.json())
        assert body2.get("ok") is True
