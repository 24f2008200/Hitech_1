import enum
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from sqlalchemy import Enum,select, func ,inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Query








db = SQLAlchemy()

    
# --------------------------
# Enums
# --------------------------
class AppointmentStatus(enum.Enum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
class Sessions(enum.Enum):
    S1 = "8A"
    S2 = "9A"
    S3 = "10A"
    S4 = "11A"
    S5 = "5P"
    S6 = "6P"
    S7 = "7P"
    S8 = "8P"



class myModel:
    def to_dict(self, include_relationships=False, seen=None):
        if seen is None:
            seen = set()

        identity = (self.__class__, self.id)
        if identity in seen:
            return {"id": self.id}
        seen.add(identity)

        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)

            # Handle datetime
            if isinstance(value, datetime):
                value = value.isoformat()

            # Handle Enum (like AppointmentStatus)
            elif isinstance(value, Enum):
                value = "Test" #value.value

            # Handle booleans explicitly if needed (though JSON can already do True/False)
            elif isinstance(value, bool):
                value = bool(value)

            result[column.name] = value

        # Optionally serialize relationships
        if include_relationships:
            for rel in self.__mapper__.relationships:
                related_value = getattr(self, rel.key)
                if related_value is None:
                    result[rel.key] = None
                elif isinstance(related_value, list):  # one-to-many
                    result[rel.key] = [item.to_dict(True, seen) for item in related_value]
                else:  # many-to-one / one-to-one
                    result[rel.key] = related_value.to_dict(True, seen)

        return result


    


# --------------------------
# Base User Model
# --------------------------
class User(db.Model,UserMixin,myModel):
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

    def __init__(self, name, email, password, last_name=None, 
                 dob=None, phone=None, address=None ,role ="user", **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.email = email
        self.last_name = last_name
        self.dob = dob
        self.phone = phone
        self.address = address
        self.role = role
        self.set_password(password)

    def set_password(self, plain_password: str):
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        return check_password_hash(self.password_hash, plain_password)


# --------------------------
# Admin
# --------------------------
class Admin(User,myModel):
    __tablename__ = "admins"

    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "admin",
    }
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# --------------------------
# Department
# --------------------------
class Department(db.Model,myModel):
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
    license_number = db.Column(db.String(20))
    experience = db.Column(db.Integer)
    department = db.relationship("Department", back_populates="doctors")
    appointments = db.relationship("Appointment", back_populates="doctor")
    availability = db.relationship("Slot", back_populates="doctor", cascade="all, delete-orphan")
    speciality = db.Column(db.String(100))

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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)



# --------------------------
# Appointment 
# --------------------------
class Appointment(db.Model,myModel):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey("availability.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)   # <-- add this

    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    reason = db.Column(db.Text)

    patient = db.relationship("Patient", back_populates="appointments")
    slot = db.relationship("Slot", back_populates="appointment")
    doctor = db.relationship("Doctor", back_populates="appointments")   # <-- now valid
    treatment = db.relationship("Treatment", back_populates="appointment", uselist=False)



    def cancel(self):
        """Cancel the appointment and free up the slot."""
        if self.status != AppointmentStatus.BOOKED:
            raise ValueError("Only booked appointments can be cancelled.")
        self.status = AppointmentStatus.CANCELLED
        self.slot.is_free = True
        db.session.add(self)

    def complete(self, treatment=None):
        """Mark appointment as completed and create Treatment record."""
        if self.status != AppointmentStatus.BOOKED:
            raise ValueError("Only booked appointments can be completed.")
        self.status = AppointmentStatus.COMPLETED
        self.slot.is_free = False
        self.slot.available = False # slot stays closed
        
        if treatment:
            treatment.appointment = self
            db.session.add(treatment)

        return treatment

class Slot(db.Model,myModel):
    __tablename__ = "availability" 
    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(20), nullable=False)   # morning / evening
    block_reason = db.Column(db.Text, nullable=True)      # <-- NEW
    available = db.Column(db.Boolean, default=True, nullable=False)
    is_free = db.Column(db.Boolean, default=True, nullable=False)


    doctor = db.relationship("Doctor", back_populates="availability")
    appointment = db.relationship("Appointment", back_populates="slot", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("doctor_id", "date", "session", name="unique_doctor_slot"),
    )

    @property
    def is_busy(self):
        return self.appointment is not None and self.appointment.status == AppointmentStatus.BOOKED

    # @property
    # def is_free(self):
    #     return self.available and not self.is_busy

    def book(self, patient_id, reason=None):
        if not self.available:
            raise ValueError("This slot is not available.")
        if not self.is_free:
            raise ValueError("This slot is already booked.")

        patient = Patient.query.filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError("Patient not found.")

        # Check double-booking for the patient
        for appt in patient.appointments:
            if (
                appt.slot.date == self.date
                and appt.slot.session == self.session
                and appt.status == AppointmentStatus.BOOKED
            ):
                raise ValueError("Patient already has an appointment in this slot.")

        appt = Appointment(
        patient_id=patient.id,
        doctor_id=self.doctor_id,
        slot_id=self.id,
        reason=reason,
        status=AppointmentStatus.BOOKED,
            )
        self.is_free = False
        db.session.add(appt)
        return appt

    def cancel(self):
        if not self.is_busy:
            raise ValueError("No active appointment to cancel.")

        self.appointment.status = AppointmentStatus.CANCELLED
        self.is_free = self.available
        db.session.add(self.appointment)

    def open(self, reason=None):
        """Block this slot without creating an appointment."""
        # if self.is_free:
        #     raise ValueError("slot already free.")
        self.available = True
        self.is_free = True
        self.block_reason = reason or "Unavailable"
        db.session.add(self)
        return self
    def block(self, reason=None):
        """Block this slot without creating an appointment."""
        if self.appointment is not None:
            raise ValueError("Cannot block: slot already booked.")
        self.available = False
        self.is_free = False
        self.block_reason = reason or "Unavailable"
        db.session.add(self)
        return self

# --------------------------
# Treatment
# --------------------------
class Treatment(db.Model,myModel):
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
    appointment = db.relationship("Appointment", back_populates="treatment")


def search_all(search_term):
    """
    Search across all tables and text-convertible columns in the SQLAlchemy db.
    Returns a list of dicts with table, column, row_id, and matched_value.
    """

    results = []
    inspector = inspect(db.engine)

    # Get all table names
    tables = inspector.get_table_names()

    with db.engine.connect() as conn:
        for table in tables:            # Get all column names
            columns = [col["name"] for col in inspector.get_columns(table)]

            for col in columns:
                try:
                    query = text(f"""
                        SELECT rowid as id, {col} as value
                        FROM {table}
                        WHERE CAST({col} AS TEXT) LIKE :term
                    """)

                    rows = conn.execute(query, {"term": f"%{search_term}%"}).fetchall()

                    for row in rows:
                        results.append({
                            "table": table,
                            "column": col,
                            "row_id": row.id,
                            "matched_value": row.value
                        })
                except SQLAlchemyError:
                        # Skip columns that can't be searched
                    continue

    return results
