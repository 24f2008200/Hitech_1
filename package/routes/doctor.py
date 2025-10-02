# utils/doctor.py
import calendar
from flask import Blueprint, render_template, request, abort, url_for
from flask_login import current_user , LoginManager
from models import *
from package.routes.auth import *
from package.routes.utils import *

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")

@doctor_bp.route("/edit/<int:doctor_id>", methods=["GET", "POST"])
@role_required("admin", "doctor")
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    edit_url = url_for("doctor.edit_doctor",doctor_id=doctor_id)
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

@doctor_bp.route("/dashboard", methods=["GET"])
@doctor_required
def doctor_dashboard():
    doctor  = current_user
    appointments = doctor.appointments
    patients = {appt.patient for appt in appointments if appt.patient is not None}  # unique patients
    #print (patients)
    #return render_template("doctor_dashboard.html", doctor=doctor, appointments=appointments, patients=patients)
    # appt_rows = []
    # for a in appointments :
    #     if a is not None:
    #         appt_rows.append({
    #             "ID": a.id,
    #             "Patient": a.patient.name +" " +a.patient.last_name if a.patient is not None else "",
    #             "Date": a.slot.date.strftime("%Y-%m-%d"),
    #             "Time": a.slot.session,
    #             "Status": a.status,
    #             "Reason": a.reason or "—",
    #             "Actions": [
    #                 {"label": "Update", "url": url_for("doctor.update_appointment",  appointment_id=a.id), "color": "info"},
    #                 {"label": "Close", "url": url_for("doctor.close_appointment",  appointment_id=a.id), "color": "success"},
    #                 {"label": "Cancel", "url": url_for("doctor.cancel_appointment",  appointment_id=a.id), "color": "danger"},
    #             ],
    #         }) #"showUpdateForm(`{{ appt.id }}`, '{{ appt.patient.name }}', '{{ doctor.department.name  }}')"
    patient_rows = []
    if doctor.appointments is not None:
        for a in doctor.appointments:
            if a.patient is not None:
                patient_rows.append({"ID": a.patient.id, "Patient": a.patient.name +" " +a.patient.last_name, "Status": a.status,
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
        {"label": "My Appointments", "columns": ["ID", "Patient", "Date", "Time", "Status", "Reason", "Actions"], "rows": appointments_rows},
        {"label": "My Patients", "columns": ["ID", "Patient", "Status","Actions"], "rows": patient_rows},
        {"label": "Appointments", "columns": ["ID", "Date","Department","Doctor","Patient","Actions"], "rows": appointments_rows},
                {"label": "Search", "page" : "dummy1.html" ,"rows":["One","two"], "extra":["OK"]},
        {"label": "ToDo", "page" : "dummy1.html" ,"rows":["Doctor’s dashboard must display upcoming appointments for the day/week.","Doctor’s dashboard must show list of patients assigned to the doctor.",
                                                          "Doctor's dashboard must have the option to mark appointments as Completed or Cancelled.",
                                                          "Doctors can provide their availability for the next 7 days.",
                                                          "Doctors can update patient treatment history like provide diagnosis, treatment and prescriptions.",],
                                                            "extra":["OK"]},
    ]

    return render_template("dashboard_base.html", title="", tabs=tabs)



@doctor_bp.route("/availability") # by doc
@doctor_required
def availability():
    # doctor_id = current_user.id
    # start = date.today()
    # days = [start + timedelta(days=i) for i in range(90)]

    # # Fetch existing availability from DB
    # avail_records = Slot.query.filter(
    #     Slot.doctor_id == doctor_id,
    #     Slot.date.between(start, days[-1]),
    #     Slot.available == True
    # ).all()

    # # Map: {date: {session: available}}
    # slots = {d.isoformat(): {"morning": False, "afternoon": False, "evening": False}
    #          for d in days}

    # for rec in avail_records:
    #     slots[rec.date.isoformat()][rec.session] = rec.available
    #     print(rec)

    # return render_template("availability.html", days=days, slots=slots, doctor_id=doctor_id)
    doctor_id = current_user.id
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

    # Create Treatment entry linked to appointment
    appointment = Appointment.query.get_or_404(appointment_id)
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
    return redirect(url_for("doctor.doctor_dashboard"))


@doctor_bp.route("/edit_availability", methods=["POST"])
@login_required
def edit_availability():
    if current_user.type != "doctor":
        return "Forbidden", 403

    data = request.get_json()
    doctor_id = current_user.id
    edit_url = url_for("doctor.edit_availability")
    home_url =get_home_url()
    slots = data.get("slots", [])  # e.g., ["2025-01-21-morning-1", "2025-01-22-evening-0"]

    for slot in slots:
        date_str = slot["date"]
        session = slot["session"]
        flag = slot["available"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        is_avail = flag == True
        record = Slot.query.filter_by(doctor_id=doctor_id, date=date_obj, session=session).first()
        if record:
            if record.available != is_avail:
                print ("Old    ",date_str, record.available ,is_avail)
            if is_avail :
                record.open()
            else:
                if record.is_free:
                    record.block()
                else:
                    print ("can not block    ",date_str, record.available ,is_avail)
        # else:
        #     flash(f"Error updating Slot: {date_str +" " + session}  ", "danger")
        #     return redirect(edit_url)
    try:
        db.session.commit()
        flash("✅ Department added successfully!", "success")
        return redirect(home_url)
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating Department: {e}", "danger")
        return redirect(edit_url)

    # return jsonify({"status": "success", "message": "Slot saved successfully"})


@doctor_bp.route("/availability/<int:doctor_id>") # by patient
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
        availabilities = Slot.query.filter(
            Slot.doctor_id == doctor_id,
            Slot.date >= month_start,
            Slot.date <= month_end
        ).all()

        free_slots = [s for s in availabilities if s.is_free]

        avail_map = {(a.date, a.session): a for a in free_slots}
        months.append((month_start, weeks, avail_map))
  

    return render_template("booking.html", doctor=doctor, months=months,Sessions=Sessions)

@doctor_bp.route("/doctor_details/<int:doctor_id>")
@login_required
def doctor_details(doctor_id):
    return "ToDO"



@doctor_bp.route("/update_appointment/<int:appointment_id>")
@doctor_required
def update_appointment(appointment_id):
    return "todo"

@doctor_bp.route("/close_appointment/<int:appointment_id>")
@doctor_required
def close_appointment(appointment_id):
    return "todo"

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
    return redirect(url_for("doctor.doctor_dashboard", doctor_id=appt.slot.doctor_id))



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

    return redirect(url_for("doctor.doctor_dashboard", doctor_id=slot.doctor_id))

