
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Admin, Department, Doctor, Patient, Appointment, Treatment, User, Role, AppointmentStatus
import enum 


# --- Database creation & sample seeding -------------------------------

def create_database(uri: str = "sqlite:///hospital.db", echo: bool = False):
    engine = create_engine(uri, echo=echo)
    Base.metadata.create_all(engine)
    return engine


def seed_sample_data(session):
    # Create a predefined admin (only if not present)
    if not session.query(Admin).filter_by(username="admin").first():
        admin = Admin(username="admin", full_name="Hospital Administrator", email="admin@example.com")
        admin.set_password("admin123")
        session.add(admin)

    # Departments
    general = session.query(Department).filter_by(name="General Medicine").first()
    if not general:
        general = Department(name="General Medicine", description="General practice and family medicine")
        session.add(general)

    cardiology = session.query(Department).filter_by(name="Cardiology").first()
    if not cardiology:
        cardiology = Department(name="Cardiology", description="Heart and vascular specialists")
        session.add(cardiology)

    session.commit()

    # Doctors
    if not session.query(Doctor).filter_by(email="dr.ravi@example.com").first():
        dr = Doctor(first_name="Ravi", last_name="Kumar", email="dr.ravi@example.com", phone="+91-9000000000", specialization_id=general.id, license_number="LIC-001")
        session.add(dr)

    if not session.query(Doctor).filter_by(email="dr.anita@example.com").first():
        dr2 = Doctor(first_name="Anita", last_name="Singh", email="dr.anita@example.com", phone="+91-9000000001", specialization_id=cardiology.id, license_number="LIC-002")
        session.add(dr2)

    session.commit()

    # Patient
    if not session.query(Patient).filter_by(email="patient.ashok@example.com").first():
        p = Patient(first_name="Ashok", last_name="Sharma", email="patient.ashok@example.com")
        session.add(p)
        session.commit()
    else:
        p = session.query(Patient).filter_by(email="patient.ashok@example.com").first()

    # Appointment (sample)
    from datetime import date, time

    dr = session.query(Doctor).filter_by(email="dr.ravi@example.com").first()
    if dr:
        existing = session.query(Appointment).filter_by(patient_id=p.id, doctor_id=dr.id).first()
        if not existing:
            appt = Appointment(patient_id=p.id, doctor_id=dr.id, department_id=general.id, date=date.today(), time=time(hour=15, minute=30), status=AppointmentStatus.BOOKED, reason="General checkup")
            session.add(appt)
            session.commit()

            # Add Treatment for that appointment
            treat = Treatment(appointment_id=appt.id, diagnosis="Mild fever", prescription="Paracetamol 500mg twice daily", notes="Rest and hydration")
            session.add(treat)
            session.commit()


if __name__ == "__main__":
    engine = create_database("sqlite:///hospital.db", echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    seed_sample_data(session)

    print("Database created and sample data seeded into hospital.db")
    print("- Admin user: username=admin password=admin123 (demo) - change this for real deployments")

