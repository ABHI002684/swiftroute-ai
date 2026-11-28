
import pytest

from datetime import datetime, timedelta, timezone

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


def add_employee(db, code="TEST001"):
    employee = Employee(
        employee_code=code,
        name="Test Employee",
        city="Delhi",
        is_active=True,
    )
    db.add(employee)
    db.flush()
    return employee


def add_delivery(
    db,
    tracking_number,
    status,
    scheduled_delivery,
    employee_id=None,
):
    delivery = Delivery(
        tracking_number=tracking_number,
        customer_name="Test Customer",
        city="Delhi",
        pickup_address="Connaught Place, Delhi",
        delivery_address="Dwarka, Delhi",
        status=status,
        priority="normal",
        scheduled_delivery=scheduled_delivery,
        assigned_employee_id=employee_id,
    )
    db.add(delivery)


def test_dashboard_overview_counts(client):
    from app.core.database import SessionLocal

    # Use the overridden test database through the dependency.
    response = client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200

    data = response.json()

    assert data["total_deliveries"] == 0
    assert data["delivered"] == 0
    assert data["completion_rate"] == 0.0


def test_dashboard_completion_rate(client):
    from app.core.database import SessionLocal

    # The fixture database is populated through the test dependency.
    db = next(app.dependency_overrides[get_db]())

    try:
        add_delivery(
            db,
            "TEST-001",
            "delivered",
            datetime.now(timezone.utc) - timedelta(hours=1),
        )
        add_delivery(
            db,
            "TEST-002",
            "pending",
            datetime.now(timezone.utc) + timedelta(hours=12),
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    assert response.json()["total_deliveries"] == 2
    assert response.json()["completion_rate"] == 50.0


def test_overdue_excludes_terminal_deliveries(client):
    db = next(app.dependency_overrides[get_db]())

    past = datetime.now(timezone.utc) - timedelta(hours=5)

    try:
        add_delivery(db, "TEST-001", "pending", past)
        add_delivery(db, "TEST-002", "delivered", past)
        add_delivery(db, "TEST-003", "cancelled", past)
        add_delivery(db, "TEST-004", "failed", past)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    assert response.json()["overdue_deliveries"] == 1


def test_delayed_overdue_delivery_counted_once(client):
    db = next(app.dependency_overrides[get_db]())

    past = datetime.now(timezone.utc) - timedelta(hours=5)

    try:
        add_delivery(db, "TEST-001", "delayed", past)
        add_delivery(db, "TEST-002", "pending", past)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    assert response.json()["delayed"] == 1
    assert response.json()["overdue_deliveries"] == 2
    assert response.json()["deliveries_requiring_attention"] == 2


def test_dashboard_active_employee_count(client):
    db = next(app.dependency_overrides[get_db]())

    try:
        add_employee(db, "TEST001")
        add_employee(db, "TEST002")

        inactive = Employee(
            employee_code="TEST003",
            name="Inactive Employee",
            city="Delhi",
            is_active=False,
        )
        db.add(inactive)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    assert response.json()["active_employees"] == 2
