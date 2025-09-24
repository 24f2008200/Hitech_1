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
class User( db.Model):   # <-- inherit UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False)
    is_active = db.Column(db.Boolean, default=True)   # new
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=True)

    def __init__(self, username, password, role, patient_id=None, doctor_id=None):
        self.username = username
        self.set_password(password)
        self.role = role
        self.patient_id = patient_id
        self.doctor_id = doctor_id
        self.is_active = True


    def set_password(self, plain: str):
        self.password_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()

    def check_password(self, plain: str) -> bool:
        print(self.password_hash)
        print(hashlib.sha256(plain.encode("utf-8")).hexdigest())
        return self.password_hash == hashlib.sha256(plain.encode("utf-8")).hexdigest()


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
