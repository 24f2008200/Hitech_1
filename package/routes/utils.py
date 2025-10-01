
from flask import Flask, render_template, redirect, url_for, request ,send_from_directory, flash
from models import db,Admin ,  Appointment ,  Department , Doctor ,  Patient ,  Treatment ,  User,Slot
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from models import AppointmentStatus
from werkzeug.security import check_password_hash
from package.routes.auth import admin_required,  doctor_required, patient_required ,role_required
from flask_wtf import CSRFProtect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from datetime import datetime ,timedelta ,date
from sqlalchemy import and_

def field_value(obj, attr, default=""):
    if obj is None:
        return ""
    return getattr(obj, attr, default) if obj else default
def get_userID_fromEmail(email):
    user = User.query.filter_by(email=email).first()
    return user.id if user else None
def get_home_url():
    if current_user.is_authenticated:
        role = current_user.role
        if role == "admin":
            return url_for("admin.admin_dashboard")
        elif role == "doctor":
            return url_for("doctor.doctor_dashboard")
        else: 
            return url_for("patient.patient_dashboard")
    else:
        return url_for("login")

def get_appointment_rows(doc_id=None, pat_id=None, start_date=None, dept_id=None, active=None,actions =None):

    query = Appointment.query.join(Patient, Appointment.patient_id == Patient.id)\
                             .join(Doctor, Appointment.doctor_id == Doctor.id)\
                             .join(Slot, Appointment.slot_id == Slot.id)

    filters = []

    if doc_id:
        filters.append(Appointment.doctor_id == doc_id)
    if pat_id:
        filters.append(Appointment.patient_id == pat_id)
    if start_date:
        filters.append(Slot.date >= start_date)
    if dept_id:
        filters.append(Doctor.department_id == dept_id)
    if active is not None:
        if active: 
            filters.append(Appointment.status == AppointmentStatus.BOOKED)
        else:  
            filters.append(Appointment.status != AppointmentStatus.BOOKED)

    if filters:
        query = query.filter(and_(*filters))

    appointments = query.order_by(Slot.date.asc()).all()
    if not actions:
        actions =[{"label":"View","url":"patient.edit_appointment", "color": "warning"},
                  {"label":"Delete","url":"patient.delete_appointment", "color": "danger"},]
    

    appointment_rows = [
        {
            "ID": a.id,
            "Doctor": f"{a.doctor.name} {a.doctor.last_name}",
            "Patient": f"{a.patient.name} {a.patient.last_name}",
            "Date": a.slot.date.strftime("%Y-%m-%d"),
            "Session": a.slot.session,
            "Department": a.doctor.department.name if a.doctor.department else "N/A",
            "Status": a.status.value,  # BOOKED / CANCELLED / COMPLETED
            "Actions": [{"label":p["label"],"url":url_for(p["url"],appointment_id=a.id),"color":p["color"]} for p in actions
                # {"label": "View", "url": url_for("patient.edit_appointment", appointment_id=a.id), "color": "warning"},
                # {"label": "Delete", "url": url_for("patient.delete_appointment", appointment_id=a.id), "color": "danger"},
            ],
        }
        for a in appointments
    ]

    return appointment_rows
