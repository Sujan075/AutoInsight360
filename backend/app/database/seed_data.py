"""
AutoInsight360 - Synthetic Data Generator
==========================================
Generates realistic but entirely fictitious automotive customer data
for demonstration and development purposes.

IMPORTANT — DATA DISCLAIMER
----------------------------
All records produced by this module are SYNTHETIC.
No real personal information, vehicle identification numbers,
phone numbers, email addresses or postal codes are used.
VINs are prefixed with 'SYNTH-' to make this unambiguous.
Synthetic emails use the domain '@autoinsight.demo'.

Usage
-----
Called from scripts/seed_db.py via seed_database().

Design
------
- A fixed RANDOM_SEED ensures reproducibility.
- Records are generated in dependency order:
    dealers → customers → vehicles → transactions →
    service_visits → loyalty_events → customer_reviews
- Every foreign key reference points to a valid parent record.
- Duplicate prevention: check by unique field before inserting.
"""

from __future__ import annotations

import datetime
import logging
import random
import string
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.database.models import (
    Customer,
    CustomerReview,
    Dealer,
    LoyaltyEvent,
    ServiceVisit,
    Transaction,
    Vehicle,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Reference data for synthetic generation
# ---------------------------------------------------------------------------
_FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "William", "Barbara", "David", "Susan", "Richard", "Jessica",
    "Joseph", "Karen", "Thomas", "Sarah", "Charles", "Lisa", "Christopher",
    "Nancy", "Daniel", "Betty", "Matthew", "Margaret", "Anthony", "Sandra",
    "Mark", "Ashley", "Donald", "Dorothy", "Steven", "Kimberly", "Paul",
    "Emily", "Andrew", "Donna", "Joshua", "Michelle", "Kenneth", "Carol",
    "Kevin", "Amanda", "Brian", "Melissa", "George", "Deborah", "Timothy",
    "Stephanie", "Ronald", "Rebecca", "Edward", "Sharon", "Jason", "Laura",
    "Jeffrey", "Cynthia", "Ryan", "Kathleen", "Jacob", "Amy", "Gary",
    "Angela", "Nicholas", "Shirley", "Eric", "Anna", "Jonathan", "Brenda",
    "Stephen", "Pamela", "Larry", "Emma", "Justin", "Nicole", "Scott",
    "Helen", "Brandon", "Samantha", "Benjamin", "Katherine", "Samuel",
    "Christine", "Raymond", "Debra", "Gregory", "Rachel", "Frank",
    "Carolyn", "Alexander", "Janet", "Patrick", "Catherine", "Jack",
    "Maria", "Dennis", "Heather", "Jerry", "Diane",
]

_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

_CITIES_STATES = [
    ("Houston", "TX"), ("Phoenix", "AZ"), ("San Antonio", "TX"),
    ("San Diego", "CA"), ("Dallas", "TX"), ("Jacksonville", "FL"),
    ("Columbus", "OH"), ("Charlotte", "NC"), ("Indianapolis", "IN"),
    ("Seattle", "WA"), ("Denver", "CO"), ("Nashville", "TN"),
    ("Oklahoma City", "OK"), ("El Paso", "TX"), ("Boston", "MA"),
    ("Portland", "OR"), ("Las Vegas", "NV"), ("Memphis", "TN"),
    ("Louisville", "KY"), ("Baltimore", "MD"),
]

_VEHICLE_DATA = [
    # (make, model, body_style, fuel_type)
    ("Toyota", "Camry", "Sedan", "Gasoline"),
    ("Toyota", "RAV4", "SUV", "Hybrid"),
    ("Toyota", "Highlander", "SUV", "Gasoline"),
    ("Toyota", "Tacoma", "Truck", "Gasoline"),
    ("Toyota", "Corolla", "Sedan", "Gasoline"),
    ("Honda", "Accord", "Sedan", "Gasoline"),
    ("Honda", "CR-V", "SUV", "Hybrid"),
    ("Honda", "Civic", "Sedan", "Gasoline"),
    ("Honda", "Pilot", "SUV", "Gasoline"),
    ("Ford", "F-150", "Truck", "Gasoline"),
    ("Ford", "Explorer", "SUV", "Gasoline"),
    ("Ford", "Mustang", "Coupe", "Gasoline"),
    ("Ford", "Escape", "SUV", "Hybrid"),
    ("Chevrolet", "Silverado", "Truck", "Gasoline"),
    ("Chevrolet", "Equinox", "SUV", "Gasoline"),
    ("Chevrolet", "Malibu", "Sedan", "Gasoline"),
    ("BMW", "3 Series", "Sedan", "Gasoline"),
    ("BMW", "X5", "SUV", "Gasoline"),
    ("BMW", "5 Series", "Sedan", "Gasoline"),
    ("Mercedes-Benz", "C-Class", "Sedan", "Gasoline"),
    ("Mercedes-Benz", "GLE", "SUV", "Gasoline"),
    ("Audi", "A4", "Sedan", "Gasoline"),
    ("Audi", "Q5", "SUV", "Gasoline"),
    ("Tesla", "Model 3", "Sedan", "Electric"),
    ("Tesla", "Model Y", "SUV", "Electric"),
    ("Nissan", "Altima", "Sedan", "Gasoline"),
    ("Nissan", "Rogue", "SUV", "Gasoline"),
    ("Hyundai", "Elantra", "Sedan", "Gasoline"),
    ("Hyundai", "Tucson", "SUV", "Gasoline"),
    ("Kia", "Sorento", "SUV", "Gasoline"),
    ("Kia", "Telluride", "SUV", "Gasoline"),
    ("Jeep", "Grand Cherokee", "SUV", "Gasoline"),
    ("Dodge", "Ram 1500", "Truck", "Gasoline"),
]

_COLORS = [
    "White", "Black", "Silver", "Gray", "Red", "Blue", "Green",
    "Brown", "Gold", "Orange", "Yellow", "Pearl White", "Midnight Black",
]

_TRIMS = [
    "Base", "Sport", "Limited", "Premium", "Platinum", "SE", "LE",
    "XLE", "XSE", "TRD Pro", "Touring", "EX", "EX-L", "Elite",
]

_TRANSMISSIONS = ["Automatic", "Manual", "CVT", "DCT"]

_ENGINES = [
    "2.0L 4-Cylinder", "2.5L 4-Cylinder", "3.5L V6", "5.0L V8",
    "2.0L Turbocharged", "3.0L Turbocharged", "Electric Motor",
    "2.0L Hybrid", "1.8L 4-Cylinder",
]

_SERVICE_TYPES = [
    "Oil Change",
    "Tyre Rotation",
    "Brake Inspection",
    "Major Service",
    "Air Filter Replacement",
    "Transmission Service",
    "Coolant Flush",
    "Battery Replacement",
    "Wheel Alignment",
    "Recall Service",
    "Warranty Repair",
    "Multi-Point Inspection",
    "Windshield Replacement",
    "AC Service",
]

_SERVICE_COSTS = {
    "Oil Change": (45, 120),
    "Tyre Rotation": (25, 60),
    "Brake Inspection": (80, 300),
    "Major Service": (300, 900),
    "Air Filter Replacement": (20, 55),
    "Transmission Service": (200, 600),
    "Coolant Flush": (90, 180),
    "Battery Replacement": (100, 350),
    "Wheel Alignment": (75, 150),
    "Recall Service": (0, 0),
    "Warranty Repair": (0, 0),
    "Multi-Point Inspection": (40, 100),
    "Windshield Replacement": (200, 500),
    "AC Service": (100, 350),
}

_TRANSACTION_TYPES = [
    "vehicle_purchase",
    "service_payment",
    "parts",
    "accessories",
    "financing",
]

_PAYMENT_METHODS = ["cash", "card", "finance", "lease"]

_REVIEW_TITLES_BY_RATING = {
    5: [
        "Outstanding service every time!",
        "Absolutely love my new vehicle",
        "Best dealership I've visited",
        "Five stars — no hesitation",
        "Exceeded all my expectations",
        "Top-notch customer service",
    ],
    4: [
        "Very happy overall",
        "Great experience, minor wait",
        "Recommended dealer",
        "Good service, good price",
        "Pleasant buying experience",
    ],
    3: [
        "Average experience",
        "Decent but could be better",
        "Nothing special, but fine",
        "Service was okay",
        "Mixed feelings overall",
    ],
    2: [
        "Somewhat disappointed",
        "Service took too long",
        "Expected more for the price",
        "Communication was lacking",
    ],
    1: [
        "Would not recommend",
        "Very poor experience",
        "Serious issues with service",
        "Disappointed and frustrated",
    ],
}

_REVIEW_BODIES = [
    "The team was professional and kept me informed throughout the process.",
    "I had to wait longer than expected but the work was done correctly.",
    "My vehicle was returned clean and in excellent condition.",
    "The service advisor explained everything clearly before proceeding.",
    "Pricing was fair and transparent with no hidden charges.",
    "The waiting lounge was comfortable and well equipped.",
    "They completed the work ahead of schedule, which I appreciated.",
    "Follow-up communication after the service was excellent.",
    "The technician took extra care with my vehicle.",
    "I'll definitely return for my next scheduled service.",
    "The dealership matched the online quote exactly.",
    "I had a minor concern which was resolved quickly and professionally.",
    "The service manager was attentive and genuinely helpful.",
    "Parts availability was an issue but they resolved it promptly.",
    "Overall a positive experience I would recommend to others.",
    "The process was smooth from start to finish.",
    "The team went above and beyond to ensure my satisfaction.",
    "A few administrative delays but the technical work was flawless.",
    "I appreciate the digital service report they emailed afterwards.",
    "The technician identified an additional issue and consulted me first.",
]

_DEALER_DATA = [
    {
        "name": "AutoInsight Premier — Houston",
        "city": "Houston",
        "state": "TX",
        "phone": "555-100-0001",
        "email": "houston@autoinsight.demo",
    },
    {
        "name": "AutoInsight Premier — Phoenix",
        "city": "Phoenix",
        "state": "AZ",
        "phone": "555-100-0002",
        "email": "phoenix@autoinsight.demo",
    },
    {
        "name": "AutoInsight Premier — Dallas",
        "city": "Dallas",
        "state": "TX",
        "phone": "555-100-0003",
        "email": "dallas@autoinsight.demo",
    },
    {
        "name": "AutoInsight Premier — Seattle",
        "city": "Seattle",
        "state": "WA",
        "phone": "555-100-0004",
        "email": "seattle@autoinsight.demo",
    },
    {
        "name": "AutoInsight Premier — Nashville",
        "city": "Nashville",
        "state": "TN",
        "phone": "555-100-0005",
        "email": "nashville@autoinsight.demo",
    },
]

_SEGMENTS = ["Premium", "Standard", "Fleet", "First-Time Buyer", "Loyal"]
_PREFERRED_CONTACTS = ["email", "phone", "sms"]
_GENDERS = ["Male", "Female", "Non-binary", "Prefer not to say"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _random_date(
    rng: random.Random,
    start: datetime.date,
    end: datetime.date,
) -> datetime.date:
    delta = (end - start).days
    return start + datetime.timedelta(days=rng.randint(0, delta))


def _random_postal(rng: random.Random) -> str:
    return f"{rng.randint(10000, 99999)}"


def _synth_vin(rng: random.Random, index: int) -> str:
    """Generate a clearly synthetic VIN that cannot be confused with a real one."""
    suffix = "".join(rng.choices(string.ascii_uppercase + string.digits, k=8))
    return f"SYNTH-{index:04d}-{suffix}"


def _synth_email(first: str, last: str, index: int) -> str:
    """Generate a clearly synthetic email using the .demo TLD."""
    return f"{first.lower()}.{last.lower()}{index}@autoinsight.demo"


def _synth_phone(rng: random.Random) -> str:
    """Generate a synthetic phone number in 555-NXX-XXXX format."""
    return f"555-{rng.randint(200, 999)}-{rng.randint(1000, 9999)}"


def _synth_ref(rng: random.Random, prefix: str, index: int) -> str:
    suffix = "".join(rng.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{index:06d}-{suffix}"


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_dealers(db: Session) -> list[Dealer]:
    """Seed the fixed set of dealers.  Idempotent: skip if name already exists."""
    dealers: list[Dealer] = []
    for data in _DEALER_DATA:
        existing = db.query(Dealer).filter(Dealer.name == data["name"]).first()
        if existing:
            dealers.append(existing)
            logger.debug("Dealer %r already exists — skipping.", data["name"])
        else:
            dealer = Dealer(country="USA", is_active=True, **data)
            db.add(dealer)
            db.flush()
            dealers.append(dealer)
            logger.debug("Created dealer %r.", data["name"])
    db.commit()
    logger.info("Dealers ready: %d total.", len(dealers))
    return dealers


def seed_customers(db: Session, rng: random.Random, count: int = 100) -> list[Customer]:
    """Seed synthetic customers.  Idempotent: returns existing if already at target count."""
    existing_count = db.query(Customer).count()
    if existing_count >= count:
        logger.info(
            "Customers already seeded (%d >= %d target).", existing_count, count
        )
        return db.query(Customer).order_by(Customer.id).all()

    customers: list[Customer] = list(db.query(Customer).order_by(Customer.id).all())
    existing_emails = {c.email for c in customers}

    today = datetime.date.today()
    dob_start = today.replace(year=today.year - 70)
    dob_end = today.replace(year=today.year - 18)

    for i in range(count):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        email = _synth_email(first, last, i + 1)
        if email in existing_emails:
            continue

        city, state = rng.choice(_CITIES_STATES)
        dob = _random_date(rng, dob_start, dob_end)
        segment = rng.choice(_SEGMENTS)
        registered_days_ago = rng.randint(30, 365 * 8)
        registered_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            days=registered_days_ago
        )

        customer = Customer(
            first_name=first,
            last_name=last,
            email=email,
            phone=_synth_phone(rng),
            date_of_birth=dob,
            gender=rng.choice(_GENDERS),
            city=city,
            state=state,
            country="USA",
            postal_code=_random_postal(rng),
            customer_segment=segment,
            preferred_contact=rng.choice(_PREFERRED_CONTACTS),
            is_active=rng.choices([True, False], weights=[90, 10])[0],
            loyalty_points_balance=0,
            registered_at=registered_at,
            updated_at=registered_at,
        )
        db.add(customer)
        customers.append(customer)
        existing_emails.add(email)

        if len(customers) >= count:
            break

    db.commit()
    logger.info("Customers ready: %d total.", len(customers))
    return customers


def seed_vehicles(
    db: Session,
    rng: random.Random,
    customers: list[Customer],
) -> list[Vehicle]:
    """
    Seed synthetic vehicles.

    - Each customer gets 1–2 vehicles; some premium customers get 3.
    - One vehicle per customer is flagged as primary.
    - Idempotent: customers who already have vehicles are skipped.
    """
    existing_vehicles = list(db.query(Vehicle).order_by(Vehicle.id).all())
    existing_customer_ids = {v.customer_id for v in existing_vehicles}

    # If all provided customers already have vehicles, return existing
    if customers and all(c.id in existing_customer_ids for c in customers):
        logger.info(
            "Vehicles already seeded (%d vehicles for %d customers).",
            len(existing_vehicles),
            len(customers),
        )
        return existing_vehicles

    vehicles: list[Vehicle] = list(existing_vehicles)
    existing_vins = {v.vin for v in existing_vehicles}
    vin_index = len(existing_vehicles)
    today = datetime.date.today()

    for customer in customers:
        if customer.id in existing_customer_ids:
            continue

        num_vehicles = rng.choices([1, 2, 3], weights=[55, 35, 10])[0]
        for v_i in range(num_vehicles):
            vin_index += 1
            vin = _synth_vin(rng, vin_index)
            while vin in existing_vins:
                vin_index += 1
                vin = _synth_vin(rng, vin_index)

            make, model, body_style, fuel_type = rng.choice(_VEHICLE_DATA)
            year = rng.randint(2008, 2025)
            purchase_date = _random_date(
                rng,
                today.replace(year=today.year - (2025 - year) - 1),
                today,
            )
            purchase_price = round(rng.uniform(15_000, 85_000), 2)
            mileage_at_purchase = rng.randint(0, 40_000) if year < 2023 else 0
            current_mileage = mileage_at_purchase + rng.randint(500, 60_000)
            transmission = (
                "Automatic" if fuel_type == "Electric"
                else rng.choice(_TRANSMISSIONS)
            )

            vehicle = Vehicle(
                customer_id=customer.id,
                vin=vin,
                make=make,
                model=model,
                year=year,
                color=rng.choice(_COLORS),
                trim=rng.choice(_TRIMS),
                body_style=body_style,
                fuel_type=fuel_type,
                transmission=transmission,
                engine=rng.choice(_ENGINES),
                purchase_date=purchase_date,
                purchase_price=purchase_price,
                mileage_at_purchase=mileage_at_purchase,
                current_mileage=current_mileage,
                is_primary=(v_i == 0),  # first vehicle is primary
                is_active=True,
            )
            db.add(vehicle)
            vehicles.append(vehicle)
            existing_vins.add(vin)
            existing_customer_ids.add(customer.id)

    db.commit()
    logger.info("Vehicles ready: %d total.", len(vehicles))
    return vehicles


def seed_transactions(
    db: Session,
    rng: random.Random,
    customers: list[Customer],
    vehicles: list[Vehicle],
    dealers: list[Dealer],
    target_count: int = 400,
) -> list[Transaction]:
    """
    Seed synthetic transactions.

    Transaction distribution:
    - Vehicle purchase transactions are linked to a vehicle.
    - Service payments and parts are common repeat transactions.
    - Idempotent: returns existing if already at target count.
    """
    existing_count = db.query(Transaction).count()
    if existing_count >= target_count:
        logger.info(
            "Transactions already seeded (%d >= %d target).", existing_count, target_count
        )
        return db.query(Transaction).order_by(Transaction.id).all()

    transactions: list[Transaction] = list(db.query(Transaction).order_by(Transaction.id).all())
    existing_refs = {t.reference_number for t in transactions}
    tx_index = len(transactions)
    today = datetime.date.today()

    # Build a lookup: customer_id → list of vehicles
    cust_to_vehicles: dict[int, list[Vehicle]] = {}
    for v in vehicles:
        cust_to_vehicles.setdefault(v.customer_id, []).append(v)

    needed = target_count - len(transactions)
    for _ in range(needed):
        tx_index += 1
        ref = _synth_ref(rng, "TXN", tx_index)
        while ref in existing_refs:
            tx_index += 1
            ref = _synth_ref(rng, "TXN", tx_index)

        customer = rng.choice(customers)
        dealer = rng.choice(dealers)
        tx_type = rng.choices(
            _TRANSACTION_TYPES,
            weights=[15, 40, 20, 15, 10],
        )[0]

        cust_vehicles = cust_to_vehicles.get(customer.id, [])
        vehicle = rng.choice(cust_vehicles) if cust_vehicles else None

        if tx_type == "vehicle_purchase":
            amount = round(rng.uniform(15_000, 90_000), 2)
        elif tx_type in ("service_payment",):
            amount = round(rng.uniform(45, 900), 2)
        elif tx_type in ("parts", "accessories"):
            amount = round(rng.uniform(20, 500), 2)
        else:  # financing
            amount = round(rng.uniform(200, 2_000), 2)

        days_ago = rng.randint(0, 365 * 5)
        tx_date = today - datetime.timedelta(days=days_ago)

        transaction = Transaction(
            customer_id=customer.id,
            dealer_id=dealer.id,
            vehicle_id=vehicle.id if vehicle else None,
            transaction_type=tx_type,
            amount=amount,
            currency="USD",
            transaction_date=tx_date,
            payment_method=rng.choice(_PAYMENT_METHODS),
            status=rng.choices(
                ["completed", "completed", "completed", "refunded", "pending"],
                weights=[80, 5, 5, 7, 3],
            )[0],
            reference_number=ref,
            notes=None,
        )
        db.add(transaction)
        transactions.append(transaction)
        existing_refs.add(ref)

    db.commit()
    logger.info("Transactions ready: %d total.", len(transactions))
    return transactions


def seed_service_visits(
    db: Session,
    rng: random.Random,
    vehicles: list[Vehicle],
    dealers: list[Dealer],
    target_count: int = 300,
) -> list[ServiceVisit]:
    """
    Seed synthetic service visit records.

    - Each vehicle gets at least 1 service visit.
    - Additional visits are distributed randomly.
    - Idempotent: based on count comparison (service visits have no unique key).
    """
    service_visits: list[ServiceVisit] = []
    today = datetime.date.today()
    existing_count = db.query(ServiceVisit).count()
    if existing_count >= target_count:
        logger.info(
            "Service visits already seeded (%d >= %d target).", existing_count, target_count
        )
        return db.query(ServiceVisit).all()

    # Ensure every vehicle has at least one service visit
    for vehicle in vehicles:
        dealer = rng.choice(dealers)
        svc_type = rng.choice(_SERVICE_TYPES)
        low, high = _SERVICE_COSTS.get(svc_type, (50, 200))
        cost = round(rng.uniform(low, high), 2) if high > 0 else 0.0
        days_ago = rng.randint(10, 365 * 4)
        svc_date = today - datetime.timedelta(days=days_ago)
        mileage = (vehicle.mileage_at_purchase or 0) + rng.randint(500, 40_000)

        sv = ServiceVisit(
            vehicle_id=vehicle.id,
            dealer_id=dealer.id,
            service_type=svc_type,
            service_date=svc_date,
            mileage_at_service=mileage,
            cost=cost,
            description=f"Scheduled {svc_type.lower()} for vehicle {vehicle.vin}.",
            technician_notes=rng.choice([None, "No issues found.", "Minor wear noted.", "Parts replaced."]),
            is_warranty=(svc_type in ("Recall Service", "Warranty Repair")),
            next_service_date=svc_date + datetime.timedelta(days=rng.randint(90, 365)),
        )
        db.add(sv)
        service_visits.append(sv)

    db.flush()

    # Add additional visits to reach target_count
    additional_needed = target_count - len(service_visits)
    for _ in range(max(0, additional_needed)):
        vehicle = rng.choice(vehicles)
        dealer = rng.choice(dealers)
        svc_type = rng.choice(_SERVICE_TYPES)
        low, high = _SERVICE_COSTS.get(svc_type, (50, 200))
        cost = round(rng.uniform(low, high), 2) if high > 0 else 0.0
        days_ago = rng.randint(0, 365 * 5)
        svc_date = today - datetime.timedelta(days=days_ago)
        mileage = (vehicle.mileage_at_purchase or 0) + rng.randint(500, 80_000)

        sv = ServiceVisit(
            vehicle_id=vehicle.id,
            dealer_id=dealer.id,
            service_type=svc_type,
            service_date=svc_date,
            mileage_at_service=mileage,
            cost=cost,
            description=f"Service visit for {vehicle.make} {vehicle.model} ({vehicle.year}).",
            technician_notes=rng.choice([None, "Completed per schedule.", "Customer concern addressed."]),
            is_warranty=(svc_type in ("Recall Service", "Warranty Repair")),
            next_service_date=svc_date + datetime.timedelta(days=rng.randint(90, 365)),
        )
        db.add(sv)
        service_visits.append(sv)

    db.commit()
    logger.info("Service visits ready: %d total.", len(service_visits))
    return service_visits


def seed_loyalty_events(
    db: Session,
    rng: random.Random,
    customers: list[Customer],
    transactions: list[Transaction],
    target_count: int = 400,
) -> list[LoyaltyEvent]:
    """
    Seed loyalty events and update each customer's points balance.

    Rules:
    - Earn events: ~10 points per $100 spent on transactions.
    - Redeem events: random redemptions for some customers.
    - Bonus events: occasional bonus points.
    - Running balance is tracked per customer.
    - Idempotent: based on count comparison.
    """
    loyalty_events: list[LoyaltyEvent] = []
    existing_count = db.query(LoyaltyEvent).count()
    if existing_count >= target_count:
        logger.info(
            "Loyalty events already seeded (%d >= %d target).", existing_count, target_count
        )
        return db.query(LoyaltyEvent).all()

    # Build a lookup: customer_id → list of transactions
    cust_transactions: dict[int, list[Transaction]] = {}
    for tx in transactions:
        cust_transactions.setdefault(tx.customer_id, []).append(tx)

    # Track running balances (start from current DB balance)
    balances: dict[int, int] = {c.id: c.loyalty_points_balance for c in customers}

    for customer in customers:
        cust_txns = cust_transactions.get(customer.id, [])

        # Earn points from each transaction
        for tx in cust_txns:
            if tx.status != "completed":
                continue
            earned = max(1, int(float(tx.amount) / 100 * 10))
            balances[customer.id] = balances.get(customer.id, 0) + earned

            le = LoyaltyEvent(
                customer_id=customer.id,
                event_type="earn",
                points=earned,
                event_date=tx.transaction_date,
                description=f"Points earned on transaction {tx.reference_number}.",
                related_transaction_id=tx.id,
                balance_after=balances[customer.id],
            )
            db.add(le)
            loyalty_events.append(le)

        # Occasional redemption for customers with enough balance
        if balances.get(customer.id, 0) > 500 and rng.random() < 0.4:
            redeem = rng.randint(100, min(500, balances[customer.id]))
            balances[customer.id] -= redeem
            le = LoyaltyEvent(
                customer_id=customer.id,
                event_type="redeem",
                points=-redeem,
                event_date=datetime.date.today() - datetime.timedelta(days=rng.randint(1, 365)),
                description="Points redeemed for service discount.",
                related_transaction_id=None,
                balance_after=balances[customer.id],
            )
            db.add(le)
            loyalty_events.append(le)

        # Random bonus for some customers
        if rng.random() < 0.25:
            bonus = rng.randint(50, 300)
            balances[customer.id] = balances.get(customer.id, 0) + bonus
            le = LoyaltyEvent(
                customer_id=customer.id,
                event_type="bonus",
                points=bonus,
                event_date=datetime.date.today() - datetime.timedelta(days=rng.randint(1, 180)),
                description="Promotional bonus points awarded.",
                related_transaction_id=None,
                balance_after=balances[customer.id],
            )
            db.add(le)
            loyalty_events.append(le)

    # Update customer point balances
    db.flush()
    for customer in customers:
        customer.loyalty_points_balance = max(0, balances.get(customer.id, 0))

    db.commit()
    logger.info("Loyalty events ready: %d total.", len(loyalty_events))
    return loyalty_events


def seed_reviews(
    db: Session,
    rng: random.Random,
    customers: list[Customer],
    dealers: list[Dealer],
    vehicles: list[Vehicle],
    target_count: int = 150,
) -> list[CustomerReview]:
    """
    Seed synthetic customer reviews.

    - Reviews are of type: dealer, vehicle, or service.
    - Ratings are skewed toward positive (realistic distribution).
    - Idempotent: based on count comparison.
    """
    reviews: list[CustomerReview] = []
    existing_count = db.query(CustomerReview).count()
    if existing_count >= target_count:
        logger.info(
            "Reviews already seeded (%d >= %d target).", existing_count, target_count
        )
        return db.query(CustomerReview).all()

    cust_to_vehicles: dict[int, list[Vehicle]] = {}
    for v in vehicles:
        cust_to_vehicles.setdefault(v.customer_id, []).append(v)

    today = datetime.date.today()

    for _ in range(target_count):
        customer = rng.choice(customers)
        review_type = rng.choice(["dealer", "vehicle", "service"])
        # Realistic rating distribution: skewed high
        rating = rng.choices([1, 2, 3, 4, 5], weights=[3, 5, 10, 25, 57])[0]
        title = rng.choice(_REVIEW_TITLES_BY_RATING[rating])
        body = " ".join(rng.choices(_REVIEW_BODIES, k=rng.randint(1, 3)))
        days_ago = rng.randint(1, 365 * 3)
        review_date = today - datetime.timedelta(days=days_ago)

        dealer = rng.choice(dealers) if review_type in ("dealer", "service") else None
        cust_vehicles = cust_to_vehicles.get(customer.id, [])
        vehicle = rng.choice(cust_vehicles) if cust_vehicles and review_type in ("vehicle", "service") else None

        review = CustomerReview(
            customer_id=customer.id,
            dealer_id=dealer.id if dealer else None,
            vehicle_id=vehicle.id if vehicle else None,
            review_type=review_type,
            rating=rating,
            title=title,
            body=body,
            review_date=review_date,
            is_verified=rng.choices([True, False], weights=[60, 40])[0],
            is_published=rng.choices([True, False], weights=[90, 10])[0],
        )
        db.add(review)
        reviews.append(review)

    db.commit()
    logger.info("Reviews ready: %d total.", len(reviews))
    return reviews


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def seed_database(db: Session, reset: bool = False) -> dict:
    """
    Seed all synthetic data into the database.

    Parameters
    ----------
    db      : SQLAlchemy Session
    reset   : If True, the caller has already confirmed a reset and
              tables have been recreated; seed proceeds unconditionally.

    Returns
    -------
    dict mapping table names to row counts generated.
    """
    rng = random.Random(RANDOM_SEED)

    logger.info("=== AutoInsight360 Synthetic Data Seed (seed=%d) ===", RANDOM_SEED)

    dealers = seed_dealers(db)
    customers = seed_customers(db, rng, count=100)
    vehicles = seed_vehicles(db, rng, customers)
    transactions = seed_transactions(db, rng, customers, vehicles, dealers, target_count=400)
    service_visits = seed_service_visits(db, rng, vehicles, dealers, target_count=300)
    loyalty_events = seed_loyalty_events(db, rng, customers, transactions, target_count=400)
    reviews = seed_reviews(db, rng, customers, dealers, vehicles, target_count=150)

    counts = {
        "dealers": db.query(Dealer).count(),
        "customers": db.query(Customer).count(),
        "vehicles": db.query(Vehicle).count(),
        "transactions": db.query(Transaction).count(),
        "service_visits": db.query(ServiceVisit).count(),
        "loyalty_events": db.query(LoyaltyEvent).count(),
        "customer_reviews": db.query(CustomerReview).count(),
    }

    logger.info("=== Seed complete: %s ===", counts)
    return counts
