import enum
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin

db = SQLAlchemy()

# --------------------------
# Enums
# --------------------------
class AppointmentStatus(enum.Enum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# --------------------------
# Base User Model
# --------------------------
class User(db.Model,UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    dob = db.Column(db.Date)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    role = db.Column(db.String(10))

    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="active")  # active / blacklisted

    type = db.Column(db.String(50))  # discriminator column

    __mapper_args__ = {
        "polymorphic_identity": "user",
        "polymorphic_on": type,
    }

    def __init__(self, name, email, password, last_name=None, dob=None, phone=None, address=None):
        self.name = name
        self.email = email
        self.last_name = last_name
        self.dob = dob
        self.phone = phone
        self.address = address
        self.set_password(password)

    def set_password(self, plain_password: str):
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        return check_password_hash(self.password_hash, plain_password)


# --------------------------
# Admin
# --------------------------
class Admin(User):
    __tablename__ = "admins"

    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "admin",
    }


# --------------------------
# Department
# --------------------------
class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)

    doctors = db.relationship("Doctor", back_populates="department")


# --------------------------
# Doctor
# --------------------------
class Doctor(User):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))

    department = db.relationship("Department", back_populates="doctors")
    appointments = db.relationship("Appointment", back_populates="doctor")
    availability = db.relationship("Availability", back_populates="doctor", cascade="all, delete-orphan")


    __mapper_args__ = {
        "polymorphic_identity": "doctor",
    }


# --------------------------
# Patient
# --------------------------
class Patient(User):
    __tablename__ = "patients"

    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    medical_history = db.Column(db.Text)

    appointments = db.relationship("Appointment", back_populates="patient")

    __mapper_args__ = {
        "polymorphic_identity": "patient",
    }


# --------------------------
# Appointment
# --------------------------
class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    reason = db.Column(db.Text)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    treatments = db.relationship("Treatment", back_populates="appointment", cascade="all, delete-orphan")

class Availability(db.Model):
    __tablename__ = "availability"
    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(20), nullable=False)   # morning / afternoon / evening
    available = db.Column(db.Boolean, default=False, nullable=False)

    # ensure uniqueness of (doctor_id, date, session)
    __table_args__ = (
        db.UniqueConstraint("doctor_id", "date", "session", name="unique_doctor_slot"),
    )

    # relationship back to Doctor
    doctor = db.relationship("Doctor", back_populates="availability")

# --------------------------
# Treatment
# --------------------------
class Treatment(db.Model):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    visit_type = db.Column(db.Text)
    tests = db.Column(db.Text)
    medicines = db.Column(db.Text)
    appointment = db.relationship("Appointment", back_populates="treatments")
