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

@app.route("/login", methods=["POST" ,"GET"])
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
    patients = {appt.patient for appt in appointments if appt.patient is not None}  # unique patients
    print (patients)
    return render_template("doctor_dashboard.html", doctor=doctor, appointments=appointments, patients=patients)

@app.route("/patient/dashboard")
@patient_required
def patient_dashboard():
    patient =  current_user
    appointments = patient.appointments
    departments = Department.query.all()
    treatments = [t for appt in appointments for t in appt.treatments]
    return render_template("patient_dashboard.html", patient=patient, appointments=appointments,\
                            treatments=treatments,departments=departments)
@app.route("/department_details/<int:dept_id>")
@login_required
def department_details(dept_id):

    department = Department.query.get_or_404(dept_id)
    doctors = Doctor.query.filter_by(department_id=dept_id).all()

    return render_template(
        "department_details.html",
        department=department,
        doctors=doctors
    )



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
        appointment=appointment,
        diagnosis=diagnosis,
        prescription=prescription,
        visit_type =visit_type,
        tests=test_done,
        medicines= medicines,
        notes=f"VisitType: {visit_type}, Test: {test_done}, Medicines: {medicines}"
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
    return jsonify({"status": "success", "message": "Availability saved successfully"})


@app.route("/availability")
@doctor_required
def availability():
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

    for rec in avail_records:
        slots[rec.date.isoformat()][rec.session] = rec.available

    return render_template("availability.html", days=days, slots=slots, doctor_id=doctor_id)


@app.route("/availability/<int:doctor_id>")
@login_required
def doctor_availability(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    today = date.today()
    months = []

    for m in range(4):  # next 4 months
        month_start = (today.replace(day=1) + timedelta(days=32*m)).replace(day=1)
        year, month = month_start.year, month_start.month

        # Get all weeks for this month (as list of weeks, each week = [Mon..Sun])
        cal = calendar.Calendar(firstweekday=0)  # Monday = 0
        weeks = cal.monthdatescalendar(year, month)

        # Get all availability for that month
        month_end = weeks[-1][-1]
        availabilities = Availability.query.filter(
            Availability.doctor_id == doctor_id,
            Availability.date >= month_start,
            Availability.date <= month_end
        ).all()

        avail_map = {(a.date, a.session): a for a in availabilities}
        months.append((month_start, weeks, avail_map))

    return render_template("booking.html", doctor=doctor, months=months)

@app.route("/doctor_details/<int:doctor_id>")
@login_required
def doctor_details(doctor_id):
    return "ToDO"

@app.route("/doctor/<int:doctor_id>/book", methods=["POST"])
@login_required
def appointments_book(doctor_id):
    date_str = request.form.get("date")
    session = request.form.get("session")
    patient_id = 1  # TODO: replace with logged-in patient’s ID

    if not date_str or not session:
        flash("Please select a slot before booking.", "danger")
        return redirect(url_for("doctor_availability", doctor_id=doctor_id))

    # convert date string to date
    selected_date = datetime.fromisoformat(date_str).date()

    # find availability
    avail = Availability.query.filter_by(
        doctor_id=doctor_id, date=selected_date, session=session
    ).first()

    if not avail or not avail.available:
        flash("Selected slot is not available.", "danger")
        return redirect(url_for("doctor_availability", doctor_id=doctor_id))

    if avail.is_busy:
        flash("This slot has already been booked by another patient.", "danger")
        return redirect(url_for("doctor_availability", doctor_id=doctor_id))
    date = selected_date
    time = datetime.fromisoformat(date_str).time()
    status = AppointmentStatus.BOOKED
    reason = "Test"
    availability_id = db.Column(db.Integer, db.ForeignKey("availability.id"), nullable=False)

    # create appointment
    appt = Appointment(patient_id=patient_id, doctor_id=doctor_id, availability=avail ,date=date, time=time, status=status)
    db.session.add(appt)
    db.session.commit()

    flash("Appointment booked successfully!", "success")
    return redirect(url_for("doctor_availability", doctor_id=doctor_id))

@app.route("/patient/history/<int:patient_id>")
@doctor_required
def patient_history(patient_id):
    # pagination settings
    page = request.args.get("page", 1, type=int)
    per_page = 10   # visits per page

    # Fetch from DB (example, replace with ORM query)
    patient = Patient.query.get_or_404(patient_id)
    treatments = [
        appt.treatments
        for appt in patient.appointments
        if appt.treatments is not None
    ]
    for t in treatments:
        print (t)
    all_visits = []
    for treatment_list in treatments:
        for tr in treatment_list:
            all_visits.append({
                "visit_type": tr.visit_type,
                "diagnosis": tr.diagnosis,
                "prescription": tr.prescription,
                "medicines": tr.medicines,
                "tests": tr.tests
            })

    total = len(all_visits)
    start = (page - 1) * per_page
    end = start + per_page
    visits = all_visits[start:end]

    total_pages = (total + per_page - 1) // per_page  # ceil division


    doctor = current_user


    return render_template("patient_history.html",
                           patient=patient,
                           doctor=doctor,
                           visits=visits,
                           page=page,
                           total_pages=total_pages,
                           patient_id=patient_id,
                           return_address =  url_for('doctor_dashboard')
                           )


@app.route("/update_slot/<int:doctor_id>", methods=["POST"])
@doctor_required
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


@app.route("/admin/add_department", methods=["GET", "POST"])
def add_department():


        if current_user.role != "admin":
            flash("❌ Unauthorized", "danger")
            return redirect(url_for("home"))

        departments = Department.query.all()

        if request.method == "POST":
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            email = request.form["email"]
            phone = request.form["phone"]
            license_number = request.form["license_number"]
            specialization_id = request.form["specialization_id"]
            username = request.form["username"]
            password = request.form["password"]

            # Create Doctor
            doctor = Doctor(first_name=first_name, last_name=last_name,
                            email=email, phone=phone, license_number=license_number,
                            specialization_id=specialization_id)
            db.session.add(doctor)
            db.session.flush()

            # Create User
            user = User(username=username, password=password, role=Role.DOCTOR, doctor_id=doctor.id)
            db.session.add(user)
            db.session.commit()

            flash("✅ Doctor added successfully!", "success")
            return redirect(url_for("admin_dashboard"))

        return render_template("add_department.html", departments="")
@app.route("/doctors/new", methods=["GET", "POST"])
@admin_required
def add_doctor():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        specialization = request.form.get("specialization")
        experience = request.form.get("experience")
        dept_id = request.form.get("department_id")

        if not fullname or not specialization:
            flash("Fullname and specialization are required.", "danger")
            return redirect(url_for("admin.add_doctor"))

        doctor = Doctor(
            fullname=fullname,
            specialization=specialization,
            experience_years=int(experience) if experience else None,
            department_id=int(dept_id) if dept_id else None
        )
        db.session.add(doctor)
        db.session.commit()
        flash("Doctor added successfully!", "success")
        return redirect(url_for("admin.list_doctors"))

    departments = Department.query.all()
    return render_template("add_doctor.html", departments=departments)


if __name__ == "__main__":
    app.run(debug=True)