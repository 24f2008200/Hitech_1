from flask import Flask
from faker import Faker
import random
from datetime import date, timedelta

from models import db, Admin, Department, Doctor, Patient, Slot, Appointment, AppointmentStatus, Treatment, User,Sessions

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///api_database.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

fake = Faker()


def seed_database():
    db.drop_all()
    db.create_all()
    print("✅ Tables dropped & recreated")

    # -----------------
    # 1 Admin
    # -----------------
    admin = Admin(
        name="Super",
        last_name="Admin",
        email="admin@example.com",
        password="123",
        role="admin",
    )
    db.session.add(admin)

    # -----------------
    # 10 Departments
    # -----------------
    dept_names = [
        "Cardiology", "Neurology", "Orthopedics", "Pediatrics", "Oncology",
        "Dermatology", "Gastroenterology", "ENT", "Urology", "Endocrinology"
    ]
    departments = []
    for name in dept_names:
        d = Department(name=name, description=fake.sentence(nb_words=8))
        db.session.add(d)
        departments.append(d)
    db.session.commit()
    print("✅ Departments created")

    # -----------------
    # 40 Patients
    # -----------------
    patients = []
    for i in range(40):
        p = Patient(
            name=fake.first_name(),
            last_name=fake.last_name(),
            email=f"patient{i}@example.com",
            password="123",
            role="patient",
        )
        db.session.add(p)
        patients.append(p)
    db.session.commit()
    print(f"✅ Created {len(patients)} patients")

    # -----------------
    # 10 Doctors
    # -----------------
    doctors = []
    for i in range(10):
        doc = Doctor(
            name=f"Dr. {fake.first_name()}",
            last_name=fake.last_name(),
            email=f"doctor{i}@example.com",
            password="123",
            role="doctor",
            department=random.choice(departments),
        )
        db.session.add(doc)
        doctors.append(doc)
    db.session.commit()
    print(f"✅ Created {len(doctors)} doctors")

    # -----------------
    # Slot: 90 days × 2 sessions = 180 slots per doctor
    # -----------------
    sessions = [s.value for s in Sessions]
    start_date = date.today()
    slots_by_doctor = {}
    for doc in doctors:
        slots_by_doctor[doc.id] = []
        for offset in range(90):
            d = start_date + timedelta(days=offset)
            for sess in sessions:
                slot = Slot(doctor=doc, date=d, session=sess, available=True)
                db.session.add(slot)
                slots_by_doctor[doc.id].append(slot)
    db.session.commit()
    print("✅ Created availability slots")

    # -----------------
    # For each doctor: 10 booked appts + 5 completed with treatments
    # -----------------
    for doc in doctors:
        free_slots = [s for s in slots_by_doctor[doc.id] if s.available and s.is_free ]
        random.shuffle(free_slots)

        # 10 booked
        for slot in free_slots[:10]:
            patient = random.choice(patients)
            try:
                appt = slot.book(patient_id=patient.id, reason=fake.sentence(nb_words=6))
                db.session.add(appt)
                db.session.commit()
            except Exception as e:
                db.session.rollback()

                


        # refresh free slots
        free_slots = [s for s in slots_by_doctor[doc.id] if s.available and s.is_free]
        random.shuffle(free_slots)

        # 5 completed
        for slot in free_slots[:5]:
            patient = random.choice(patients)
            appt = slot.book(patient_id=patient.id, reason=fake.sentence(nb_words=6))
            db.session.add(appt)
            db.session.commit()

            # complete + treatment
            appt.complete({
                "diagnosis": fake.sentence(nb_words=6),
                "prescription": fake.sentence(nb_words=6),
                "notes": fake.paragraph(nb_sentences=2),
                "visit_type": random.choice(["OPD", "Follow-up", "Emergency"]),
                "tests": random.choice(["ECG", "Blood Test", "X-Ray", "MRI"]),
                "medicines": fake.sentence(nb_words=4),
            })
            db.session.commit()


    print("✅ Appointments & treatments created")
    print("🎉 Database seeding finished.")


if __name__ == "__main__":
    with app.app_context():
        seed_database()
