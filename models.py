import enum
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from sqlalchemy import Enum,select, func ,inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Query
from sqlalchemy.orm import aliased


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

# Patient:
# {
#  'id'               :2,			
#  'name'             : 'Kavya',			
#  'last_name'        : 'Desai',			
#  'dob'              : datetime.date(1971,5,9),			
#  'email'            : 'patient0@example.com',			
#  'phone'            : '001-226-991-5605',			
#  'address'          : 'Golf Course Road,			
#  'role'             : 'patient',			
#  'password'         : 'scrypt,			
#  'status'           : 'blacklisted',			
#  'type'             : 'patient',			
#  'medical_history'  : None
#  },			


# Doctor:
# {'id'              :42,	
#  'name'            : 'Dr. Shreya',	
#  'last_name'       : 'Das',	
#  'dob'             : datetime.date(1985,	
#  'email'           : 'doctor0@example.com',	
#  'phone'           : '001-502-965-2313x787',	
#  'address'         : '5th Cross Road,	
#  'role'            : 'doctor',	
#  'password_hash'   : 'scrypt,	
#  'status'          : 'active',	
#  'type'            : 'doctor',	
#  'department_id'   :2,	
#  'license_number'  : None	
#  'experience'      :15	
#  'speciality'      : 'Expert in managing childhood growth and',    
#  },	


# Appointment:

# {'id'          :1,	
#  'patient_id'  :21,	
#  'slot_id'     :330,	
#  'doctor_id'   :42,	
#  'status'      : <AppointmentStatus.BOOKED,	
#  'reason'      : 'Chest tightness Cough with phlegm'},
# }	

# Slot:
# {'id'           :1,	
#  'doctor_id'    :42,	
#  'date'         : datetime.date(2025,	
#  'session'      : '8A',	
#  'ever_active'  : False,	
#  'available'    : True,	
#  'is_free'      : True},	
#  'status'          : 'active',	
#  'type'            : 'doctor',	
#  'department_id'   :2,	
#  'license_number'  : None	
#  'experience'      :15	
#  'speciality'      : 'Expert in managing childhood growth and	,
#  },

# Treatment:
# {'id'              :1,			
#  'appointment_id'  :2,			
#  'diagnosis'       : 'Contact dermatitis',			
#  'prescription'    : 'Insulin Aspart 2 tablets TDS for Until recovery',			
#  'notes'           : 'True five plant reality number much.',			
#  'performed_at'    : datetime.datetime(2025,			
# }

class myModel(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime(timezone = True), default= lambda : datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone = True), default= lambda : datetime.now(timezone.utc),onupdate= lambda : datetime.now(timezone.utc))


    def to_dict(self, include_relationships=False, seen=None, depth=1):
        if seen is None:
            seen = set()

        identity = (self.__class__, getattr(self, "id", None))
        if identity in seen:
            return {"id": getattr(self, "id", None)}
        seen.add(identity)

        result = {}
        mapper = self.__class__.__mapper__

        for column in mapper.columns:
            result[column.key] = getattr(self, column.key)

        if include_relationships and depth > 0:
            for rel in mapper.relationships:
                value = getattr(self, rel.key)
                if value is not None:
                    if rel.uselist:
                        result[rel.key] = [
                            obj.to_dict(True, seen, depth - 1) for obj in value
                        ]
                    else:
                        result[rel.key] = value.to_dict(True, seen, depth - 1)

        return result

    # ---------------------------------------
    @classmethod
    def from_dict(cls, data, session=None):

        subtype = data.get("type")
        if subtype and subtype != cls.__mapper_args__.get("polymorphic_identity"):
            for subclass in cls.__subclasses__():
                if hasattr(subclass, "__mapper_args__"):
                    if subclass.__mapper_args__.get("polymorphic_identity") == subtype:
                        return subclass.from_dict(data, session=session)

        obj = cls()
        mapper = cls.__mapper__

        # Only fill columns (ignore relationships)
        for column in mapper.columns:
            key = column.key
            if key in data:
                setattr(obj, key, data[key])

        if session:
            session.add(obj)

        return obj


    


# --------------------------
# Base User Model
# --------------------------
class User(myModel,UserMixin):
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

    # __mapper_args__ = {
    #     "polymorphic_identity": "user",
    #     "polymorphic_on": type,
    # }

    def __init__(self, name, email, password, last_name=None, 
                 dob=None, phone=None, address=None ,role ="patient", **kwargs):
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


# # --------------------------
# # Admin
# # --------------------------
# class Admin(User):
#     __tablename__ = "admins"

#     id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

#     __mapper_args__ = {
#         "polymorphic_identity": "admin",
#     }
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)


# --------------------------
# Department
# --------------------------
class Department(myModel):
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
class Appointment(myModel):
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

class Slot(myModel):
    __tablename__ = "availability" 
    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(20), nullable=False)   # morning / evening
    ever_active = db.Column(db.Boolean, default=False, nullable=False)
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
        self.ever_active = True
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
class Treatment(myModel):
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
    consultation_fee = db.Column(db.Integer ,default = 0)


def to_dict_any(obj, include_relationships=False):
    if isinstance(obj, list):
        return [item.to_dict(include_relationships) for item in obj]
    return obj.to_dict(include_relationships)

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

def search_all(search_term, table=None):
    """
    Search across all tables (or a specified one) for the search_term.
    Includes joined 'users' data for inherited tables (patients, doctors, etc.)
    and returns ALL matches.
    """
    results = []
    inspector = inspect(db.engine)
    all_tables = inspector.get_table_names()

    # Normalize table argument
    if table is None:
        tables_to_search = all_tables
    elif isinstance(table, str):
        tables_to_search = [table] if table in all_tables else []
    elif isinstance(table, (list, tuple, set)):
        tables_to_search = [t for t in table if t in all_tables]
    else:
        raise ValueError("table must be a string, list, or None")

    if not tables_to_search:
        print("⚠️ No valid tables found.")
        return results

    search_term_like = f"%{search_term}%"

    with db.engine.connect() as conn:
        for table_name in tables_to_search:
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            fks = inspector.get_foreign_keys(table_name)
            fk_to_user = next((fk for fk in fks if fk["referred_table"] == "users"), None)

            # ✅ 1. Search in joined 'users' table if applicable
            if fk_to_user:
                user_cols = [col["name"] for col in inspector.get_columns("users")]
                for user_col in user_cols:
                    try:
                        query = text(f"""
                            SELECT t.id AS id, u.{user_col} AS value
                            FROM {table_name} t
                            JOIN users u ON t.{fk_to_user['constrained_columns'][0]} = u.id
                            WHERE CAST(u.{user_col} AS TEXT) LIKE :term
                        """)
                        rows = conn.execute(query, {"term": search_term_like}).fetchall()

                        for row in rows:
                            if row.value:  # skip nulls
                                results.append({
                                    "table": table_name,
                                    "column": f"users.{user_col}",
                                    "row_id": row.id,
                                    "matched_value": row.value
                                })
                    except SQLAlchemyError:
                        continue

            # ✅ 2. Search within this table itself
            for col in columns:
                try:
                    query = text(f"""
                        SELECT id, {col} AS value
                        FROM {table_name}
                        WHERE CAST({col} AS TEXT) LIKE :term
                    """)
                    rows = conn.execute(query, {"term": search_term_like}).fetchall()

                    for row in rows:
                        if row.value:
                            results.append({
                                "table": table_name,
                                "column": col,
                                "row_id": row.id,
                                "matched_value": row.value
                            })
                except SQLAlchemyError:
                    # Some columns may not be searchable (e.g., binary, JSON)
                    continue

    # ✅ Deduplicate (optional) while keeping all distinct matches
    seen = set()
    unique_results = []
    for r in results:
        key = (r["table"], r["column"], r["row_id"], r["matched_value"])
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results
