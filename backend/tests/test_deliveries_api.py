
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

from app.models.employee import Employee
from app.models.delivery import Delivery


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def employee_payload():
    return {
        "employee_code": "EMP001",
        "name": "Test Employee",
        "phone": "9876543210",
        "city": "Delhi",
    }


def delivery_payload(tracking_number="TRK001"):
    return {
        "tracking_number": tracking_number,
        "customer_name": "Test Customer",
        "customer_phone": "9876543211",
        "city": "Delhi",
        "pickup_address": "Connaught Place, Delhi",
        "delivery_address": "Dwarka, Delhi",
        "priority": "normal",
    }


def create_employee(client):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(),
    )
    return response.json()["id"]


def create_delivery(client, payload=None):
    response = client.post(
        "/api/v1/deliveries",
        json=payload or delivery_payload(),
    )
    return response


def test_create_pending_delivery(client):
    response = create_delivery(client)

    assert response.status_code == 201
    assert response.json()["tracking_number"] == "TRK001"
    assert response.json()["status"] == "pending"


def test_create_assigned_delivery(client):
    employee_id = create_employee(client)

    payload = delivery_payload()
    payload["assigned_employee_id"] = employee_id

    response = create_delivery(client, payload)

    assert response.status_code == 201
    assert response.json()["status"] == "assigned"
    assert response.json()["assigned_employee_id"] == employee_id


def test_duplicate_tracking_number(client):
    create_delivery(client)

    response = create_delivery(client)

    assert response.status_code == 409
    assert response.json()["detail"] == "Tracking number already exists"


def test_assignment_to_nonexistent_employee(client):
    payload = delivery_payload()
    payload["assigned_employee_id"] = 999

    response = create_delivery(client, payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Assigned employee not found"


def test_assignment_to_employee_in_another_city(client):
    employee_id = create_employee(client)

    payload = delivery_payload()
    payload["city"] = "Mumbai"
    payload["assigned_employee_id"] = employee_id

    response = create_delivery(client, payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Employee and delivery must belong to the same city"
    )


def test_assignment_to_inactive_employee(client):
    employee_id = create_employee(client)

    client.delete(f"/api/v1/employees/{employee_id}")

    payload = delivery_payload()
    payload["assigned_employee_id"] = employee_id

    response = create_delivery(client, payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot assign delivery to an inactive employee"
    )


def test_patch_priority_preserves_existing_status(client):
    delivery = create_delivery(client).json()

    response = client.patch(
        f"/api/v1/deliveries/{delivery['id']}",
        json={"priority": "high"},
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "high"
    assert response.json()["status"] == "pending"


def test_assign_and_unassign_delivery(client):
    employee_id = create_employee(client)
    delivery = create_delivery(client).json()

    assign_response = client.patch(
        f"/api/v1/deliveries/{delivery['id']}",
        json={"assigned_employee_id": employee_id},
    )

    assert assign_response.status_code == 200
    assert assign_response.json()["status"] == "assigned"

    unassign_response = client.patch(
        f"/api/v1/deliveries/{delivery['id']}",
        json={"assigned_employee_id": None},
    )

    assert unassign_response.status_code == 200
    assert unassign_response.json()["status"] == "pending"
    assert unassign_response.json()["assigned_employee_id"] is None


def test_valid_delivery_status_transitions(client):
    employee_id = create_employee(client)

    payload = delivery_payload()
    payload["assigned_employee_id"] = employee_id

    delivery = create_delivery(client, payload).json()
    delivery_id = delivery["id"]

    for new_status in ["picked_up", "in_transit", "delivered"]:
        response = client.patch(
            f"/api/v1/deliveries/{delivery_id}",
            json={"status": new_status},
        )
        assert response.status_code == 200
        assert response.json()["status"] == new_status

    assert response.json()["delivered_at"] is not None


def test_invalid_delivery_status_transition(client):
    delivery = create_delivery(client).json()

    response = client.patch(
        f"/api/v1/deliveries/{delivery['id']}",
        json={"status": "delivered"},
    )

    assert response.status_code == 409


def test_completed_delivery_cannot_be_modified(client):
    employee_id = create_employee(client)

    payload = delivery_payload()
    payload["assigned_employee_id"] = employee_id

    delivery = create_delivery(client, payload).json()
    delivery_id = delivery["id"]

    for new_status in ["picked_up", "in_transit", "delivered"]:
        client.patch(
            f"/api/v1/deliveries/{delivery_id}",
            json={"status": new_status},
        )

    response = client.patch(
        f"/api/v1/deliveries/{delivery_id}",
        json={"priority": "urgent"},
    )

    assert response.status_code == 409


def test_cancel_delivery(client):
    delivery = create_delivery(client).json()

    response = client.delete(
        f"/api/v1/deliveries/{delivery['id']}"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_list_deliveries_with_status_filter(client):
    employee_id = create_employee(client)

    create_delivery(client)

    assigned_payload = delivery_payload("TRK002")
    assigned_payload["assigned_employee_id"] = employee_id
    create_delivery(client, assigned_payload)

    response = client.get(
        "/api/v1/deliveries",
        params={"status": "assigned"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["tracking_number"] == "TRK002"


def test_get_nonexistent_delivery(client):
    response = client.get("/api/v1/deliveries/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Delivery not found"
