from flask import Blueprint, render_template, request, abort, url_for
from flask_login import current_user
from models import Doctor
from package.routes.auth import *
from package.routes.utils import *

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")



@patient_bp.route("/register", methods=["GET", "POST"])
def register():
    patient = None
    add_url = url_for("patient.register")
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




@patient_bp.route("/edit_appointmen/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "patient")
def edit_appointment(appointment_id):
    return "todo"
    


@patient_bp.route("/delete_appointmen/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "patient")
def delete_appointment(appointment_id):
    return "todo"


@patient_bp.route("/dashboard", methods=["GET", "POST"])
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
                {"label": "View", "url": url_for("admin.department_details", dept_id=d.id), "color": "warning"},
            ]
        })
    tabs = [
        {"label": "My Appointments", "columns": ["ID", "Doctor", "Date", "Time", "Status"], "rows": appt_rows},
        {"label": "My Treatments", "columns": ["ID", "Date", "Doctor", "Prescription"],"rows": treat_rows},
        {"label": "Departments", "columns":["Departments", "Action"],"rows": department_rows},
    ]

    return render_template("dashboard_base.html", title="Patient Dashboard", tabs=tabs)


@patient_bp.route("/history/<int:patient_id>", methods=["GET"])
@role_required("admin", "patient","doctor")
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
                           return_address =  url_for('doctor.doctor_dashboard')
                           )



@patient_bp.route("/<int:doctor_id>/book", methods=["POST"])
@login_required
def appointments_book(doctor_id):
    date_str = request.form.get("date")
    session = request.form.get("session")
    patient_id = current_user.id

    if not date_str or not session:
        flash("Please select a slot before booking.", "danger")
        return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))

    # convert date string to date
    selected_date = datetime.fromisoformat(date_str).date()

    # find availability
    avail = Availability.query.filter_by(
        doctor_id=doctor_id, date=selected_date, session=session
    ).first()

    if not avail or not avail.available:
        flash("Selected slot is not available.", "danger")
        return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))

    if avail.is_busy:
        flash("This slot has already been booked by another patient.", "danger")
        return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))
    date = selected_date
    time = datetime.fromisoformat(date_str).time()
    status = AppointmentStatus.BOOKED
    reason = "Test"
    availability_id = db.Column(db.Integer, db.ForeignKey("availability.id"), nullable=False)
    avail.available = False

    # create appointment
    appt = Appointment(patient_id=patient_id, doctor_id=doctor_id, slot=avail , status=status)
    db.session.add(appt)
    db.session.commit()
    

    flash("Appointment booked successfully!", "success")
    return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))



@patient_bp.route("/update_slot/<int:doctor_id>", methods=["POST"])
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



@patient_bp.route("/appointments/book/<int:slot_id>", methods=["POST"])
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



@patient_bp.route("/appointments/<int:appt_id>/cancel", methods=["POST"])
def cancel(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    try:
        appt.cancel()
        db.session.commit()
        flash("Appointment cancelled and slot freed.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("doctor.doctor_dashboard", doctor_id=appt.slot.doctor_id))


