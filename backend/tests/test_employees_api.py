
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# Import models to register their tables.
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


def employee_payload(employee_code="TEST001"):
    return {
        "employee_code": employee_code,
        "name": "Test Employee",
        "phone": "9876543210",
        "city": "Delhi",
    }


def test_create_employee(client):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(),
    )

    assert response.status_code == 201
    assert response.json()["employee_code"] == "TEST001"
    assert response.json()["name"] == "Test Employee"


def test_duplicate_employee_code(client):
    client.post(
        "/api/v1/employees",
        json=employee_payload(),
    )

    response = client.post(
        "/api/v1/employees",
        json=employee_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Employee code already exists"


def test_get_nonexistent_employee(client):
    response = client.get("/api/v1/employees/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"


def test_invalid_employee_data(client):
    response = client.post(
        "/api/v1/employees",
        json={
            "employee_code": "T",
            "name": "A",
            "city": "Delhi",
        },
    )

    assert response.status_code == 422


def test_update_nonexistent_employee(client):
    response = client.patch(
        "/api/v1/employees/99999",
        json={"city": "Mumbai"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"


def test_deactivate_employee(client):
    create_response = client.post(
        "/api/v1/employees",
        json=employee_payload(),
    )

    employee_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/employees/{employee_id}"
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Employee deactivated successfully"

    get_response = client.get(
        f"/api/v1/employees/{employee_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False
