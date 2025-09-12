from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import enum
import hashlib
from datetime import datetime, date, time

# ----------------------------------
# App & DB Config
# ----------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///api_database.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ----------------------------------
# Helper
# ----------------------------------
def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


# ----------------------------------
# Enums
# ----------------------------------
class Role(enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"


class AppointmentStatus(enum.Enum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ----------------------------------
# Models
# ----------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False)

    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=True)

    def __init__(self, username: str, password: str, role: Role, patient_id=None, doctor_id=None):
        self.username = username
        self.set_password(password)
        self.role = role
        self.patient_id = patient_id
        self.doctor_id = doctor_id

    def set_password(self, plain: str):
        self.password_hash = hash_password(plain)

    def check_password(self, plain: str) -> bool:
        return self.password_hash == hash_password(plain)


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)

    doctors = db.relationship("Doctor", back_populates="department")


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(200), unique=True)
    phone = db.Column(db.String(50))
    license_number = db.Column(db.String(100), unique=True)

    specialization_id = db.Column(db.Integer, db.ForeignKey("department.id"))
    department = db.relationship("Department", back_populates="doctors")

    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")
    user = db.relationship("User", backref="doctor_account", uselist=False)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    dob = db.Column(db.Date)
    email = db.Column(db.String(200), unique=True)
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)

    appointments = db.relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    user = db.relationship("User", backref="patient_account", uselist=False)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)

    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    reason = db.Column(db.Text)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    treatments = db.relationship("Treatment", back_populates="appointment", cascade="all, delete-orphan")


class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship("Appointment", back_populates="treatments")


# ----------------------------------
# Init & Seed Function
# ----------------------------------
def init_db():
    db.drop_all()
    db.create_all()

    # Seed Admin
    admin = User(username="admin", password="admin123", role=Role.ADMIN)
    db.session.add(admin)

    # Departments
    dept1 = Department(name="General Medicine", description="General practice and family medicine")
    dept2 = Department(name="Cardiology", description="Heart and vascular specialists")
    db.session.add_all([dept1, dept2])

    # Doctors
    doctor1 = Doctor(first_name="Deepak", last_name="Jumani", email="deepak@hospital.com",
                     phone="111-222-3333", license_number="DOC1001", department=dept1)
    doctor2 = Doctor(first_name="Abhishek", last_name="Jumani", email="abhishek@hospital.com",
                     phone="444-555-6666", license_number="DOC2001", department=dept2)
    doctor3 = Doctor(first_name="Amit", last_name="Devidaos", email="amit@hospital.com",
                     phone="555-666-7777", license_number="DOC3001", department=dept1)
    doctor4 = Doctor(first_name="Ashiwarya", last_name="Tendulkar", email="ashiwarya@hospital.com",
                     phone="888-999-0000", license_number="DOC4001", department=dept2)
    db.session.add_all([doctor1, doctor2, doctor3, doctor4])
    db.session.flush()

    # Users for doctors
    user_doc1 = User(username="deepak", password="deepak123", role=Role.DOCTOR, doctor_id=doctor1.id)
    user_doc2 = User(username="abhishek", password="abhishek123", role=Role.DOCTOR, doctor_id=doctor2.id)
    user_doc3 = User(username="amit", password="amit123", role=Role.DOCTOR, doctor_id=doctor3.id)
    user_doc4 = User(username="ashiwarya", password="ashiwarya123", role=Role.DOCTOR, doctor_id=doctor4.id)
    db.session.add_all([user_doc1, user_doc2, user_doc3, user_doc4])

    # Patient
    patient1 = Patient(first_name="Hiral", last_name="Nagarkar", dob=date(1990, 5, 20),
                       email="hiral@patient.com", phone="777-888-9999", address="123 Main St")
    patient2 = Patient(first_name="Ram", last_name="Shennoy", dob=date(1985, 3, 15),
                       email="ram@patient.com", phone="888-999-0000", address="456 Elm St")
    patient3 = Patient(first_name="Lakshman", last_name="Sonawane", dob=date(1992, 7, 30),
                       email="lakshman@patient.com", phone="999-000-1111", address="789 Oak St")
    patient4 = Patient(first_name="Thushar", last_name="Begde", dob=date(1988, 11, 25),
                       email="thushar@patient.com", phone="000-111-2222", address="101 Pine St")

    db.session.add_all([patient1, patient2, patient3, patient4])
    db.session.flush()  # assign patient1.id before user creation

    # User for patient
    user_pat1 = User(username="hiral", password="hiral123", role=Role.PATIENT, patient_id=patient1.id)
    user_pat2 = User(username="ram", password="ram123", role=Role.PATIENT, patient_id=patient2.id)
    user_pat3 = User(username="lakshman", password="lakshman123", role=Role.PATIENT, patient_id=patient3.id)
    user_pat4 = User(username="thushar", password="thushar123", role=Role.PATIENT, patient_id=patient4.id)
    db.session.add_all([user_pat1, user_pat2, user_pat3, user_pat4])

    # Appointments
    appt1 = Appointment(patient=patient1, doctor=doctor1, department_id=dept1.id,
                        date=date(2025, 9, 15), time=time(10, 0),
                        status=AppointmentStatus.BOOKED, reason="Regular checkup")
    appt2 = Appointment(patient=patient1, doctor=doctor2, department_id=dept2.id,
                        date=date(2025, 9, 16), time=time(14, 30),
                        status=AppointmentStatus.COMPLETED, reason="Chest pain consultation")
    appt3 = Appointment(patient=patient2, doctor=doctor3, department_id=dept1.id,
                        date=date(2025, 9, 17), time=time(9, 0),
                        status=AppointmentStatus.BOOKED, reason="Flu symptoms")
    appt4 = Appointment(patient=patient3, doctor=doctor4, department_id=dept2.id,
                        date=date(2025, 9, 18), time=time(11, 15),
                        status=AppointmentStatus.CANCELLED, reason="Follow-up on blood test")
    db.session.add_all([appt1, appt2, appt3, appt4])
    db.session.flush()

    # Treatments for completed appointment
    treat1 = Treatment(appointment=appt2, diagnosis="Mild hypertension",
                       prescription="Beta-blockers", notes="Monitor BP weekly")
    treat2 = Treatment(appointment=appt3, diagnosis="Flu",
                       prescription="Rest and hydration", notes="Follow up in a week")
    treat3 = Treatment(appointment=appt4, diagnosis="Anxiety",
                       prescription="Cognitive Behavioral Therapy", notes="Refer to psychologist")
    treat4 = Treatment(appointment=appt1, diagnosis="General Checkup",
                       prescription="Multivitamins", notes="Annual physical exam")

    db.session.add_all([treat1, treat2, treat3, treat4])

    db.session.commit()
    print(" Database initialized with sample data.")


# ----------------------------------
# Run Script
# ----------------------------------
if __name__ == "__main__":
    with app.app_context():
        init_db()
