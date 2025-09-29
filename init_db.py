from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import enum
from faker import Faker
import random
from datetime import datetime, timedelta
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

    def __init__(self, name, email, password, last_name=None, dob=None, phone=None, address=None ,role ="user"):
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
class Admin(User):
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

    def __init__(self, **kwargs):
        self.department = kwargs.pop("department", None)
        super().__init__(**kwargs)

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
class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    reason = db.Column(db.Text)
    availability_id = db.Column(db.Integer, db.ForeignKey("availability.id"), nullable=False)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    treatments = db.relationship("Treatment", back_populates="appointment", cascade="all, delete-orphan")
    availability = db.relationship("Availability", back_populates="appointments")

class Availability(db.Model):
    __tablename__ = "availability"
    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(20), nullable=False)   # morning /  evening
    available = db.Column(db.Boolean, default=False, nullable=False)

    # ensure uniqueness of (doctor_id, date, session)
    __table_args__ = (
        db.UniqueConstraint("doctor_id", "date", "session", name="unique_doctor_slot"),
    )

    # relationship back to Doctor
    doctor = db.relationship("Doctor", back_populates="availability")
    appointments = db.relationship("Appointment", back_populates="availability", cascade="all, delete-orphan")

    @property
    def is_busy(self):
        """Session is busy if any active appointment exists."""
        return any(appt.status == "active" for appt in self.appointments)

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

# --------------------------
# Flask App Setup
# --------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///api_database.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
fake = Faker()
with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Tables created successfully!")

    
    # Departments
    dept_names = ["Cardiology", "Neurology", "Orthopedics", "Pediatrics", "Oncology"]
    departments = []
    for name in dept_names:
        d = Department(name=name, description=fake.text(max_nb_chars=50))
        db.session.add(d)
        departments.append(d)

    db.session.commit()

    # 51 Admins
    for i in range(2):
        admin = Admin(
            name=fake.first_name(),
            last_name=fake.last_name(),
            email=f"admin{i}@example.com",
            password="admin123",
            role="admin"
        )
        db.session.add(admin)

    # 5 Doctors
    doctors = []
    for i in range(5):
        doc = Doctor(
            name=f"Dr. {fake.first_name()}",
            last_name=fake.last_name(),
            email=f"doctor{i}@example.com",
            password="doc123",
            role="doctor",
            department=random.choice(departments)
        )
        db.session.add(doc)
        doctors.append(doc)

    # 5 Patients
    patients = []
    for i in range(5):
        pat = Patient(
            name=fake.first_name(),
            last_name=fake.last_name(),
            email=f"patient{i}@example.com",
            password="pat123",
            role="patient"
        )
        db.session.add(pat)
        patients.append(pat)

    db.session.commit()

    availabilities = []
    sessions = ["morning", "evening"]

    for doctor in doctors:
        for i in range(5):  # next 5 days
            for session in sessions:
                avail = Availability(
                    doctor=doctor,
                    date=(datetime.today() + timedelta(days=i)).date(),
                    session=session,
                    available=True
                )
                db.session.add(avail)
                availabilities.append(avail)

    db.session.commit()


    # 10 Appointments
    appointments = []
    for i in range(10):  # generate 10 appointments
        avail = random.choice(availabilities)  # pick an availability slot

        appt = Appointment(
            patient=random.choice(patients),
            doctor=avail.doctor,         # match doctor from availability
            date=avail.date,             # match date
            time=datetime.now().time(),  # could also depend on session
            reason=fake.sentence(),
            status=random.choice(list(AppointmentStatus)),
            availability=avail           # link relationship (auto sets availability_id)
        )

        db.session.add(appt)
        appointments.append(appt)

    db.session.commit()

    # 10 Treatments
    for i in range(10):
        tr = Treatment(
            appointment=random.choice(appointments),
            diagnosis=fake.sentence(),
            prescription=fake.sentence(),
            tests =random.choice(["ECG","Blood","Corona"]),
            visit_type =fake.text(max_nb_chars=100),
            medicines =fake.text(max_nb_chars=100),
            notes=fake.text(max_nb_chars=100)
        )
        db.session.add(tr)

    db.session.commit()

    print("Database seeded successfully!")



    print("✅ Sample data inserted!")


if __name__ == "__main__":
    app.run(debug=True)
