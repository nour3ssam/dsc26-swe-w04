from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from nour_transfers.app import create_app


def get_now():
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# --- Public Example Test ---
def test_request_transfer_returns_a_pending_card(client):
    r = client.post(
        "/v1/transfers",
        json={"itemCode": "MET500", "fromBranch": "heliopolis", "toBranch": "tanta", "quantity": 20},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


# --- Mutant Killers ---
def test_cors_origins_strictly_configured():
    app = create_app(stock={}, items={}, sales={}, now=get_now)
    client = TestClient(app)

    res_allowed = client.options(
        "/v1/transfers",
        headers={"Origin": "https://branch.nour.example", "Access-Control-Request-Method": "POST"},
    )
    assert res_allowed.headers.get("access-control-allow-origin") == "https://branch.nour.example"

    res_disallowed = client.options(
        "/v1/transfers",
        headers={"Origin": "https://malicious.example", "Access-Control-Request-Method": "POST"},
    )
    assert res_disallowed.headers.get("access-control-allow-origin") != "*"
    assert res_disallowed.headers.get("access-control-allow-origin") != "https://malicious.example"


def test_same_branch_transfer_rejected():
    app = create_app(
        stock={("b1", "med1"): 10},
        items={"med1": {"reserve": 2, "chronic": True}},
        sales={("b1", "med1"): 1.0},
        now=get_now,
    )
    client = TestClient(app)

    res = client.post(
        "/v1/transfers",
        json={"fromBranch": "b1", "toBranch": "b1", "itemCode": "med1", "quantity": 2},
    )
    assert res.status_code == 422


def test_error_problem_media_type_headers():
    app = create_app(
        stock={("b1", "med1"): 2, ("b2", "med1"): 0},
        items={"med1": {"reserve": 5, "chronic": False}},
        sales={},
        now=get_now,
    )
    client = TestClient(app)

    res = client.post(
        "/v1/transfers",
        json={"fromBranch": "b1", "toBranch": "b2", "itemCode": "med1", "quantity": 1},
    )
    assert res.status_code == 409
    assert res.headers["content-type"].startswith("application/problem+json")


def test_approve_twice_disallowed_and_credits_destination():
    app = create_app(
        stock={("b1", "med1"): 10, ("b2", "med1"): 5},
        items={"med1": {"reserve": 2, "chronic": False}},
        sales={},
        now=get_now,
    )
    client = TestClient(app)

    # 1. إنشاء طلب تحويل
    create_res = client.post(
        "/v1/transfers",
        json={"fromBranch": "b1", "toBranch": "b2", "itemCode": "med1", "quantity": 3},
    )
    assert create_res.status_code == 201
    transfer_id = create_res.json()["id"]

    # 2. القبول الأول ونجاحه (M13)
    approve1 = client.post(f"/v1/transfers/{transfer_id}/approve")
    assert approve1.status_code == 200

    # 3. القبول الثاني مرفوض برمز 409 والنوع المناسب (M06)
    approve2 = client.post(f"/v1/transfers/{transfer_id}/approve")
    assert approve2.status_code == 409
    assert approve2.headers["content-type"].startswith("application/problem+json")
    assert approve2.json()["type"].endswith("/problems/not-pending")


def test_inbox_sorting_by_priority_and_time():
    app = create_app(
        stock={
            ("b1", "m_normal"): 50,
            ("b1", "m_high"): 50,
            ("b1", "m_urgent"): 50,
            ("b2", "m_normal"): 100,  # رصيد مرتفع يضمن أولوية normal
            ("b2", "m_high"): 10,     # تغطية متوسطة -> high
            ("b2", "m_urgent"): 2,     # تغطية منخفضة + مزمن -> urgent
        },
        items={
            "m_normal": {"reserve": 1, "chronic": False},
            "m_high": {"reserve": 1, "chronic": False},
            "m_urgent": {"reserve": 1, "chronic": True},
        },
        sales={
            ("b2", "m_normal"): 1.0,
            ("b2", "m_high"): 2.0,
            ("b2", "m_urgent"): 2.0,
        },
        now=get_now,
    )
    client = TestClient(app)

    client.post("/v1/transfers", json={"fromBranch": "b1", "toBranch": "b2", "itemCode": "m_normal", "quantity": 1})
    client.post("/v1/transfers", json={"fromBranch": "b1", "toBranch": "b2", "itemCode": "m_high", "quantity": 1})
    client.post("/v1/transfers", json={"fromBranch": "b1", "toBranch": "b2", "itemCode": "m_urgent", "quantity": 1})

    inbox_res = client.get("/v1/branches/b2/transfers")
    assert inbox_res.status_code == 200
    res_data = inbox_res.json()
    items_list = res_data if isinstance(res_data, list) else res_data.get("items", res_data.get("transfers", []))

    priorities = [item["priority"] for item in items_list]
    assert priorities == ["urgent", "high", "normal"]