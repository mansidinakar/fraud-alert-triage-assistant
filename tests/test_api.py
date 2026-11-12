import os
import shutil

import pytest
from fastapi.testclient import TestClient

KEY = "test-key-" + "x" * 30
H = {"X-API-Key": KEY}


@pytest.fixture(scope="module")
def api_and_client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("db") / "triage.duckdb"
    shutil.copy("data/triage.duckdb", tmp)
    os.environ["TRIAGE_DB"] = str(tmp)
    os.environ["API_TOKEN"] = KEY
    import src.api as api
    with TestClient(api.app) as c:
        yield api, c


@pytest.fixture(scope="module")
def client(api_and_client):
    return api_and_client[1]


def test_health_is_open(client):
    assert client.get("/health").status_code == 200


def test_endpoints_require_key(client):
    assert client.get("/queue").status_code == 401
    assert client.get("/queue", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/alerts/1").status_code == 401
    body = {"analyst_id": "a1", "decision": "escalate", "reason": ""}
    assert client.post("/alerts/1/disposition", json=body).status_code == 401


def test_queue_lists_pending(client):
    r = client.get("/queue?limit=5", headers=H)
    assert r.status_code == 200
    assert r.json()["pending"] == 163
    assert len(r.json()["items"]) == 5


def test_queue_limit_is_bounded(client):
    assert client.get("/queue?limit=100000", headers=H).status_code == 422
    assert client.get("/queue?offset=-1", headers=H).status_code == 422


def test_alert_detail_never_exposes_label(client):
    alert_id = client.get("/queue?limit=1", headers=H).json()["items"][0]["alert_id"]
    r = client.get(f"/alerts/{alert_id}", headers=H)
    assert r.status_code == 200
    assert "is_fraud" not in r.text
    assert "syn_" not in r.text
    body = r.json()
    assert body["evidence"] and body["triage"]["summary"]


def test_bad_alert_ids_are_rejected(client):
    assert client.get("/alerts/999999999", headers=H).status_code == 404
    assert client.get("/alerts/0", headers=H).status_code == 422
    assert client.get("/alerts/1%20OR%201=1", headers=H).status_code == 422
    assert client.get("/alerts/abc", headers=H).status_code == 422


def _pick(client, n):
    return client.get(f"/queue?limit={n}", headers=H).json()["items"]


def test_invalid_disposition_payloads_rejected(client):
    aid = _pick(client, 1)[0]["alert_id"]
    url = f"/alerts/{aid}/disposition"
    good = {"analyst_id": "analyst_1", "decision": "escalate", "reason": "ok"}
    assert client.post(url, json={**good, "decision": "approve"}, headers=H).status_code == 422
    assert client.post(url, json={**good, "analyst_id": "a; drop table alerts"}, headers=H).status_code == 422
    assert client.post(url, json={**good, "reason": "x" * 501}, headers=H).status_code == 422
    assert client.post(url, json={**good, "is_admin": True}, headers=H).status_code == 422


def test_override_requires_reason(client):
    item = _pick(client, 1)[0]
    other = "request_info" if item["suggested_disposition"] != "request_info" else "escalate"
    body = {"analyst_id": "analyst_1", "decision": other, "reason": "  "}
    r = client.post(f"/alerts/{item['alert_id']}/disposition", json=body, headers=H)
    assert r.status_code == 422


def test_disposition_is_recorded_once_and_audited(api_and_client):
    api, client = api_and_client
    item = _pick(client, 1)[0]
    aid = item["alert_id"]
    before = client.get("/queue?limit=1", headers=H).json()["pending"]
    body = {"analyst_id": "analyst_1", "decision": item["suggested_disposition"], "reason": ""}
    r = client.post(f"/alerts/{aid}/disposition", json=body, headers=H)
    assert r.status_code == 201 and r.json()["overrode_suggestion"] is False
    assert client.post(f"/alerts/{aid}/disposition", json=body, headers=H).status_code == 409
    assert client.get("/queue?limit=1", headers=H).json()["pending"] == before - 1
    cur = api.CON.cursor()
    n = cur.execute("select count(*) from audit_log where alert_id = ?", [aid]).fetchone()[0]
    assert n == 1
    detail = client.get(f"/alerts/{aid}", headers=H).json()
    assert detail["disposition"]["decision"] == item["suggested_disposition"]


def test_override_with_reason_is_accepted(client):
    item = _pick(client, 1)[0]
    other = "request_info" if item["suggested_disposition"] != "request_info" else "escalate"
    body = {"analyst_id": "analyst_2", "decision": other, "reason": "Customer history looks normal."}
    r = client.post(f"/alerts/{item['alert_id']}/disposition", json=body, headers=H)
    assert r.status_code == 201 and r.json()["overrode_suggestion"] is True
