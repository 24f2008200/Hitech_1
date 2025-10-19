from flask import Blueprint, render_template, request, abort, url_for
from flask_login import current_user
from models import *
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

        patient = Patient(
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
        "title": "Add New User",
        "fields": [
            {"label": "First Name", "name": "first_name", "type": "text",
            "required": True, "value": field_value(patient, "name")},

            {"label": "Last Name", "name": "last_name", "type": "text",
            "value": field_value(patient, "last_name")},

            {"label": "Date of Birth", "name": "dob", "type": "date",
            "required": False, "value":field_value(patient, "dob")},

            {"label": "Email", "name": "email", "type": "email",
            "required": True, "value":""},

            {"label": "Phone", "name": "phone", "type": "text",
            "value":field_value(patient, "phone")},

            {"label": "Address", "name": "address", "type": "textarea",
            "value":field_value(patient, "address")},
            
            {"label": "Password", "name": "password", "type": "password",
            "required": False, "value":""},
        ],

        "other_buttons" :[{"label" :"Back" ,"url": home_url}],
        "submit_label": "Register"
    }
    
    return render_template("form_base.html", form = patient_form ,title = "Add New User")




@patient_bp.route("/dashboard/<int:tab_id>", methods=["GET", "POST"])
@patient_required
def patient_dashboard(tab_id=1):
    patient=  current_user
    appointments = patient.appointments
    departments = Department.query.all()
    treatments = [a.treatment for a in appointments or [] if a and a.treatment]

    # return render_template("patient_dashboard.html", patient=patient, appointments=appointments,\
    #                         treatments=treatments,departments=departments)
    actions =[
                    # {"label": "Update", "url":"doctor.update_appointment", "color": "info"},
                    # {"label": "Close", "url": "doctor.close_appointment",  "color": "success"},
                    {"label": "Cancel", "url": "patient.delete_appointment", "color": "danger"},
                ]
    appt_rows = get_appointment_rows(pat_id=patient.id,actions=actions)
    appointments_cols = [
            {"key": "ID", "label": "ID"},
            {"key": "Doctor", "label": "Doctor"},
            {"key": "Date", "label": "Date"},
            {"key": "Session", "label": "Time"},
            {"key": "Department", "label": "Department"},
            {"key": "Status", "label": "Status", "filterType": "select"},
            {"key": "Actions", "label": "Actions", "type": "action"}]
    
    treat_rows = [t for t in appt_rows if t["Status"] == AppointmentStatus.COMPLETED.value]
    treat_rows.reverse()
    appt_rows_old = [t for t in appt_rows if not(t["Status"] == AppointmentStatus.BOOKED.value)]
    appt_rows_old.reverse()
    appt_rows = [t for t in appt_rows if t["Status"] == AppointmentStatus.BOOKED.value]
    alert_rows = get_alerts(pat_id=patient.id)
    alert_cols =[ {"key": "ID", "label": "ID"},
        {"key": "Patient", "label": "Patient"},
        {"key": "P Mobile", "label": "P Mobile", },
        {"key": "Doctor", "label": "Doctor", },
        {"key": "D Mobile", "label": "D Mobile"},
        {"key": "Message", "label": "Message", },
        {"key": "Time", "label": "actionTime", },
        {"key": "Actions", "label": "Actions", "type": "action"}
                ]
    department_rows = []
    for d in departments:
        department_rows.append({
            "Departments":d.name,
            "Description":d.description,
            "Action":[
                {"label": "View", "url": url_for("admin.department_details", dept_id=d.id), "color": "warning"},
            ]
        })
    doctors = Doctor.query.filter(Doctor.status != "deleted").all()
    doctors_rows = []
    for d in doctors:
        doctors_rows.append({
            "Doctors": d.name,
            "Departments": d.department.name if d.department else "N/A",
            "Speciality": d.speciality,
            "Experience": d.experience,
            "Action": [
                {"label": "View", "url": url_for("doctor.doctor_availability", doctor_id=d.id), "color": "warning"},
            ]
        })
    tabs = [
        {"label": "Open Appointments", "columns": ["ID", "Doctor", "Date", "Session", "Symptoms","Status","Actions"], "rows": appt_rows},
        {"label": "My Treatments", "filterTable": "treats","columns": ["ID", "Doctor", "Date", "Session", "Symptoms","Tests","Diagnosis",
                                               "Prescription","Medicines"],"rows": treat_rows},
        {"label": "Departments", "columns":["Departments", "Action"],"rows": department_rows},
        {"label": "Doctors", "columns":["Doctors","Departments", "Speciality", "Experience", "Action"],"rows": doctors_rows},
        {"label": "Other Appointments", "columns": ["ID", "Doctor", "Date", "Session", "Symptoms","Status",], "rows": appt_rows_old},
        {"label": "Alerts", "filterTable": "alerts", "columns": alert_cols, "rows": alert_rows},
        {"label": "Search", "page" : "search_tab.html" ,"rows":["One","two"], "extra":["OK"]},
        {"label": "ToDo", "page" : "dummy2.html" ,"rows":["Patients can register and login themselves on the app.",
                                                          "Patients’ Dashboard must display all available specialization/departments",
                                                          "Patients’ Dashboard must display availability of doctors for the coming 7 days (1 week) and patients can read doctors profiles.",
                                                          "It must display upcoming appointments and their status.","It must show past appointment history with diagnosis and prescriptions.",
                                                          "Patients can edit their profile.","Patients can book as well as cancel appointments with doctors.",],
                                                            "extra":["OK"]},
    ]

    return render_template("dashboard_base.html", title="Patient Dashboard", tabs=tabs, active_index=tab_id)



@patient_bp.route("/appointments_book/<int:doctor_id>", methods=["POST"])
@login_required
def appointments_book(doctor_id):
    date_str = request.form.get("date")
    session = request.form.get("session")
    patient_id = current_user.id
    add_url = url_for("doctor.doctor_availability", doctor_id=doctor_id)
    home_url =get_home_url()

    if not date_str or not session:
        flash("Please select a slot before booking.", "danger")
        return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))

    # convert date string to date
    selected_date = datetime.fromisoformat(date_str).date()

    # find availability
    spot = Slot.query.filter_by(
        doctor_id=doctor_id, date=selected_date, session=session
    ).first()
    print(spot)
    if not spot or not spot.available:
        flash("Selected slot is not available.", "danger")
        return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))

    if spot.is_busy:
        flash("This slot has already been booked by another patient.", "danger")
        return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))


    try:
        appt =spot.book(patient_id)
        db.session.commit()
        flash("Appointment booked successfully!", "success")
        return redirect(url_for("doctor.doctor_availability", doctor_id=doctor_id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error Booking Appointment: {e}", "danger")
        return redirect(add_url)

    
@patient_bp.route("/delete_appointmen/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "patient")
def delete_appointment(appointment_id):
    ap = Appointment.query.get_or_404(appointment_id)
    edit_url = url_for("patient.delete_appointment",appointment_id=appointment_id)
    if current_user.role == "patient":
        tab_id = 1
    else:
        tab_id = 5
    home_url = get_home_url(tab_id=tab_id)
    if request.method == "POST":
        code = int(request.form.get("confirmation"))
        if code !=appointment_id:
            return render_template('confirmation.html',
                                   message ="Do You want to cancel this appointment", 
                                   confirmation_code = appointment_id,
                                   button_msg = "Yes-Delete",
                                   return_url = edit_url
                                   )
        
        try:
            ap.cancel()
            db.session.commit()
            flash(" That  appoinment is cancelled", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error cancelling appointment: {e}", "danger")
            return redirect(home_url)

    return render_template('confirmation.html',
                                   message ="Do You want to cancel this appointment",
                                   confirmation_code = appointment_id,
                                   button_msg = "Yes-Delete",
                                   return_url = edit_url,
                                   cancel_url = home_url
                                   )

@patient_bp.route("/history/<int:patient_id>", methods=["GET"])
@role_required("admin", "patient","doctor")
def patient_history(patient_id):

    actions =[
                    # {"label": "Update", "url":"doctor.update_appointment", "color": "info"},
                    # {"label": "Close", "url": "doctor.close_appointment",  "color": "success"},
                    {"label": "Cancel", "url": "patient.delete_appointment", "color": "danger"},
                ]

    appt_rows = get_appointment_rows(pat_id = patient_id,actions=actions)
    
    treat_rows = [t for t in appt_rows if t["Status"] == AppointmentStatus.COMPLETED.value]
    treat_rows.reverse()
    p = Patient.query.get_or_404(patient_id)
    title = p.name + " " + p.last_name + "'s Treatments"

    tabs = [{"label": title, "filterTable": "treats","back_url":'', "columns": ["ID", "Doctor", "Date", "Session", "Symptoms","Tests","Diagnosis",
                                               "Prescription","Medicines"],"rows": treat_rows},
            # {"label": title,  "columns": ["ID", "Doctor", "Date", "Session", "Symptoms","Tests","Diagnosis",
            #                                    "Prescription","Medicines"],"rows": treat_rows}
                                               ]
    role = current_user.role
    tab_id = 3 if role == 'admin' else 2 if role =='doctor' else 2
    return render_template("dashboard_base.html", title="Patient Dashboard", tabs=tabs, active_index=1)



@patient_bp.route("/history2/<int:patient_id>", methods=["GET"])
@role_required("admin", "patient","doctor")
def patient_history2(patient_id):
    # pagination settings
    page = request.args.get("page", 1, type=int)
    per_page = 10   # visits per page

    # Fetch from DB (example, replace with ORM query)
    patient = Patient.query.filter(
                Patient.id == patient_id,
                Patient.status != "deleted"
            ).first()
    treatments = [
        appt.treatment
        for appt in patient.appointments
        if appt.treatment is not None
    ]

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
    role = current_user.role
    tab_id = 3 if role == 'admin' else 2 if role =='doctor' else 2


    return render_template("patient_history.html",
                           patient=patient,
                           doctor=doctor,
                           visits=visits,
                           page=page,
                           total_pages=total_pages,
                           patient_id=patient_id,
                           return_address =  get_home_url(tab_id= tab_id)
                           )



@patient_bp.route("/edit_appointmen/<int:appointment_id>", methods=["GET", "POST"])
@role_required("admin", "patient")
def edit_appointment(appointment_id):
    ap = Appointment.query.get_or_404(appointment_id)
    edit_url = url_for("patient.edit_appointment",appointment_id=appointment_id)
    if current_user.role == "patient":
        tab_id = 1
    else:
        tab_id = 5
    home_url = get_home_url(tab_id=tab_id)
    if request.method == "POST":
        flash("Editing appointment is not allowed. Please cancel and rebook.", "danger")
        return redirect(home_url)

    appointment_form = {
        "action": url_for("patient.edit_appointment", appointment_id=appointment_id)    ,
        "method": "POST",
        "fields": [
            {"label": "Patient Name", "name": "first_name", "type": "text",
            "required": False, "value": ap.patient.name},

            {"label": "Doctor's Name", "name": "last_name", "type": "text",
            "value": ap.doctor.name},

            {"label": "Date of Appointment", "name": "dob", "type": "date",
            "required": False, "value":ap.slot.date},

            {"label": "Session", "name": "email", "type": "text",
            "required": False, "value":ap.slot.session},

            {"label": "Tests", "name": "phone", "type": "text",
            "value":ap.treatment.tests if ap.treatment else ""},
            
            {"label": "Diagnosis", "name": "phone", "type": "text",
            "value":ap.treatment.diagnosis if ap.treatment else ""},

            {"label": "Prescription", "name": "phone", "type": "text",
            "value":ap.treatment.prescription if ap.treatment else ""},
            
          
            {"label": "Medicines", "name": "phone", "type": "text",
            "value":ap.treatment.medicines if ap.treatment else ""},
        ],

        "other_buttons" :[{"label" :"Delete" ,"url": url_for('patient.delete_appointment',
                              appointment_id=appointment_id)},
                              {"label" :"Back" ,"url":home_url}
                              ],

        "submit_label": "Edit appointment"
    }
    

    # GET request – render the edit form
    return render_template("form_base.html", form = appointment_form ,title = "Edit appointment")


    

@patient_bp.route("/update_slot/<int:doctor_id>", methods=["POST"])
@doctor_required
def update_slot(doctor_id):
    data = request.get_json()
    date_str = data["date"]
    session = data["session"]
    available = data["available"]

    rec = Slot.query.filter_by(
        doctor_id=doctor_id, date=date.fromisoformat(date_str), session=session
    ).first()

    if not rec:
        rec = Slot(
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



# @patient_bp.route("/appointments/book/<int:slot_id>", methods=["POST"])
# def book(slot_id):
#     slot = Slot.query.get_or_404(slot_id)
#     patient_id = request.form["patient_id"]
#     reason = request.form.get("reason")

#     try:
#         appt = slot.book(patient_id=patient_id, reason=reason)
#         db.session.commit()
#         flash("Appointment booked!", "success")
#     except ValueError as e:
#         flash(str(e), "danger")
#     return redirect(url_for("appointments.check_availability", doctor_id=slot.doctor_id))


