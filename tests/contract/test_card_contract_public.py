from datetime import datetime, timezone
import json
import pathlib
from jsonschema import Draft202012Validator
from fastapi.testclient import TestClient
from nour_transfers.app import create_app

SCHEMA = json.loads((pathlib.Path(__file__).parents[2] / "contracts/transfer_card.schema.json").read_text())


def get_now():
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_card_matches_what_the_branch_app_expects(client):
    r = client.post("/v1/transfers", json={"itemCode": "AMOX250", "fromBranch": "heliopolis",
                                           "toBranch": "tanta", "quantity": 5})
    Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(r.json())


# --- Mutant Killers ---

def test_transfer_card_schema_and_camel_case_and_timezone():
    app = create_app(
        stock={("b1", "med1"): 10, ("b2", "med1"): 0},
        items={"med1": {"reserve": 2, "chronic": True}},
        sales={},
        now=get_now,
    )
    client = TestClient(app)

    post_res = client.post(
        "/v1/transfers",
        json={"fromBranch": "b1", "toBranch": "b2", "itemCode": "med1", "quantity": 2},
    )
    assert post_res.status_code == 201

    inbox_res = client.get("/v1/branches/b2/transfers")
    assert inbox_res.status_code == 200
    res_data = inbox_res.json()
    items_list = res_data if isinstance(res_data, list) else res_data.get("items", res_data.get("transfers", []))

    assert len(items_list) >= 1
    card = items_list[0]

    Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(card)

    assert "fromBranch" in card
    assert "toBranch" in card
    assert "itemCode" in card
    assert "requestedAt" in card
    assert "from_branch" not in card

    assert card["requestedAt"].endswith("Z")