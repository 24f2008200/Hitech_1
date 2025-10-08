from flask import Blueprint, render_template, request, abort,Flask, render_template, redirect, url_for, request ,send_from_directory, flash
from flask_login import current_user ,LoginManager
from sqlalchemy import or_

from package.routes.auth import *
from package.routes.utils import *
from models import *


login_manager = LoginManager()  
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# @admin_bp.route("/dashboard", methods=["GET", "POST"])
@admin_bp.route("/dashboard/<int:tab_id>", methods=["GET", "POST"])
@admin_required
def admin_dashboard(tab_id):
    doctors = Doctor.query.filter(Doctor.status != "deleted").all()
    doctor_rows = []
    for d in doctors:
        doctor_rows.append({
            "ID": d.id,
            "Name": d.name +" "+d.last_name,
            "Department": d.department.name if d.department else "—",
            "Open": db.session.query(Appointment).filter(
                        Appointment.doctor_id == d.id,
                        Appointment.status == AppointmentStatus.BOOKED
                    ).count(),
            "Closed":db.session.query(Appointment).filter(
                        Appointment.doctor_id == d.id,
                        Appointment.status == AppointmentStatus.COMPLETED
                    ).count(),
            "Available":db.session.query(Slot).filter(
                        Slot.doctor_id == d.id,
                        Slot.is_free == True
                    ).count(),
            "Status": d.status,
            "Actions": [
                {"label": "Edit", "url": url_for("doctor.edit_doctor", doctor_id=d.id), "color": "warning"},
                {"label": "Delete", "url": url_for("admin.delete_doctor", doctor_id=d.id), "color": "danger"},
                {"label": "Blacklist", "url": url_for("admin.blacklist_doctor", doctor_id=d.id), "color": "dark"},
            ],
        })
    doctor_cols =["ID", "Name", "Department", "Open","Closed","Available","Status", "Actions"]
    patients = Patient.query.filter(Patient.status != "deleted").all()
    patient_rows = [{
        "ID": p.id, 
        "Name": p.name + " " + p.last_name, 
        "Phone": p.phone,
        "Email": p.email,
        "Status": p.status,
         "Actions": [
                {"label": "Edit", "url": url_for("admin.edit_patient", patient_id=p.id), "color": "warning"},
                {"label": "Delete", "url": url_for("admin.delete_patient", patient_id=p.id), "color": "danger"},
                {"label": "Blacklist", "url": url_for("admin.blacklist_patient", patient_id=p.id), "color": "dark"},
            ],

        } 
        for p in patients]
    
    patient_columns =[ {"key": "ID", "label": "ID"},
        {"key": "Name", "label": "Full Name"},
        {"key": "Phone", "label": "Phone", },
        {"key": "Email", "label": "Email", },
        {"key": "Status", "label": "Status", "filterType": "select"},
        {"key": "Actions", "label": "Actions", "type": "action"}
                ]
    appointments_cols = [
        {"key": "ID", "label": "ID"},
        {"key": "Doctor", "label": "Doctor"},
        {"key": "Patient", "label": "Patient"},
        {"key": "Date", "label": "Date"},
        {"key": "Session", "label": "Session"},
        {"key": "Department", "label": "Department"},
        {"key": "Status", "label": "Status"},
        {"key": "Actions", "label": "Actions", "type": "action"}
    ]

    departments = Department.query.all()
    department_rows = [{
        "Name": d.name , 
        "Description": d.description, 
        "Doctors": ", ".join([ doc.name for doc in d.doctors  ]) ,
        "Actions": [
                {"label": "Edit", "url": url_for("admin.edit_department", department_id=d.id), "color": "warning"},
                {"label": "Delete", "url": url_for("admin.delete_department", department_id=d.id), "color": "danger"},
            ],
        }
          for d in departments ] 
    department_cols =["Name", "Description","Doctors","Actions"]
    appointments_rows = get_appointment_rows()

    total_doctors = db.session.query(Doctor).count()
    total_patients = db.session.query(Patient).count()
    total_appointments = db.session.query(Appointment).count()

    active_appointments = db.session.query(Appointment).filter_by(
        status=AppointmentStatus.BOOKED
    ).count()

    closed_appointments = db.session.query(Appointment).filter_by(
        status=AppointmentStatus.COMPLETED
    ).count()

    dummy2_rows =["Admin dashboard must display total number of doctors, patients, and appointments.",
                "Admin should pre-exist in the app i.e. it must be created programmatically after the creation of the database. [No admin registration allowed]",
                "Admin can add/update doctor and patient profiles.",
                "Admin can view all upcoming and past appointments.",
                "Admin can search for patients or doctors and view their details.",
                "Admin can edit doctor details such as name, specialization etc., and also patient info if needed.",
                "Admin can remove/blacklist doctors and patients from the system.",
                "API resources are created to interact with the users, appointments etc. (Please note: you can choose which API resources to make from the given ones, It is NOT mandatory to create API resources for CRUD of all the components)",
                "APIs can either be created by returning JSON from a controller (with at least 4 http methods) or using a flask extension like flask_restful",
                "External APIs/libraries for creating charts, e.g. Chart JS",
                "Implementing frontend validation on all the form fields using HTML5 form validation or JavaScript",
                "Implement backend validation within your app's controllers.",
                "Provide styling and aesthetics to your application by creating a beautiful and responsive front end using simple CSS or Bootstrap (No other styling library is allowed.)",
                "Incorporate a proper login system to prevent unauthorized access to the app using Flask extensions like flask_login, flask_security etc.",
                "Any additional feature you feel is appropriate for the application"]
                

    tabs = [
        
        {"label": "Summary", "page" : "summary.html" ,"rows": {"total_doctors":total_doctors, "total_patients":total_patients,
                "total_appointments":total_appointments,"active_appointments":active_appointments,
                "closed_appointments":closed_appointments}},
        {"label": "Doctors", "columns": doctor_cols, "rows": doctor_rows},
        {"label": "Patients", "filterTable": "patients", "columns": patient_columns, "rows": patient_rows},
        {"label": "Departments", "columns": department_cols, "rows": department_rows},
        {"label": "Appointments", "filterTable": "appointments", "columns": appointments_cols, "rows": appointments_rows},
        {"label": "Search", "page" : "search_tab.html" ,"rows":["One","two"], "extra":["OK"]},
        {"label": "Develop", "page" : "dummy1.html" ,"rows":["One","two"], "extra":["OK"]},
        {"label": "ToDo", "page" : "dummy2.html" ,"rows":dummy2_rows,"extra":["OK"]},
    ]
    

    return render_template("dashboard_base.html", title=None, tabs=tabs, active_index=tab_id)
    # return render_template("dashboard_base.html", title=None, tabs=tabs,active_tab="availablilty")

@admin_bp.route("/query", methods=["GET", "POST"])
@login_required
def search():
    wheretosearch = request.form["fromWhere"]
    feature = request.form["field"]
    value = request.form["q"]
    results, searchResults_columns = search_records(wheretosearch, feature, value)
    return render_template("search.html", title="Search Results", 
                           searchResults_columns=searchResults_columns, 
                           searchResults_rows=results)


    return fromWhere + " " + field + " " + query

@admin_bp.route("/add_department", methods=["GET", "POST"])
@admin_required
def add_department():
    department = None
    add_url = url_for("admin.add_department")
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
            flash(f"Error Adding Department: {e}", "danger")
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


@admin_bp.route("/department_details/<int:dept_id>", methods=["GET"])
@login_required
def department_details(dept_id):

    department = Department.query.get_or_404(dept_id)
    doctors = Doctor.query.filter_by(department_id=dept_id).all()

    doctor_rows = [{
        "ID": d.id, 
        "Name": d.name,
        "Specialization": d.department.name if d.department else "—",
        "Experience": d.experience,
        "Actions": [
            {"label": "View", "url": url_for("admin.doctor_details", doctor_id=d.id), "color": "info"},
            {"label": "Edit", "url": url_for("admin.edit_doctor", doctor_id=d.id), "color": "warning"},
            {"label": "Delete", "url": url_for("admin.delete_doctor", doctor_id=d.id), "color": "danger"},
            {"label": "Blacklist", "url": url_for("admin.blacklist_doctor", doctor_id=d.id), "color": "dark"},
            {"label": "Back ", "url": url_for("admin.admin_dashboard", tab_id= 2), "color": "info"},
        ] if current_user.role == "admin" else [
            {"label": "Book Appointment", "url": url_for("doctor.doctor_availability", doctor_id=d.id), "color": "info"},
            {"label": "Back ", "url": url_for("patient.patient_dashboard", tab_id=3), "color": "info"},
        ]
    } for d in doctors]

    tab_id = 2 if current_user.role == "admin" else 3
    tabs = [{"label": "Doctor Details", "columns": ["ID", "Name", "Specialization", "Experience", "Actions"], "rows": doctor_rows}, ]   
    return render_template("dashboard_base.html", title="Doctor Details", tabs=tabs, active_index=1)

@admin_bp.route("/edit_department/<int:department_id>", methods=["GET", "POST"])
@admin_required
def edit_department(department_id):
    department = Department.query.get_or_404(department_id)
    edit_url = url_for("admin.edit_department",department_id=department_id)
    home_url = get_home_url(4)
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


@admin_bp.route("/delete_department/<int:department_id>", methods=["GET", "POST"])
@admin_required
def delete_department(department_id):
    ap = Department.query.get_or_404(department_id)
    edit_url = url_for("admin.delete_department",department_id=department_id)
    home_url =get_home_url()
    if request.method == "POST":
        code = int(request.form.get("confirmation"))
        if code !=department_id:
            return render_template('confirmation.html',
                                   message ="Do You want to cancel this appointment",
                                   confirmation_code = department_id,
                                   button_msg = "Yes-Delete",
                                   return_url = edit_url
                                   )
        
        try:
            db.session.delete(ap)
            db.session.commit()
            flash("✅ That  appoinment is cancelled", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error cancelling appointment: {e}", "danger")
            return redirect(home_url)

    return render_template('confirmation.html',
                                   message ="Do You want to cancel this appointment",
                                   confirmation_code = department_id,
                                   button_msg = "Yes-Delete",
                                   return_url = edit_url
                                   )

@admin_bp.route("/doctors/new", methods=["GET", "POST"])
@admin_required
def add_doctor():
    doctor = None
    add_url = url_for("admin.add_doctor")
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



@admin_bp.route("/delete_doctor/<int:doctor_id>", methods=["GET", "POST"])
@admin_required
def delete_doctor(doctor_id):
    doc = Doctor.query.get_or_404(doctor_id)
    edit_url = url_for("admin.delete_doctor",doctor_id=doctor_id)
    tab_id = 2
    home_url = get_home_url(tab_id=tab_id)
    if request.method == "POST":
        code = int(request.form.get("confirmation"))
        if code !=doctor_id:
            return render_template('confirmation.html',
                                   message ="Do You want to remove this doctor", 
                                   confirmation_code = doctor_id,
                                   button_msg = "Yes-Delete",
                                   return_url = edit_url
                                   )
        
        try:
            app =doc.appointments
            for a in app:
                if a.status == AppointmentStatus.BOOKED:
                    slot = a.slot
                    if slot:
                        slot.cancel()
            doc.status = "deleted"
            db.session.commit()
            flash("✅ That  doctor is removed", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error removing doctor: {e}", "danger")
            return redirect(home_url)

    return render_template('confirmation.html',
                                   message ="Do You want to remove this doctor",
                                   confirmation_code = doctor_id,
                                   button_msg = "Yes-Remove",
                                   return_url = edit_url,
                                   cancel_url = home_url
                                   )

@admin_bp.route("/blacklist_doctor/<int:doctor_id>", methods=["GET", "POST"])
@admin_required
def blacklist_doctor(doctor_id):
    doc = Doctor.query.get_or_404(doctor_id)
    edit_url = url_for("admin.blacklist_doctor",doctor_id=doctor_id)
    tab_id = 2
    home_url = get_home_url(tab_id=tab_id)
    if request.method == "POST":
        code = int(request.form.get("confirmation"))
        if code !=doctor_id:
            return render_template('confirmation.html',
                                   message ="Do You want to blacklist this doctor", 
                                   confirmation_code = doctor_id,
                                   button_msg = "Yes-Blacklist",
                                   return_url = edit_url
                                   )
        
        try:
            app =doc.appointments
            for a in app:
                if a.status == AppointmentStatus.BOOKED:
                    slot = a.slot
                    if slot:
                        slot.cancel()
            doc.status = "blacklisted"
            db.session.commit()
            flash("✅ That  doctor is blacklisted", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error blacklisting doctor: {e}", "danger")
            return redirect(home_url)

    return render_template('confirmation.html',
                                   message ="Do You want to blacklist this doctor",
                                   confirmation_code = doctor_id,
                                   button_msg = "Yes-Blacklist",
                                   return_url = edit_url,
                                   cancel_url = home_url
                                   )


@admin_bp.route("/edit_patient/<int:patient_id>", methods=["GET", "POST"])
@role_required("admin", "patient")
def edit_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    edit_url = url_for("admin.edit_patient",patient_id=patient_id)
    if current_user.role == "patient" and current_user.id != patient_id:
        tab_id = 2
    else:
        tab_id =3
    home_url =get_home_url(tab_id=tab_id)
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



@admin_bp.route("/delete_patient/<int:patient_id>", methods=["GET", "POST"])
@admin_required
def delete_patient(patient_id):
    patient = Patient.query.filter(
                Patient.id == patient_id,
                Patient.status != "deleted"
            ).first()
    edit_url = url_for("admin.delete_patient", patient_id=patient_id)
    tab_id = 2
    home_url = get_home_url(tab_id=tab_id)
    if request.method == "POST":
        code = int(request.form.get("confirmation"))
        if code != patient_id:
            return render_template('confirmation.html',
                                   message ="Do You want to remove this patient", 
                                   confirmation_code = patient_id,
                                   button_msg = "Yes-Delete",
                                   return_url = edit_url
                                   )
        
        try:
            app =patient.appointments
            for a in app:
                if a.status == AppointmentStatus.BOOKED:
                    slot = a.slot
                    if slot:
                        slot.cancel()
            patient.status = "deleted"
            db.session.commit()
            flash("✅ That  patient is removed", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error removing patient: {e}", "danger")
            return redirect(home_url)

    return render_template('confirmation.html',
                                   message ="Do You want to remove this patient",
                                   confirmation_code = patient_id,
                                   button_msg = "Yes-Remove",
                                   return_url = edit_url,
                                   cancel_url = home_url
                                   )



@admin_bp.route("/blacklist_patient/<int:patient_id>", methods=["GET", "POST"])
@admin_required
def blacklist_patient(patient_id):
    patient = Patient.query.filter(
                Patient.id == patient_id,
                Patient.status != "deleted"
            ).first()
    edit_url = url_for("admin.blacklist_patient", patient_id=patient_id)
    tab_id = 2
    home_url = get_home_url(tab_id=tab_id)
    if request.method == "POST":
        code = int(request.form.get("confirmation"))
        if code != patient_id:
            return render_template('confirmation.html',
                                   message ="Do You want to blacklist this patient", 
                                   confirmation_code = patient_id,
                                   button_msg = "Yes-Blacklist",
                                   return_url = edit_url
                                   )
        
        try:
            app =patient.appointments
            for a in app:
                if a.status == AppointmentStatus.BOOKED:
                    slot = a.slot
                    if slot:
                        slot.cancel()
            patient.status = "blacklisted"
            db.session.commit()
            flash("✅ That  patient is blacklisted", "success")
            return redirect(home_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Error blacklisting patient: {e}", "danger")
            return redirect(home_url)

    return render_template('confirmation.html',
                                   message ="Do You want to blacklist this patient",
                                   confirmation_code = patient_id,
                                   button_msg = "Yes-Blacklist",
                                   return_url = edit_url,
                                   cancel_url = home_url
                                   )
