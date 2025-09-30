import os
import calendar
from flask import Flask, render_template, redirect, url_for, request ,send_from_directory, flash
from models import db,Admin ,  Appointment ,  Department , Doctor ,  Patient ,  Treatment ,  User,Availability
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from models import AppointmentStatus
from werkzeug.security import check_password_hash
from package.routes.auth import admin_required,  doctor_required, patient_required ,role_required
from flask_wtf import CSRFProtect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from datetime import datetime ,timedelta ,date
from sqlalchemy import and_


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///api_database.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret-key"  
app.config['SECRET_KEY'] = 'supersecretkey'  


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




@app.route("/update_appointment/<int:appt_id>")
@doctor_required
def update_appointment(appt_id):
    return "todo"

@app.route("/close_appointment/<int:appt_id>")
@doctor_required
def close_appointment(appt_id):
    return "todo"

@app.route("/cancel_appointment/<int:appt_id>")
@doctor_required
def cancel_appointment(appt_id):
    return "todo"


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
            date=date.fromisoformat(date_str), # type: ignore
            session=session,
            available=available
        )
        db.session.add(rec)
    else:
        rec.available = available

    db.session.commit()
    return jsonify({"status": "ok"})


@app.route("/appointments/book/<int:slot_id>", methods=["POST"])
def book(slot_id):
    slot = Availability.query.get_or_404(slot_id)
    patient_id = request.form["patient_id"]
    reason = request.form.get("reason")

    try:
        appt = slot.book(patient_id=patient_id, reason=reason)
        db.session.commit()
        flash("Appointment booked!", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("appointments.check_availability", doctor_id=slot.doctor_id))


@app.route("/appointments/<int:appt_id>/cancel", methods=["POST"])
def cancel(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    try:
        appt.cancel()
        db.session.commit()
        flash("Appointment cancelled and slot freed.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("doctor_dashboard", doctor_id=appt.slot.doctor_id))


@app.route("/appointments/<int:appt_id>/complete", methods=["POST"])
def complete(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    try:
        treatment = appt.complete(treatment_data={"notes": "Treatment started"})
        db.session.commit()
        flash("Appointment completed. Treatment record created.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("doctor_dashboard", doctor_id=appt.slot.doctor_id))


@app.route("/availability/<int:slot_id>/block", methods=["POST"])
def block_slot(slot_id):
    slot = Availability.query.get_or_404(slot_id)
    reason = request.form.get("reason", "On leave")

    try:
        slot.block(reason=reason)
        db.session.commit()
        flash(f"Slot on {slot.date} ({slot.session}) blocked: {reason}", "info")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("doctor_dashboard", doctor_id=slot.doctor_id))


#=====================================================================================

def field_value(obj, attr, default=""):
    if obj is None:
        return ""
    return getattr(obj, attr, default) if obj else default
def get_userID_fromEmail(email):
    user = User.query.filter_by(email=email).first()
    return user.id if user else None
def get_home_url():
    user = current_user.role
    if user == "admin":
        return url_for("admin_dashboard")
    elif user == "doctor":
        return url_for("doctor_dashboard")
    else: 
        return url_for("patient_dashboard")

def get_appointment_rows(doc_id=None, pat_id=None, start_date=None, dept_id=None, active=None):

    query = Appointment.query.join(Appointment.patient).join(Appointment.doctor).join(Appointment.slot)

    filters = []

    if doc_id:
        filters.append(Appointment.doctor_id == doc_id)
    if pat_id:
        filters.append(Appointment.patient_id == pat_id)
    if start_date:
        filters.append(Availability.date >= start_date)
    if dept_id:
        filters.append(Doctor.department_id == dept_id)
    if active is not None:
        if active: 
            filters.append(Appointment.status == AppointmentStatus.BOOKED)
        else:  
            filters.append(Appointment.status != AppointmentStatus.BOOKED)

    if filters:
        query = query.filter(and_(*filters))

    appointments = query.all()

    appointment_rows = [
        {
            "ID": a.id,
            "Doctor": f"{a.doctor.name} {a.doctor.last_name}",
            "Patient": f"{a.patient.name} {a.patient.last_name}",
            "Date": a.slot.date.strftime("%Y-%m-%d"),
            "Session": a.slot.session,
            "Department": a.doctor.department.name if a.doctor.department else "N/A",
            "Status": a.status.value,  # BOOKED / CANCELLED / COMPLETED
            "Actions": [
                {"label": "Edit", "url": url_for("edit_appointment", appointment_id=a.id), "color": "warning"},
                {"label": "Delete", "url": url_for("delete_appointment", appointment_id=a.id), "color": "danger"},
            ],
        }
        for a in appointments
    ]

    return appointment_rows

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    doctors = Doctor.query.all()
    doctor_rows = []
    for d in doctors:
        doctor_rows.append({
            "ID": d.id,
            "Name": d.name,
            "Department": d.department.name if d.department else "—",
            "Status": d.status,
            "Actions": [
                {"label": "Edit", "url": url_for("edit_doctor", doctor_id=d.id), "color": "warning"},
                {"label": "Delete", "url": url_for("delete_doctor", doctor_id=d.id), "color": "danger"},
                {"label": "Blacklist", "url": url_for("blacklist_doctor", doctor_id=d.id), "color": "dark"},
            ],
        })

    patients = Patient.query.all()
    patient_rows = [{
        "ID": p.id, 
        "Name": p.name + " " + p.last_name, 
        "Phone": p.phone,
        "Email": p.email,
        "Status": "OK" if p.status == "active" else "Blocked",
         "Actions": [
                {"label": "Edit", "url": url_for("edit_patient", patient_id=p.id), "color": "warning"},
                {"label": "Delete", "url": url_for("delete_patient", patient_id=p.id), "color": "danger"},
                {"label": "Blacklist", "url": url_for("blacklist_patient", patient_id=p.id), "color": "dark"},
            ],

        } 
        for p in patients]

    departments = Department.query.all()
    department_rows = [{
        "Name": d.name , 
        "Description": d.description, 
        "Doctors": ", ".join([ doc.name for doc in d.doctors  ]) ,
        "Actions": [
                {"label": "Edit", "url": url_for("edit_department", department_id=d.id), "color": "warning"},
                {"label": "Delete", "url": url_for("delete_department", department_id=d.id), "color": "danger"},
            ],
        }
          for d in departments ] 
    appointments_rows = get_appointment_rows()

    tabs = [
        {"label": "Doctors", "columns": ["ID", "Name", "Department", "Status", "Actions"], "rows": doctor_rows},
        {"label": "Patients", "columns": ["ID", "Name", "Phone","Email","Status","Actions"], "rows": patient_rows},
        {"label": "Departments", "columns": ["Name", "Description","Doctors","Actions"], "rows": department_rows},
        {"label": "Appointments", "columns": ["ID", "Date","Department","Doctor","Patient","Actions"], "rows": appointments_rows},
        {"label": "Availablilty", "page" : "dummy1.html"},

    ]

    return render_template("dashboard_base.html", title=None, tabs=tabs)


@app.route("/admin/add_department", methods=["GET", "POST"])
@admin_required
def add_department():
    department = None
    add_url = url_for("add_department")
    home_url =get_home_url()
    if request.method == "POST":
        if current_user.role != "admin":
            flash("❌ Unauthorized", "danger")
            return redirect(url_for("home"))

        
        deptName = request.form["deptName"]
        description = request.form["description"]
        
        department = Department(name=deptName, description = description)
        db.session.add(department)
        db.session.flush()

        try:
            db.session.commit()
            flash("✅ Department added successfully!", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating Department: {e}", "danger")
            return redirect(add_url)

    department_form = {
        "action": add_url,
        "method": "POST",
        "fields": [
            {"label": "Department Name", "name": "deptName", "type": "text",
            "required": True, "value": field_value(department, "deptName")},

            {"label": "Description", "name": "description", "type": "textarea",
            "value": field_value(department, "description")},
        ],
        "submit_label": "Add Department",
        "other_buttons" :[{"label" :"Back" ,"url":home_url}],
    }
    
    return render_template("form_base.html", form = department_form ,title = "Add Department")

@app.route("/admin/edit_department/<int:department_id>", methods=["GET", "POST"])
@admin_required
def edit_department(department_id):
    department = Department.query.get_or_404(department_id)
    edit_url = url_for("edit_department",department_id=department_id)
    home_url =get_home_url()
    if request.method == "POST":
        if current_user.role != "admin":
            flash("❌ Unauthorized", "danger")
            return redirect(url_for("home"))

        
        deptName = request.form["deptName"]
        description = request.form["description"]
        
        department.name = deptName
        department.description = description

        try:
            db.session.commit()
            flash("✅ Department added successfully!", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating Department: {e}", "danger")
            return redirect(edit_url)

    department_form = {
        "action": edit_url,
        "method": "POST",
        "fields": [
            {"label": "Department Name", "name": "deptName", "type": "text",
            "required": True, "value": field_value(department, "name")},

            {"label": "Description", "name": "description", "type": "textarea",
            "value": field_value(department, "description")},
        ],
        "submit_label": "Update Department",
        "other_buttons" :[{"label" :"Back" ,"url": home_url}],
    }
    
    return render_template("form_base.html", form = department_form ,title = "Update Department")

@app.route("/admin/delete_department/<int:department_id>", methods=["GET", "POST"])
@admin_required
def delete_department(department_id):
    return "todo"

@app.route("/doctors/new", methods=["GET", "POST"])
@admin_required
def add_doctor():
    doctor = None
    add_url = url_for("add_doctor")
    home_url =get_home_url()
    if request.method == "POST":
        name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        dob_str = request.form.get("dob")
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
                return redirect(add_url)
        else:
            dob = None
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        license_number = request.form.get("license_number")
        experience = request.form.get("experience")
        dept_id = request.form.get("department_id")
        password = request.form.get("password")
        print(name,dept_id)
        if not name or not dept_id or not email:
            flash("name and specialization are required.", "danger")
            return redirect(home_url)
        if (get_userID_fromEmail(email) is not None):
            flash("That  eEmail is in use.", "danger")
            return redirect(add_url)

            
        doctor = Doctor(
            name=name,
            last_name=last_name,
            dob=dob,
            email=email,
            phone =phone,
            address = address,
            license_number =license_number,
            experience=int(experience) if experience else None,
            department_id=int(dept_id) if dept_id else None,
            password=password
        )
        db.session.add(doctor)
        try:
            db.session.commit()
            flash("Doctor added successfully!", "success")
            return redirect(home_url)  
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating doctor: {e}", "danger")
            return redirect(add_url)

    departments = Department.query.all()

    doctor_form = {
        "action": add_url,
        "method": "POST",
        "fields": [
            {"label": "First Name", "name": "first_name", "type": "text",
            "required": True, "value": field_value(doctor, "name")},

            {"label": "Last Name", "name": "last_name", "type": "text",
            "value": field_value(doctor, "last_name")},

            {"label": "Date of Birth", "name": "dob", "type": "date",
            "required": False, "value":field_value(doctor, "dob")},

            {"label": "Email", "name": "email", "type": "email",
            "required": True, "value":field_value(doctor, "email")},

            {"label": "Phone", "name": "phone", "type": "text",
            "value":field_value(doctor, "phone")},

            {"label": "Address", "name": "address", "type": "textarea",
            "value":field_value(doctor, "address")},
            
            {"label": "License_number", "name": "license_number", "type": "text",
            "required": True, "value":field_value(doctor, "license_number")},

            {"label": "Experience in Years", "name": "experience", "type": "text",
            "value":field_value(doctor, "experience")},

            {"label": "Department", "name": "department_id", "type": "select",
            "options": [(d.id, d.name) for d in departments],
            "required": True, "value": field_value(doctor, "department_id")},

            {"label": "Password", "name": "password", "type": "text",
            "required": True, "value":""},
        ],
        "submit_label": "Add Doctor",
        "other_buttons" :[{"label" :"Back" ,"url": home_url}],
    }
    
    return render_template("form_base.html", form = doctor_form ,title = "Add Doctor")


@app.route("/admin/edit_doctor/<int:doctor_id>", methods=["GET", "POST"])
@role_required("admin", "doctor")
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    edit_url = url_for("edit_doctor",doctor_id=doctor_id)
    home_url =get_home_url()
    if request.method == "POST":
        name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        dob_str = request.form.get("dob")
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
                return redirect(edit_url)
        else:
            dob = None
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        license_number = request.form.get("license_number")
        experience = request.form.get("experience")
        dept_id = request.form.get("department_id")
        password = request.form.get("password")
        print(name,dept_id)
        if not name or not dept_id:
            flash("name and specialization are required.", "danger")
            return redirect(url_for("edit_doctor", doctor_id=doctor_id))
        if (get_userID_fromEmail(email) != doctor_id):
            flash("That  eEmail is in use.", "danger")
            return redirect(url_for("edit_doctor", doctor_id=doctor_id))
        doctor.name = name
        doctor.last_name = last_name
        doctor.dob=dob
        doctor.email = email
        doctor.phone = phone
        doctor.address = address
        doctor.license_number = license_number
        doctor.experience = experience
        doctor.department_id = dept_id

        if password:  # only update password if user entered a new one
            doctor.set_password(password)

        try:
            db.session.commit()
            flash("Doctor updated successfully.", "success")
            return redirect(home_url)  
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating doctor: {e}", "danger")
            return redirect(edit_url)
        
    departments = Department.query.all()
    back_url = current_user.role
    doctor_form = {
        "action": edit_url,
        "method": "POST",
        "fields": [
            {"label": "First Name", "name": "first_name", "type": "text",
            "required": True, "value": field_value(doctor, "name")},

            {"label": "Last Name", "name": "last_name", "type": "text",
            "value": field_value(doctor, "last_name")},

            {"label": "Date of Birth", "name": "dob", "type": "date",
            "required": False, "value":field_value(doctor, "dob")},

            {"label": "Email", "name": "email", "type": "email",
            "required": True, "value":field_value(doctor, "email")},

            {"label": "Phone", "name": "phone", "type": "text",
            "value":field_value(doctor, "phone")},

            {"label": "Address", "name": "address", "type": "textarea",
            "value":field_value(doctor, "address")},
            
            {"label": "License_number", "name": "license_number", "type": "text",
            "required": False, "value":field_value(doctor, "license_number")},

            {"label": "Experience in Years", "name": "experience", "type": "text",
            "value":field_value(doctor, "experience")},

            {"label": "Department", "name": "department_id", "type": "select",
            "options": [(d.id, d.name) for d in departments],
            "required": False, "value": field_value(doctor, "department_id")},

            {"label": "Password", "name": "password", "type": "text",
            "required": False, "value":""},
        ],

        "other_buttons" :[{"label" :"Back" ,"url": home_url}],
        "submit_label": "Update Doctor"
    }
    

    # GET request – render the edit form
    return render_template("form_base.html", form = doctor_form ,title = "Edit Doctor")

@app.route("/admin/delete_doctor/<int:doctor_id>", methods=["GET", "POST"])
@admin_required
def delete_doctor(doctor_id):
    return "todo"

@app.route("/admin/blacklist_doctor/<int:doctor_id>", methods=["GET", "POST"])
@admin_required
def blacklist_doctor(doctor_id):
    return "todo"

@app.route("/register")
def register():
    patient = None
    add_url = url_for("register")
    home_url =get_home_url()
    if request.method == "POST":
        name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        dob_str = request.form.get("dob")
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
                return redirect(add_url)
        else:
            dob = None
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        password = request.form.get("password")

        if not name or not password:
            flash("name and password are required.", "danger")
            return redirect(add_url)
        if (get_userID_fromEmail(email) != None):
            flash("That  eEmail is in use.", "danger")
            return redirect(add_url)

        patient = User(
            name=name,
            last_name=last_name,
            dob=dob,
            email=email,
            phone =phone,
            address = address,
            password=password
            )
        db.session.add(patient)
        try:
            db.session.commit()
            flash("User added successfully!", "success")
            return redirect(home_url)  
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating doctor: {e}", "danger")
            return redirect(add_url)

       
    patient_form = {
        "action": add_url,
        "method": "POST",
        "fields": [
            {"label": "First Name", "name": "first_name", "type": "text",
            "required": True, "value": field_value(patient, "name")},

            {"label": "Last Name", "name": "last_name", "type": "text",
            "value": field_value(patient, "last_name")},

            {"label": "Date of Birth", "name": "dob", "type": "date",
            "required": False, "value":field_value(patient, "dob")},

            {"label": "Email", "name": "email", "type": "email",
            "required": True, "value":field_value(patient, "email")},

            {"label": "Phone", "name": "phone", "type": "text",
            "value":field_value(patient, "phone")},

            {"label": "Address", "name": "address", "type": "textarea",
            "value":field_value(patient, "address")},
            
            {"label": "Password", "name": "password", "type": "text",
            "required": False, "value":""},
        ],

        "other_buttons" :[{"label" :"Back" ,"url": home_url}],
        "submit_label": "Register"
    }
    
    return render_template("form_base.html", form = patient_form ,title = "Add New User")



@app.route("/admin/edit_patient/<int:patient_id>", methods=["GET", "POST"])
@role_required("admin", "patient")
def edit_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    edit_url = url_for("edit_patient",patient_id=patient_id)
    home_url =get_home_url()
    if request.method == "POST":
        name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        dob_str = request.form.get("dob")
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
                return redirect(edit_url)
        else:
            dob = None
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        password = request.form.get("password")

        if not name or not password:
            flash("name and password are required.", "danger")
            return redirect(edit_url)
        if (get_userID_fromEmail(email) != patient_id):
            flash("That  eEmail is in use.", "danger")
            return redirect(edit_url)
        patient.name = name
        patient.last_name = last_name
        patient.email = email
        patient.phone = phone
        patient.address = address
        patient.dob = dob


        if password:  # only update password if user entered a new one
            patient.set_password(password)

        try:
            db.session.commit()
            flash("patient updated successfully.", "success")
            return redirect(home_url)  
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating patient: {e}", "danger")
            return redirect(edit_url)
        
    patient_form = {
        "action": edit_url,
        "method": "POST",
        "fields": [
            {"label": "First Name", "name": "first_name", "type": "text",
            "required": True, "value": field_value(patient, "name")},

            {"label": "Last Name", "name": "last_name", "type": "text",
            "value": field_value(patient, "last_name")},

            {"label": "Date of Birth", "name": "dob", "type": "date",
            "required": False, "value":field_value(patient, "dob")},

            {"label": "Email", "name": "email", "type": "email",
            "required": True, "value":field_value(patient, "email")},

            {"label": "Phone", "name": "phone", "type": "text",
            "value":field_value(patient, "phone")},

            {"label": "Address", "name": "address", "type": "textarea",
            "value":field_value(patient, "address")},
            
            {"label": "Password", "name": "password", "type": "text",
            "required": False, "value":""},
        ],

        "other_buttons" :[{"label" :"Back" ,"url": home_url}],
        "submit_label": "Update patient"
    }
    

    # GET request – render the edit form
    return render_template("form_base.html", form = patient_form ,title = "Edit patient")


@app.route("/admin/delete_patient/<int:patient_id>", methods=["GET", "POST"])
@admin_required
def delete_patient(patient_id):
    return "todo"

@app.route("/admin/blacklist_patient/<int:patient_id>", methods=["GET", "POST"])
@admin_required
def blacklist_patient(patient_id):
    return "todo"


@app.route("/admin/edit_appointmen/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "appointmen")
def edit_appointment(appointment_id):
    return "todo"
    

@app.route("/admin/delete_appointmen/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "appointmen")
def delete_appointment(appointment_id):
    return "todo"

@app.route("/patient/dashboard")
@patient_required
def patient_dashboard():
    patient=  current_user
    appointments = patient.appointments
    departments = Department.query.all()
    treatments = [a.treatment for a in appointments or [] if a and a.treatment]

    # return render_template("patient_dashboard.html", patient=patient, appointments=appointments,\
    #                         treatments=treatments,departments=departments)
    appt_rows = []
    for a in appointments:
        appt_rows.append({
            "ID": a.id,
            "Doctor": a.doctor.name,
            "Date": a.slot.date.strftime("%Y-%m-%d"),
            "Time": a.slot.session,
            "Status": a.status,
        })
    treat_rows=[]
    for t in treatments:
        treat_rows.append({
            "ID":t.id,
            "Date":t.appointment.slot.date,
            "Doctor":t.appointment.doctor.name,
            "Prescription":t.prescription,
        })
    department_rows = []
    for d in departments:
        department_rows.append({
            "Departments":d.name,
            "Description":d.description,
            "Action":[
                {"label": "View", "url": url_for("department_details", dept_id=d.id), "color": "warning"},
            ]
        })
    tabs = [
        {"label": "My Appointments", "columns": ["ID", "Doctor", "Date", "Time", "Status"], "rows": appt_rows},
        {"label": "My Treatments", "columns": ["ID", "Date", "Doctor", "Prescription"],"rows": treat_rows},
        {"label": "Departments", "columns":["Departments", "Action"],"rows": department_rows},
    ]

    return render_template("dashboard_base.html", title="Patient Dashboard", tabs=tabs)


@app.route("/patient/history/<int:patient_id>")
@doctor_required
def patient_history(patient_id):
    # pagination settings
    page = request.args.get("page", 1, type=int)
    per_page = 10   # visits per page

    # Fetch from DB (example, replace with ORM query)
    patient = Patient.query.get_or_404(patient_id)
    treatments = [
        appt.treatment
        for appt in patient.appointments
        if appt.treatment is not None
    ]
    for t in treatments:
        print (t)
    all_visits = []
    for tr in treatments:
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


@app.route("/doctor/dashboard")
@doctor_required
def doctor_dashboard():
    doctor  = current_user
    appointments = doctor.appointments
    patients = {appt.patient for appt in appointments if appt.patient is not None}  # unique patients
    #print (patients)
    #return render_template("doctor_dashboard.html", doctor=doctor, appointments=appointments, patients=patients)
    appt_rows = []
    for a in appointments :
        if a is not None:
            appt_rows.append({
                "ID": a.id,
                "Patient": a.patient.name if a.patient is not None else "",
                "Date": a.slot.date.strftime("%Y-%m-%d"),
                "Time": a.slot.session,
                "Status": a.status,
                "Reason": a.reason or "—",
                "Actions": [
                    {"label": "Update", "url": url_for("update_appointment",  appt_id=a.id), "color": "info"},
                    {"label": "Close", "url": url_for("close_appointment",  appt_id=a.id), "color": "success"},
                    {"label": "Cancel", "url": url_for("cancel_appointment",  appt_id=a.id), "color": "danger"},
                ],
            }) #"showUpdateForm(`{{ appt.id }}`, '{{ appt.patient.name }}', '{{ doctor.department.name  }}')"
    patient_rows = []
    if doctor.appointments is not None:
        for a in doctor.appointments:
            if a.patient is not None:
                patient_rows.append({"ID": a.patient.id, "Patient": a.patient.name, "Status": a.status,
                                     "Actions": [
                    {"label": "View", "url": url_for("patient_history",  patient_id=a.patient.id), "color": "info"},
                    # {"label": "Close", "url": url_for("close_appointment",  appt_id=a.id), "color": "success"},
                    # {"label": "Cancel", "url": url_for("cancel_appointment",  appt_id=a.id), "color": "danger"},
                ],} )
  
    appointments_rows = get_appointment_rows(doc_id=doctor.id)
    tabs = [
        {"label": "My Appointments", "columns": ["ID", "Patient", "Date", "Time", "Status", "Reason", "Actions"], "rows": appt_rows},
        {"label": "My Patients", "columns": ["ID", "Patient", "Status","Actions"], "rows": patient_rows},
        {"label": "Appointments", "columns": ["ID", "Date","Department","Doctor","Patient","Actions"], "rows": appointments_rows},
    ]

    return render_template("dashboard_base.html", title="", tabs=tabs)



if __name__ == "__main__":
    app.run(debug=True)