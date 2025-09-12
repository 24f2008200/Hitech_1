from datetime import datetime
import enum
import hashlib
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Time,
    DateTime,
    Enum,
    Text,
    ForeignKey,
    create_engine,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base

Base = declarative_base()

# --- Helper utilities -------------------------------------------------

def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


# --- Enums -----------------------------------------------------------
class AppointmentStatus(enum.Enum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# --- Models ----------------------------------------------------------
class Role(enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(Enum(Role), nullable=False)

    # Optional links
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)

    patient = relationship("Patient", backref="user", uselist=False)
    doctor = relationship("Doctor", backref="user", uselist=False)

    def set_password(self, plain: str):
        self.password_hash = hash_password(plain)

    def check_password(self, plain: str) -> bool:
        return self.password_hash == hash_password(plain)

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(200))
    email = Column(String(200), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def set_password(self, plain: str):
        self.password_hash = hash_password(plain)

    def check_password(self, plain: str) -> bool:
        return self.password_hash == hash_password(plain)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationship: Department -> Doctors
    doctors = relationship("Doctor", back_populates="department", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Department(id={self.id}, name={self.name})>"


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    email = Column(String(200), unique=True)
    phone = Column(String(50))
    specialization_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    license_number = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    department = relationship("Department", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Doctor(id={self.id}, name={self.first_name} {self.last_name})>"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    dob = Column(Date)
    email = Column(String(200), unique=True)
    phone = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient(id={self.id}, name={self.first_name} {self.last_name})>"


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        # Avoid double-booking same doctor at same date/time (simple constraint example)
        UniqueConstraint("doctor_id", "date", "time", name="uix_doctor_date_time"),
        Index("ix_patient_date", "patient_id", "date"),
    )

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    department = relationship("Department")

    treatments = relationship("Treatment", back_populates="appointment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Appointment(id={self.id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, date={self.date}, time={self.time})>"


class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    diagnosis = Column(Text)
    prescription = Column(Text)
    notes = Column(Text)
    performed_at = Column(DateTime, default=datetime.utcnow)

    # relationship
    appointment = relationship("Appointment", back_populates="treatments")

    def __repr__(self):
        return f"<Treatment(id={self.id}, appointment_id={self.appointment_id})>"

