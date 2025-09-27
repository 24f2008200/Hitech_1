import os
from flask import Flask, render_template, redirect, url_for, request ,send_from_directory, flash
from models import db,Admin ,  Appointment ,  Department , Doctor ,  Patient ,  Treatment ,  User,Availability
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from models import db, User
from werkzeug.security import check_password_hash
from package.routes.auth import admin_required,  doctor_required, patient_required
from flask_wtf import CSRFProtect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from datetime import datetime ,timedelta ,date
from collections import defaultdict

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///api_database.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret-key"  # 🔒 use .env in real app!
app.config['SECRET_KEY'] = 'supersecretkey'  # Needed for CSRF tokens


db.init_app(app)
# jwt = JWTManager(app)
# csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login" 

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/")
def index():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/login", methods=["POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)  # stores ID in session
            role = user.role
            dashboard = "admin_dashboard" if role =="admin" else "doctor_dashboard" if role =="doctor" else "patient_dashboard"
            return redirect(url_for(dashboard))
        return "Invalid credentials", 401
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return render_template("login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    doctors = Doctor.query.all()
    patients = Patient.query.all()
    appointments = Appointment.query.all()
    return render_template("admin_dashboard.html", doctors=doctors, patients=patients, appointments=appointments)

@app.route("/doctor/dashboard")
@doctor_required
def doctor_dashboard():
    doctor  = current_user
    appointments = doctor.appointments
    patients = {appt.patient for appt in appointments}  # unique patients
    return render_template("doctor_dashboard.html", doctor=doctor, appointments=appointments, patients=patients)

@app.route("/patient/dashboard")
@patient_required
def patient_dashboard():
    patient =  current_user
    appointments = patient.appointments
    treatments = [t for appt in appointments for t in appt.treatments]
    return render_template("patient_dashboard.html", patient=patient, appointments=appointments, treatments=treatments)

@app.route("/doctor/update_history", methods=["POST"])
@login_required
def update_history():
    if current_user.type != "doctor":
        return "Forbidden", 403

    appt_id = request.form.get("appointment_id")
    visit_type = request.form.get("visit_type")
    test_done = request.form.get("test_done")
    diagnosis = request.form.get("diagnosis")
    prescription = request.form.get("prescription")
    medicines = request.form.get("medicines")

    # Create Treatment entry linked to appointment
    appointment = Appointment.query.get_or_404(appt_id)
    treatment = Treatment(
        appointment = appointment,
        diagnosis = diagnosis,
        prescription = prescription,
        notes =f"VisitType: {visit_type}, Test: {test_done}, Medicines: {medicines}"
    )
    db.session.add(treatment)
    db.session.commit()

    flash("Patient history updated successfully", "success")
    return redirect(url_for("doctor_dashboard"))


@app.route("/doctor/save_availability", methods=["POST"])
@login_required
def save_availability():
    if current_user.type != "doctor":
        return "Forbidden", 403

    data = request.get_json()
    doctor_id = current_user.id
    slots = data.get("slots", [])  # e.g., ["2025-01-21-morning-1", "2025-01-22-evening-0"]
    for slot in slots:
        date_str = slot["date"]
        session = slot["session"]
        flag = slot["available"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        is_avail = flag == True

        # Upsert availability
        record = Availability.query.filter_by(doctor_id=doctor_id, date=date_obj, session=session).first()
        if record:
            record.available = is_avail
        else:
            db.session.add(Availability(
                doctor_id=doctor_id,
                date=date_obj,
                session=session,
                available=is_avail
            ))


    db.session.commit()
    print("done")
    flash("Availability saved successfully", "success")
    return redirect(url_for("doctor_dashboard"))

@app.route("/doctor/availability")
@login_required
def doctor_availability():
    doctor_id = current_user.id
    start = date.today()
    days = [start + timedelta(days=i) for i in range(90)]

    # Fetch existing availability from DB
    avail_records = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        Availability.date.between(start, days[-1])
    ).all()

    # Map: {date: {session: available}}
    slots = {d.isoformat(): {"morning": False, "afternoon": False, "evening": False}
             for d in days}

    # Group days by month
    months = defaultdict(list)
    for d in days:
        months[d.strftime("%B %Y")].append(d)

    return render_template(
        "availability.html",
        months=months,
        slots=slots,
        doctor_id=current_user.id
    )

@app.route("/availability/<int:doctor_id>")
def availability(doctor_id):
    start = date.today()
    days = [start + timedelta(days=i) for i in range(90)]

    # Fetch existing availability from DB
    avail_records = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        Availability.date.between(start, days[-1])
    ).all()

    # Map: {date: {session: available}}
    slots = {d.isoformat(): {"morning": False, "afternoon": False, "evening": False}
             for d in days}

    for rec in avail_records:
        slots[rec.date.isoformat()][rec.session] = rec.available

    return render_template("availability.html", days=days, slots=slots, doctor_id=doctor_id)
@app.route("/update_slot/<int:doctor_id>", methods=["POST"])
@login_required
def update_slot(doctor_id):
    data = request.get_json()
    date_str = data["date"]
    session = data["session"]
    available = data["available"]

    rec = Availability.query.filter_by(
        doctor_id=doctor_id, date=date.fromisoformat(date_str), session=session
    ).first()

    if not rec:
        rec = Availability(
            doctor_id=doctor_id,
            date=date.fromisoformat(date_str),
            session=session,
            available=available
        )
        db.session.add(rec)
    else:
        rec.available = available

    db.session.commit()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
