
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


def test_health_endpoint(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_employee_list_endpoint(client):
    response = client.get("/api/v1/employees")

    assert response.status_code == 200


def test_delivery_list_endpoint(client):
    response = client.get("/api/v1/deliveries")

    assert response.status_code == 200


def test_dashboard_overview_endpoint(client):
    response = client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200

    data = response.json()

    expected_fields = {
        "total_deliveries",
        "delivered",
        "pending",
        "in_transit",
        "delayed",
        "failed",
        "active_employees",
        "completion_rate",
        "overdue_deliveries",
        "deliveries_requiring_attention",
    }

    assert expected_fields.issubset(data.keys())


def test_api_documentation_available(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    expected_paths = [
        "/api/v1/health",
        "/api/v1/employees",
        "/api/v1/deliveries",
        "/api/v1/dashboard/overview",
    ]

    for path in expected_paths:
        assert path in paths
