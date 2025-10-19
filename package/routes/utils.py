
from collections import defaultdict
from datetime import date
from datetime import datetime ,timedelta ,date
from flask import Flask, render_template, redirect, url_for, request ,send_from_directory, flash, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_wtf import CSRFProtect
from sqlalchemy import and_,or_
from sqlalchemy.orm import aliased
from werkzeug.security import check_password_hash

from package.routes.auth import admin_required,  doctor_required, patient_required ,role_required
from models import db, Appointment ,  Department , Doctor ,  Patient ,  Treatment ,  User,Slot ,Alert,AppointmentStatus




def field_value(obj, attr, default=""):
    if obj is None:
        return ""
    return getattr(obj, attr, default) if obj else default
def get_userID_fromEmail(email):
    user = User.query.filter_by(email=email).first()
    return user.id if user else None
def get_home_url(tab_id=1):
    if current_user.is_authenticated:
        role = current_user.role
        if role == "admin":
            return url_for("admin.admin_dashboard", tab_id=tab_id)
        elif role == "doctor":
            return url_for("doctor.doctor_dashboard", tab_id=tab_id)
        else:
            return url_for("patient.patient_dashboard", tab_id=tab_id)
    else:
        return url_for("login")

def get_patients_appointments(doctor = current_user):
    # Filter only this doctor's appointments
    appointments = doctor.appointments  
    
    # Group by patient_id
    patient_dict = defaultdict(lambda: {"last_seen": None, "next_appointment": None})
    
    today = date.today()
    
    for appt in appointments:
        slot_date = appt.slot.date  # assuming slot is related
        pid = appt.patient_id
        
        if appt.status.value == 'completed':
            # update last_seen if later than previous
            if (patient_dict[pid]["last_seen"] is None) or (slot_date > patient_dict[pid]["last_seen"]):
                patient_dict[pid]["last_seen"] = slot_date
                
        elif appt.status.value == 'booked':
            # update next_appointment if earlier than previous and future
            if slot_date >= today:
                if (patient_dict[pid]["next_appointment"] is None) or (slot_date < patient_dict[pid]["next_appointment"]):
                    patient_dict[pid]["next_appointment"] = slot_date
                    
    return dict(patient_dict)

def get_appointment_rows(doc_id=None, pat_id=None, start_date=None,status=None,
                         dept_id=None, active=None, actions=None):

    # Explicit aliases to avoid overlap warnings
    DoctorAlias = aliased(Doctor, flat=True)
    PatientAlias = aliased(Patient, flat=True)
    SlotAlias = aliased(Slot, flat=True)

    query = (
        Appointment.query
        .join(PatientAlias, Appointment.patient_id == PatientAlias.id)
        .join(DoctorAlias, Appointment.doctor_id == DoctorAlias.id)
        .join(SlotAlias, Appointment.slot_id == SlotAlias.id)
    )

    filters = []

    if doc_id:
        filters.append(Appointment.doctor_id == doc_id)
    if pat_id:
        filters.append(Appointment.patient_id == pat_id)
    if start_date:
        filters.append(SlotAlias.date >= start_date)
    if dept_id:
        filters.append(DoctorAlias.department_id == dept_id)
    if status is not None:
        filters.append(Appointment.status == status)
    elif active is not None:
        if active: 
            filters.append(Appointment.status == AppointmentStatus.BOOKED)
        else:  
            filters.append(Appointment.status != AppointmentStatus.BOOKED)

    if filters:
        query = query.filter(and_(*filters))

    appointments = query.order_by(SlotAlias.date.asc()).all()


    if not actions:
        actions =[{"label":"View","url":"patient.edit_appointment", "color": "warning"},
                  {"label":"Delete","url":"patient.delete_appointment", "color": "danger"},]
    elif actions[0] == "None":
        actions = None
    def build_actions(actions, appointment_id):
        if actions is None:
            return [{"label": "NoAction", "url": "", "color": "success"}]
        return [
            {
                "label": p.get("label", "NoAction"),
                "url": url_for(p["url"], appointment_id=appointment_id) if p.get("url") else "",
                "color": p.get("color", "success"),
            }
            for p in actions 
        ]

    appointment_rows = [
        {
            "ID": a.id,
            "doctor_id":a.doctor_id,
            "patient_id":a.patient_id,
            "Doctor": f"{a.doctor.name} {a.doctor.last_name}",
            "Patient": f"{a.patient.name} {a.patient.last_name}",
            "Date": a.slot.date.strftime("%Y-%m-%d"),
            "Session": a.slot.session,
            "Symptoms": a.reason,
            "Diagnosis": a.treatment.diagnosis if a.treatment else "N/A",
            "Prescription": a.treatment.prescription if a.treatment else "N/A",
            "Department": a.doctor.department.name if a.doctor.department else "N/A",
            "Medicines": a.treatment.medicines if a.treatment else "N/A",
            "Tests": a.treatment.tests if a.treatment else "N/A",
            "Status": a.status.value,  # BOOKED / CANCELLED / COMPLETED
            "Bill":a.treatment.consultation_fee if a.treatment else "",
            "Actions": build_actions(actions =actions,appointment_id= a.id),
        }
        for a in appointments
    ]



    return appointment_rows

def get_alerts(doc_id=None, pat_id=None):
    query = Alert.query.filter_by(status='open')

    if pat_id is not None:
        query = query.filter_by(patient_id=pat_id)
    if doc_id is not None:
        query = query.filter_by(doctor_id=doc_id)


    alerts = query.all()
    alert_rows = []

    def check(alert):
        if current_user.role == 'admin':
            return True
        elif pat_id is not None:
            return alert.direction
        else:
            return not alert.direction




    for  a in alerts:
        alert_rows.append({
            "ID": a.id,
            "Patient": a.patient.name +" " +a.patient.last_name,
            "P Mobile":a.patient.phone,
            "Doctor": a.doctor.name +" " +a.doctor.last_name,
            "D Mobile":a.doctor.phone,
            "Message":a.message,
            "Time": a.created_at.strftime("%Y-%m-%d"),
            "Actions": (
                [{"label": "Close", "url": url_for("admin.close_alert", alert_id=a.id), "color": "warning"}]
                if check(a)
                else []
            )
        })




    return alert_rows

def search_records(wheretosearch, feature, value):
    value_like = f"%{value}%"
    results = []
    if(wheretosearch !="appointments" and feature in ["tests" ,"medicine"]):
        return results, []
    user_type = current_user.type
    user_id = current_user.id  # assuming this is accessible

    # ---------------------- PATIENT SEARCH ----------------------
    if wheretosearch == "patients":
        query = None
        if feature == "name":
            query = Patient.query.filter(
                Patient.status != "deleted",
                or_(
                    Patient.name.like(value_like),
                    Patient.last_name.like(value_like)
                )
            )
        elif feature == "phone":
            query = Patient.query.filter(Patient.phone.like(value_like), Patient.status != "deleted")
        elif feature == "email":
            query = Patient.query.filter(Patient.email.like(value_like), Patient.status != "deleted")
        elif feature == "id":
            query = Patient.query.filter(Patient.id.like(value_like), Patient.status != "deleted")
        elif feature == "address":
            query = Patient.query.filter(Patient.address.like(value_like), Patient.status != "deleted")

        # Restrict results based on user type
        if user_type == "doctor":
            # doctor can see only their patients
            query = query.join(Appointment, Appointment.patient_id == Patient.id).filter(
                Appointment.doctor_id == user_id
            )
        elif user_type == "patient":
            # patient can see only themselves
            query = query.filter(Patient.id == user_id)
        # admins can see everything — no restriction

        if query:
            for p in query.all():
                results.append({
                    "type": "patient",
                    "id": p.id,
                    "P_name": f"{p.name} {getattr(p, 'last_name', '')}".strip(),
                    "D_name": "",
                    "phone": getattr(p, "phone", None),
                    "email": getattr(p, "email", None),
                    "address": getattr(p, "address", None),
                    "slot": "",
                    "date": ""
                })

    # ---------------------- DOCTOR SEARCH ----------------------
    elif wheretosearch == "doctors":
        query = None
        if feature == "name":
            query = Doctor.query.filter(
                Doctor.status != "deleted",
                or_(Doctor.name.like(value_like), Doctor.last_name.like(value_like))
            )
        elif feature == "phone":
            query = Doctor.query.filter(Doctor.phone.like(value_like), Doctor.status != "deleted")
        elif feature == "email":
            query = Doctor.query.filter(Doctor.email.like(value_like), Doctor.status != "deleted")
        elif feature == "id":
            query = Doctor.query.filter(Doctor.id.like(value_like), Doctor.status != "deleted")
        elif feature == "address":
            query = Doctor.query.filter(Doctor.address.like(value_like), Doctor.status != "deleted")

        # Restrict results
        if user_type == "doctor":
            # doctor can only see themselves
            query = query.filter(Doctor.id == user_id)
        elif user_type == "patient":
            # patient can see only doctors they have appointments with
            query = query.join(Appointment, Appointment.doctor_id == Doctor.id).filter(
                Appointment.patient_id == user_id
            )

        if query:
            for d in query.all():
                results.append({
                    "type": "doctor",
                    "id": d.id,
                    "P_name": "",
                    "D_name": f"{d.name} {getattr(d, 'last_name', '')}".strip(),
                    "phone": getattr(d, "phone", None),
                    "email": getattr(d, "email", None),
                    "address": getattr(d, "address", None),
                    "slot": "",
                    "date": ""
                })

    # ---------------------- APPOINTMENT SEARCH ----------------------
    elif wheretosearch == "appointments":
        query = (
            Appointment.query
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
        )

        if feature == "name":
            query = query.filter(or_(
                Patient.name.like(value_like),
                Doctor.name.like(value_like),
                Patient.last_name.like(value_like),
                Doctor.last_name.like(value_like)
            ))
        elif feature == "phone":
            query = query.filter(or_(
                Patient.phone.like(value_like),
                Doctor.phone.like(value_like)
            ))
        elif feature == "email":
            query = query.filter(or_(
                Patient.email.like(value_like),
                Doctor.email.like(value_like)
            ))
        elif feature == "id":
            query = query.filter(or_(
                Patient.id.like(value_like),
                Doctor.id.like(value_like),
                Appointment.id.like(value_like)
            ))
        elif feature == "address":
            query = query.filter(or_(
                Patient.address.like(value_like),
                Doctor.address.like(value_like)
            ))
        elif feature == "date":
            query = query.join(Slot, Appointment.slot_id == Slot.id).filter(Slot.date.like(value_like))
        elif feature == "medicine":
            query = query.join(Treatment, Appointment.id == Treatment.appointment_id).filter(
                Treatment.medicines.like(value_like)
            )
        elif feature == "tests":
            query = query.join(Treatment, Appointment.id == Treatment.appointment_id).filter(
                Treatment.tests.like(value_like)
            )

        # Restrict results
        if user_type == "doctor":
            query = query.filter(Appointment.doctor_id == user_id)
        elif user_type == "patient":
            query = query.filter(Appointment.patient_id == user_id)

        for a in query.all():
            results.append({
                "type": "appointment",
                "id": a.id,
                "P_name": f"{a.patient.name} {getattr(a.patient, 'last_name', '')}".strip(),
                "D_name": f"{a.doctor.name} {getattr(a.doctor, 'last_name', '')}".strip(),
                "slot": getattr(a, "slot", None).session if getattr(a, "slot", None) else None,
                "date": getattr(a, "slot", None).date.strftime("%Y-%m-%d") if getattr(a, "slot", None) else None,
                "status": getattr(a, "status", None).value if getattr(a, "status", None) else None,
                "medicine": getattr(a.treatment, "medicines", None) if a.treatment else None,
                "tests": getattr(a.treatment, "tests", None) if a.treatment else None,
                "phone": getattr(a.patient, "phone", None) or getattr(a.doctor, "phone", None),
                "email": getattr(a.patient, "email", None) or getattr(a.doctor, "email", None),
                "address": getattr(a.patient, "address", None) or getattr(a.doctor, "address", None),
            })

    # ---------------------- COLUMN STRUCTURE ----------------------
    searchResults_columns = [
        {"key": "id", "label": "ID"},
        {"key": "D_name", "label": "Doctor"},
        {"key": "P_name", "label": "Patient"},
        {"key": "phone", "label": "Phone"},
        {"key": "email", "label": "Email"},
        {"key": "address", "label": "Address"},
        {"key": "date", "label": "Date"},
        {"key": "slot", "label": "Session"},
        {"key": "status", "label": "Status"},
        {"key": "medicine", "label": "Medicine"},
        {"key": "tests", "label": "Tests"}
    ]
    return results, searchResults_columns

def search_all_old(db_path, search_term):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    results = []

    # Get all table names
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        # Get all columns for this table
        cur.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cur.fetchall()]

        for col in columns:
            try:
                query = f"""
                    SELECT rowid as id, {col} as value 
                    FROM {table}
                    WHERE CAST({col} AS TEXT) LIKE ?
                """
                cur.execute(query, (f"%{search_term}%",))
                for row in cur.fetchall():
                    results.append({
                        "table": table,
                        "column": col,
                        "row_id": row["id"],
                        "matched_value": row["value"]
                    })
            except Exception:
                # Skip unsearchable columns (e.g. blobs)
                continue

    conn.close()
    return results
