
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func

from app.core.database import Base, SessionLocal, engine
from app.models.employee import Employee
from app.models.delivery import Delivery


CITIES = ["Delhi", "Mumbai", "Bengaluru"]

EMPLOYEES_PER_CITY = 5
TOTAL_DELIVERIES = 500

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Reyansh",
    "Ishita", "Ananya", "Diya", "Saanvi", "Myra",
    "Rahul", "Priya", "Rohan", "Neha", "Karan",
    "Sneha", "Amit", "Kavya", "Riya", "Vikram",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Gupta",
    "Kumar", "Mehta", "Reddy", "Malhotra", "Joshi",
]

ADDRESSES = {
    "Delhi": [
        "Connaught Place",
        "Dwarka Sector 12",
        "Rohini Sector 7",
        "Saket",
        "Karol Bagh",
        "Lajpat Nagar",
        "Vasant Kunj",
        "Janakpuri",
    ],
    "Mumbai": [
        "Andheri West",
        "Bandra West",
        "Powai",
        "Dadar",
        "Borivali",
        "Lower Parel",
        "Goregaon",
        "Kurla",
    ],
    "Bengaluru": [
        "Whitefield",
        "Electronic City",
        "Indiranagar",
        "Koramangala",
        "Marathahalli",
        "Jayanagar",
        "Hebbal",
        "HSR Layout",
    ],
}

STATUS_DISTRIBUTION = {
    "pending": 70,
    "assigned": 65,
    "picked_up": 55,
    "in_transit": 100,
    "delivered": 150,
    "delayed": 35,
    "failed": 15,
    "cancelled": 10,
}


def create_employees(db):
    employees_by_city = {}
    created_count = 0

    for city_index, city in enumerate(CITIES):
        employees_by_city[city] = []

        for employee_number in range(1, EMPLOYEES_PER_CITY + 1):
            employee_code = (
                f"SWR-{city[:3].upper()}-{employee_number:03d}"
            )

            employee = db.scalar(
                select(Employee).where(
                    Employee.employee_code == employee_code
                )
            )

            if employee is None:
                employee = Employee(
                    employee_code=employee_code,
                    name=(
                        f"{FIRST_NAMES[(city_index * 5 + employee_number - 1) % len(FIRST_NAMES)]} "
                        f"{LAST_NAMES[(employee_number + city_index) % len(LAST_NAMES)]}"
                    ),
                    phone=f"+91-00000-{employee_number + city_index * 100:05d}",
                    city=city,
                    is_active=True,
                )

                db.add(employee)
                created_count += 1

            elif employee.city.casefold() != city.casefold():
                raise ValueError(
                    f"Seed employee {employee_code} belongs to "
                    f"{employee.city}, expected {city}"
                )

            employees_by_city[city].append(employee)

    db.flush()

    for city, employees in employees_by_city.items():
        if not any(employee.is_active for employee in employees):
            raise RuntimeError(
                f"No active seed employees available in {city}"
            )

    print(f"Employees created: {created_count}")

    return employees_by_city


def build_status_list():
    statuses = []

    for delivery_status, count in STATUS_DISTRIBUTION.items():
        statuses.extend([delivery_status] * count)

    if len(statuses) != TOTAL_DELIVERIES:
        raise ValueError("Status distribution must total 500")

    return statuses



def build_delivery_timeline(rng, delivery_status, now):
    delivered_at = None

    if delivery_status in {"pending", "assigned"}:
        created_at = now - timedelta(hours=rng.randint(1, 24 * 14))
        scheduled_delivery = now + timedelta(hours=rng.randint(6, 72))

    elif delivery_status in {"picked_up", "in_transit"}:
        scheduled_delivery = now + timedelta(hours=rng.randint(-12, 36))
        created_at = min(
            now - timedelta(hours=rng.randint(6, 24 * 10)),
            scheduled_delivery - timedelta(hours=1),
        )

    elif delivery_status == "delayed":
        scheduled_delivery = now - timedelta(hours=rng.randint(1, 48))
        created_at = scheduled_delivery - timedelta(hours=rng.randint(12, 72))

    elif delivery_status == "delivered":
        scheduled_delivery = now - timedelta(hours=rng.randint(1, 72))
        created_at = scheduled_delivery - timedelta(hours=rng.randint(12, 72))

        delivered_at = min(
            now,
            scheduled_delivery + timedelta(hours=rng.randint(-8, 12)),
        )
        delivered_at = max(created_at, delivered_at)

    else:
        scheduled_delivery = now - timedelta(hours=rng.randint(1, 72))
        created_at = scheduled_delivery - timedelta(hours=rng.randint(12, 72))

    updated_at = (
        delivered_at
        if delivered_at is not None
        else min(
            now,
            created_at + timedelta(hours=rng.randint(1, 48)),
        )
    )

    return created_at, scheduled_delivery, delivered_at, updated_at

def create_deliveries(db, employees_by_city):
    rng = random.Random(42)
    now = datetime.now(timezone.utc)

    statuses = build_status_list()
    rng.shuffle(statuses)

    existing_numbers = set(
        db.scalars(
            select(Delivery.tracking_number).where(
                Delivery.tracking_number.like("SWR-2026-%")
            )
        ).all()
    )

    new_deliveries = []

    for index, delivery_status in enumerate(statuses, start=1):
        tracking_number = f"SWR-2026-{index:04d}"

        if tracking_number in existing_numbers:
            continue

        city = CITIES[(index - 1) % len(CITIES)]

        active_employees = [
            employee
            for employee in employees_by_city[city]
            if employee.is_active
        ]

        assigned_employee = None

        if delivery_status != "pending":
            assigned_employee = rng.choice(active_employees)

        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)

        pickup_area = rng.choice(ADDRESSES[city])
        delivery_area = rng.choice(ADDRESSES[city])

        while delivery_area == pickup_area:
            delivery_area = rng.choice(ADDRESSES[city])

        (
            created_at,
            scheduled_delivery,
            delivered_at,
            updated_at,
        ) = build_delivery_timeline(
            rng,
            delivery_status,
            now,
        )



        delivery = Delivery(
            tracking_number=tracking_number,
            customer_name=f"{first_name} {last_name}",
            customer_phone=f"+91-00000-{index:05d}",
            city=city,
            pickup_address=f"{pickup_area}, {city}",
            delivery_address=f"{delivery_area}, {city}",
            status=delivery_status,
            priority=rng.choices(
                ["low", "normal", "high", "urgent"],
                weights=[15, 45, 30, 10],
                k=1,
            )[0],
            scheduled_delivery=scheduled_delivery,
            delivered_at=delivered_at,
            assigned_employee_id=(
                assigned_employee.id
                if assigned_employee
                else None
            ),
            created_at=created_at,
            updated_at=updated_at,
        )

        new_deliveries.append(delivery)

    db.add_all(new_deliveries)
    db.commit()

    print(f"Deliveries created: {len(new_deliveries)}")


def seed_database():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        employees_by_city = create_employees(db)
        create_deliveries(db, employees_by_city)

        employee_count = db.scalar(
            select(func.count()).select_from(Employee).where(
                Employee.employee_code.like("SWR-%")
            )
        )

        delivery_count = db.scalar(
            select(func.count()).select_from(Delivery).where(
                Delivery.tracking_number.like("SWR-2026-%")
            )
        )

        print("\nSeed completed successfully")
        print(f"Seed employees: {employee_count}")
        print(f"Seed deliveries: {delivery_count}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
