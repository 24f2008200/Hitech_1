import os
import calendar
from flask import Flask, render_template, redirect, url_for, request ,send_from_directory, flash
from models import db,Admin ,  Appointment ,  Department , Doctor ,  Patient ,  Treatment ,  User,Availability
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from models import AppointmentStatus
from werkzeug.security import check_password_hash
from package.routes.auth import admin_required,  doctor_required, patient_required
from flask_wtf import CSRFProtect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from datetime import datetime ,timedelta ,date
import enum
from faker import Faker
import random
from datetime import datetime, timedelta



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
