# utils/doctor.py
import calendar
from flask import Blueprint, render_template, request, abort, url_for
from flask_login import current_user , LoginManager
from package.routes import doctor
from models import *
from package.routes.auth import *
from package.routes.utils import *

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")

@doctor_bp.route("/edit/<int:doctor_id>", methods=["GET", "POST"])
@role_required("admin", "doctor")
def edit_doctor(doctor_id):
    doctor = Doctor.query.filter(
        Doctor.id == doctor_id,
        Doctor.status != "deleted"
        ).first_or_404()
    edit_url = url_for("doctor.edit_doctor",doctor_id=doctor_id)
    if current_user.role == "doctor" and current_user.id != doctor_id:
        tab_id =1
    else:
        tab_id = 2
    home_url = get_home_url(tab_id=tab_id)
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
        status = request.form.get("status") if current_user.role == "admin" else None

        if not name or not dept_id:
            flash("name and specialization are required.", "danger")
            return redirect(url_for("doctor.edit_doctor", doctor_id=doctor_id))
        if (get_userID_fromEmail(email) != doctor_id):
            flash("That  eEmail is in use.", "danger")
            return redirect(url_for("doctor.edit_doctor", doctor_id=doctor_id))
        doctor.name = name
        doctor.last_name = last_name
        doctor.dob=dob
        doctor.email = email
        doctor.phone = phone
        doctor.address = address
        doctor.license_number = license_number
        doctor.experience = experience
        doctor.department_id = dept_id
        if status:
            doctor.status = status

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
    if current_user.role == "admin":
        doctor_form["fields"].insert(3,  # Insert after last_name
            {"label": "Status", "name": "status", "type": "select",
             "options": [("active", "Active"), ("inactive", "Inactive"), ("blacklisted", "Blacklisted")],
             "required": True, "value": field_value(doctor, "status")})
    

    # GET request – render the edit form
    return render_template("form_base.html", form = doctor_form ,title = "Edit Doctor")

@doctor_bp.route("/dashboard/<int:tab_id>", methods=["GET"])
@doctor_required
def doctor_dashboard(tab_id=1):
    doctor  = current_user
    appointments = sorted(doctor.appointments, key=lambda a: a.slot.date)
    patients = [] # unique patients
    patient_rows = []
    if appointments is not None:
        for a in appointments:
            if a.patient is not None and a.patient not in patients:
                patients.append(a.patient)
                patient_rows.append({"ID": a.patient.id, 
                                     "Patient": a.patient.name +" " +a.patient.last_name, 
                                     "Date": a.slot.date.strftime("%Y-%m-%d") if a.slot else "N/A",
                                     "Session": a.slot.session if a.slot else "N/A",
                                     "Status": a.status.value,
                                     "Actions": [
                    {"label": "View", "url": url_for("patient.patient_history",  patient_id=a.patient.id), "color": "info"},
                    # {"label": "Close", "url": url_for("doctor.close_appointment",  appointment_id=a.id), "color": "success"},
                    # {"label": "Cancel", "url": url_for("doctor.cancel_appointment",  appointment_id=a.id), "color": "danger"},
                ],} )
    actions =[
                    {"label": "Update", "url":"doctor.update_appointment", "color": "info"},
                    {"label": "Close", "url": "doctor.close_appointment",  "color": "success"},
                    {"label": "Cancel", "url": "doctor.cancel_appointment", "color": "danger"},
                ]

    appointments_rows = get_appointment_rows(doc_id=doctor.id,active=True,actions=actions)
    tabs = [
        {"label": "Upcomming Appointments", "columns": ["ID", "Patient", "Date", "Session", "Reason", "Actions"], "rows": appointments_rows},
        {"label": "My Patients", "columns": ["ID", "Patient","Date","Session","Status","Actions"], "rows": patient_rows},
        {"label": "All Appointments", "columns": ["ID", "Date","Session","Patient", "Reason", "Status","Actions"], "rows": appointments_rows},
                {"label": "Search", "page" : "search_tab.html" ,"rows":["One","two"], "extra":["OK"]},
        {"label": "ToDo", "page" : "dummy2.html" ,"rows":["Doctor’s dashboard must display upcoming appointments for the day/week.","Doctor’s dashboard must show list of patients assigned to the doctor.",
                                                          "Doctor's dashboard must have the option to mark appointments as Completed or Cancelled.",
                                                          "Doctors can provide their availability for the next 7 days.",
                                                          "Doctors can update patient treatment history like provide diagnosis, treatment and prescriptions.",],
                                                            "extra":["OK"]},
    ]

    return render_template("dashboard_base.html", title="", tabs=tabs, active_index=tab_id)



@doctor_bp.route("/availability") # by doc
@doctor_required
def availability():
    doctor_id = current_user.id
    doctor = Doctor.query.filter(
        Doctor.id == doctor_id,
        Doctor.status != "deleted"
    ).first_or_404()
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
        availabilities = Slot.query.filter(
            Slot.doctor_id == doctor_id,
            Slot.date >= month_start,
            Slot.date <= month_end
        ).all()

        free_slots = [s for s in availabilities]
        

        avail_map = {(a.date, a.session): a for a in free_slots}
        months.append((month_start, weeks, avail_map))
  

    return render_template("availability.html", doctor=doctor, months=months,Sessions=Sessions)

@doctor_bp.route("/update_history", methods=["POST"])
@login_required
def update_history():
    if current_user.type != "doctor":
        return "Forbidden", 403

    appointment_id = request.form.get("appointment_id")
    visit_type = request.form.get("visit_type")
    test_done = request.form.get("test_done")
    diagnosis = request.form.get("diagnosis")
    prescription = request.form.get("prescription")
    medicines = request.form.get("medicines")
    notes = request.form.get("notes")
    consultation_fee = int(request.form.get("consultation_fee"))


    # Create Treatment entry linked to appointment
    appointment = Appointment.query.get_or_404(appointment_id)
    treatment = Treatment(
        appointment=appointment,
        diagnosis=diagnosis,
        prescription=prescription,
        visit_type =visit_type,
        tests=test_done,
        medicines= medicines,
        notes= notes,
        consultation_fee = consultation_fee
    )
    db.session.add(treatment)
    db.session.commit()

    flash("Patient history updated successfully", "success")
    return redirect(url_for("doctor.doctor_dashboard", tab_id=2))


@doctor_bp.route("/edit_availability", methods=["POST"])
@login_required
def edit_availability():
    if current_user.type != "doctor":
        return "Forbidden", 403

    data = request.get_json()
    doctor_id = current_user.id
    edit_url = url_for("doctor.edit_availability")
    home_url = get_home_url(tab_id=2)
    slots = data.get("slots", [])  # e.g., ["2025-01-21-morning-1", "2025-01-22-evening-0"]

    for slot in slots:
        date_str = slot["date"]
        session = slot["session"]
        flag = slot["available"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        is_avail = flag == True
        record = Slot.query.filter_by(doctor_id=doctor_id, date=date_obj, session=session).first()
        if record:
            if record.is_free and record.available != is_avail:
                record.available = is_avail
                db.session.flush()
    try:
        db.session.commit()
        flash("✅ Department added successfully!", "success")
        return redirect(home_url)
    except Exception as e:
        db.session.rollback()
        flash(f"Error Editing Availability: {e}", "danger")
        return redirect(edit_url)

    # return jsonify({"status": "success", "message": "Slot saved successfully"})


@doctor_bp.route("/availability/<int:doctor_id>") # by patient
@login_required
def doctor_availability(doctor_id):
    doctor = Doctor.query.filter(
        Doctor.id == doctor_id,
        Doctor.status != "deleted"
        ).first_or_404()
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
        availabilities = Slot.query.filter(
            Slot.doctor_id == doctor_id,
            Slot.date >= month_start,
            Slot.date <= month_end
        ).all()

        free_slots = [s for s in availabilities if s.available and s.is_free]

        avail_map = {(a.date, a.session): a for a in free_slots}
        months.append((month_start, weeks, avail_map))
  

    return render_template("booking.html", doctor=doctor, months=months,Sessions=Sessions)

@doctor_bp.route("/doctor_details/<int:doctor_id>")
@login_required
def doctor_details(doctor_id):
    return "ToDO"



@doctor_bp.route("/update_appointment/<int:appointment_id>",methods=["GET","POST"])
@doctor_required
def update_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient = appointment.patient
    edit_url = url_for("doctor.update_appointment", appointment_id=appointment_id)
    home_url = get_home_url(tab_id=1)
    treatment = appointment.treatment if appointment else None

    if request.method == "GET":
         treatment_form = {
        "action": edit_url,
        "method": "POST",
        "fields": [
            {"label": "Name", "name": "first_name", "type": "text",
            "noedit": True, "value": patient.name +" "+ patient.last_name if patient else ""},

            {"label": "Visit Type", "name": "visit_type", "type": "text",
            "value": field_value(treatment, "visit_type")},

            {"label": "Tests Done", "name": "test_done", "type": "text",
            "required": False, "value":field_value(treatment, "tests")},

            {"label": "Diagnosis", "name": "diagnosis", "type": "textarea",
            "required": True, "value":field_value(treatment, "diagnosis")},

            {"label": "Prescription", "name": "prescription", "type": "textarea",
            "value":field_value(treatment, "prescription")},

            {"label": "Medicines", "name": "medicines", "type": "textarea",
            "value":field_value(treatment, "medicines")},

            {"label": "Notes", "name": "notes", "type": "textarea",
            "value":field_value(treatment, "notes")},

            {"label": "consultation_fee", "name": "consultation_fee", "type": "number",
            "value":field_value(treatment, "consultation_fee")},
        ],

        "other_buttons" :[{"label" :"Back" ,"url": home_url}],
        "submit_label": "Update Appointment"
        }
         return render_template("form_base.html", form = treatment_form ,title = "Edit Appointment")
         
    elif request.method == "POST":
        appointment_id = request.form.get("appointment_id")

        visit_type = request.form.get("visit_type")
        test_done = request.form.get("test_done")
        diagnosis = request.form.get("diagnosis")
        prescription = request.form.get("prescription")
        medicines = request.form.get("medicines")   
        notes = request.form.get("notes")
        consultation_fee = int(request.form.get("consultation_fee"))


        if treatment:
            treatment.visit_type = visit_type
            treatment.tests = test_done
            treatment.diagnosis = diagnosis
            treatment.prescription = prescription
            treatment.medicines = medicines
            treatment.notes = notes
            treatment.consultation_fee=consultation_fee
            db.session.commit()
        else:
            treatment = Treatment(
                appointment=appointment,
                diagnosis=diagnosis,
                prescription=prescription,
                visit_type=visit_type,
                tests=test_done,
                medicines=medicines,
                notes=notes,
                consultation_fee=consultation_fee
            )
            db.session.add(treatment)
            db.session.commit()

    flash("Patient history updated successfully", "success")
    return redirect(url_for("doctor.doctor_dashboard", tab_id=1))

@doctor_bp.route("/close_appointment/<int:appointment_id>", methods=["GET", "POST"])
@doctor_required
def close_appointment(appointment_id):
    ap = Appointment.query.get_or_404(appointment_id)
    edit_url = url_for("doctor.close_appointment", appointment_id=appointment_id)
    home_url = get_home_url()
    if request.method == "POST":
        code = int(request.form.get("confirmation"))
        if code != appointment_id:
            return render_template('confirmation.html',
                                   message ="Do You want to Close this appointment",
                                   confirmation_code = appointment_id,
                                   button_msg = "Yes-Close",
                                   return_url = edit_url,
                                      cancel_url = home_url
                                   )
        
        try:
            t = ap.treatment
            ap.complete(t)
            db.session.commit()
            flash("✅ That  appoinment is Closed", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error Closing appointment: {e}", "danger")
            return redirect(home_url)

    return render_template('confirmation.html',
                                   message ="Do You want to Close this appointment",
                                   confirmation_code = appointment_id,
                                   button_msg = "Yes-Close",
                                   return_url = edit_url,
                                   cancel_url = home_url
                                   )


@doctor_bp.route("/cancel_appointment/<int:appointment_id>")
@doctor_required
def cancel_appointment(appointment_id):
    return "todo"


@doctor_bp.route("/appointments/<int:appointment_id>/complete", methods=["GET", "POST"])
def complete(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    try:
        treatment = appt.complete(treatment_data={"notes": "Treatment started"})
        db.session.commit()
        flash("Appointment completed. Treatment record created.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("doctor.doctor_dashboard", tab_id=1))



@doctor_bp.route("/availability/<int:slot_id>/block", methods=["GET", "POST"])
def block_slot(slot_id):
    slot = Slot.query.get_or_404(slot_id)
    reason = request.form.get("reason", "On leave")

    try:
        slot.block(reason=reason)
        db.session.commit()
        flash(f"Slot on {slot.date} ({slot.session}) blocked: {reason}", "info")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("doctor.doctor_dashboard", tab_id=1))

