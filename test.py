from operator import and_ ,or_
from flask import Flask
from faker import Faker
import random
from datetime import date, timedelta,datetime
from sqlalchemy.orm import aliased
import calendar
from flask import Blueprint, render_template, request, abort, url_for
from flask_login import current_user , LoginManager
from package.routes import doctor
from models import *
from package.routes.auth import *
from package.routes.utils import *

from models import db, Admin, Department, Doctor, Patient, Slot, Appointment, AppointmentStatus, Treatment, User,Sessions

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///api_database.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

fake = Faker()

NO_OF_PATIENTS = 40
NO_OF_DOCTORS = 10  
NO_OF_APPOINTMENTS_PER_DOCTOR = 4
NO_OF_PAST_DAYS = 30
NO_OF_FUTURE_DAYS = 30
START_DATE = date.today() - timedelta(days=NO_OF_PAST_DAYS)
END_DATE = date.today() + timedelta(days=NO_OF_FUTURE_DAYS)

patient_id= 2

def test():
    r = search(wheretosearch="patients", feature="name", value="priya")
    print(len(r))

   
def get_appointment_rows(doc_id=None, pat_id=None, start_date=None,
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
    if active is not None:
        if active: 
            filters.append(Appointment.status == AppointmentStatus.BOOKED)
        else:  
            filters.append(Appointment.status != AppointmentStatus.BOOKED)

    if filters:
        query = query.filter(and_(*filters))

    appointments = query.order_by(SlotAlias.date.asc()).all()
    return [appt.to_dict(include_relationships=True) for appt in appointments]

def check_database():
    # result = Patient.query.filter(Patient.id == patient_id).first()
    # print (len(result.appointments))
    # print(result.appointments[0].to_dict(include_relationships=False))

    result = get_appointment_rows(pat_id=None, start_date=None)
    print(len(result))
    print(result)

def availability():
    doctor_id = 42
    doctor = Doctor.query.filter(
        Doctor.id == doctor_id,
        Doctor.status != "deleted"
    ).first()
    today = date.today()
    months = []

    for m in range(4):  # next 4 months
        month_start = (today.replace(day=1) + timedelta(days=32*m)).replace(day=1)
        year, month = month_start.year, month_start.month

        # Get all weeks for this month (as list of weeks, each week = [Mon..Sun])
        cal = calendar.Calendar(firstweekday=0)  # Monday = 0
        weeks = cal.monthdatescalendar(year, month)
        month_start=date(2025, 10, 7)
        month_end=date(2025, 10, 8)
        # Get all availability for that month
        #month_end = weeks[-1][-1]
        availabilities = Slot.query.filter(
            Slot.doctor_id == doctor_id,
            Slot.date >= month_start,
            Slot.date <= month_end
        ).all()

        free_slots = [s for s in availabilities]
        

        avail_map = {(a.date, a.session): a for a in free_slots}
        months.append((month_start, weeks, avail_map))
  

    return render_template("availability.html", doctor=doctor, months=months,Sessions=Sessions)

def search(wheretosearch=None, feature=None, value=None):

    value_like = f"%{value}%"
    results = []
    print (wheretosearch, feature, value, value_like)
    if wheretosearch == "patients":
        query = None
        if feature == "name":
            query = Patient.query.filter(Patient.status != "deleted",
                or_(
                Patient.name.like(value_like),
                Patient.last_name.like(value_like)  # if you have last_name
            ))
        # elif feature == "phone":
        #     query = Patient.query.filter(Patient.phone.like(value_like), Patient.status != "deleted")
        # elif feature == "email":
        #     query = Patient.query.filter(Patient.email.like(value_like), Patient.status != "deleted")
        # elif feature == "id":
        #     query = Patient.query.filter(Patient.id.like(value_like), Patient.status != "deleted")
        # elif feature == "address":
        #     query = Patient.query.filter(Patient.address.like(value_like), Patient.status != "deleted")
    
        if query:
            for p in query.all():
                results.append({
                    "type": "patient",
                    "id": p.id,
                    "P_name": f"{p.name} {getattr(p, 'last_name', '')}".strip(),
                    "D_name":"",
                    "phone": getattr(p, "phone", None),
                    "email": getattr(p, "email", None),
                    "address": getattr(p, "address", None),
                    "slot":"",
                    "date":""
                    
                })
                print(p)

    # elif wheretosearch == "doctors":
    #     query = None
    #     if feature == "name":
    #         query = Doctor.query.filter(or_(
    #             Doctor.name.like(value_like),
    #             Doctor.last_name.like(value_like),
    #              Doctor.status != "deleted"
    #         ))
    #     elif feature == "phone":
    #         query = Doctor.query.filter(Doctor.phone.like(value_like), Doctor.status != "deleted")
    #     elif feature == "email":
    #         query = Doctor.query.filter(Doctor.email.like(value_like), Doctor.status != "deleted")
    #     elif feature == "id":
    #         query = Doctor.query.filter(Doctor.id.like(value_like), Doctor.status != "deleted")
    #     elif feature == "address":
    #         query = Doctor.query.filter(Doctor.address.like(value_like), Doctor.status != "deleted")

    #     if query:
    #         for d in query.all():
    #             results.append({
    #                 "type": "doctor",
    #                 "id": d.id,
    #                 "P_name": "",
    #                 "D_name": f"{d.name} {getattr(d, 'last_name', '')}".strip(),
    #                 "phone": getattr(d, "phone", None),
    #                 "email": getattr(d, "email", None),
    #                 "address": getattr(d, "address", None),
    #                 "slot":"",
    #                 "date":""
    #             })

    # elif wheretosearch == "appointments":
    #     query = (Appointment.query
    #      .join(Patient, Appointment.patient_id == Patient.id)
    #      .join(Doctor, Appointment.doctor_id == Doctor.id))

    #     if feature == "name":
    #         query = query.filter(or_(
    #             Patient.name.like(value_like),
    #             Doctor.name.like(value_like),
    #             Patient.last_name.like(value_like),
    #             Doctor.last_name.like(value_like)
    #         ))
    #     elif feature == "phone":
    #         query = query.filter(or_(
    #             Patient.phone.like(value_like),
    #             Doctor.phone.like(value_like)
    #         ))
    #     elif feature == "email":
    #         query = query.filter(or_(
    #             Patient.email.like(value_like),
    #             Doctor.email.like(value_like)
    #         ))
    #     elif feature == "id":
    #         query = query.filter(or_(
    #             Patient.id.like(value_like),
    #             Doctor.id.like(value_like),
    #             Appointment.id.like(value_like)
    #         ))
    #     elif feature == "address":
    #         query = query.filter(or_(
    #             Patient.address.like(value_like),
    #             Doctor.address.like(value_like)
    #         ))
    #     elif feature == "date":
    #         query = query.join(Slot, Appointment.slot_id == Slot.id).filter(
    #             Slot.date.like(value_like)
    #         )
    #     # elif feature == "medicine":
    #     #     query = query.join(Treatment, Appointment.id == Treatment.appointment_id).filter(
    #     #         Treatment.medicine.like(value_like)
    #     #     )
    #     # elif feature == "tests":
    #     #     query = query.join(Treatment, Appointment.id == Treatment.appointment_id).filter(
    #     #         Treatment.tests.like(value_like)
    #     #     )
    
    #     for a in query.all():
    #         # print (a.slot.date ,a.slot.session if a.slot else "No slot")
    #         if a.treatment:
    #             print (a.treatment.medicine, a.treatment.tests)
    #         results.append({
    #             "type": "appointment",
    #             "id": a.id,
    #             "P_name": f"{a.patient.name} {getattr(a.patient, 'last_name', '')}".strip(),
    #             "D_name": f"{a.doctor.name} {getattr(a.doctor, 'last_name', '')}".strip(),
    #             "slot": getattr(a, "slot", None).session if getattr(a, "slot", None) else None,
    #             "date": getattr(a, "slot", None).date.strftime("%Y-%m-%d") if getattr(a, "slot", None) else None,
    #             "status": getattr(a, "status", None).value if getattr(a, "status", None) else None,
    #             # "medicine": getattr(a.treatment, "medicine", None) if a.treatment else None,
    #             # "tests": getattr(a.treatment, "tests", None) if a.treatment else None,
    #             "phone": getattr(a.patient, "phone", None) or getattr(a.doctor, "phone", None),
    #             "email": getattr(a.patient, "email", None) or getattr(a.doctor, "email", None),
    #             "address": getattr(a.patient, "address", None) or getattr(a.doctor, "address", None),   
    #         })
    # # searchResults_columns = [
    #     {"key": "id", "label": "ID"},
    #     {"key": "D_name", "label": "Doctor"},
    #     {"key": "P_name", "label": "Patient"},
    #         {"key": "phone", "label": "Phone"},
    #     {"key": "email", "label": "Email"},
    #     {"key": "address", "label": "Address"},
    #     {"key": "date", "label": "Date"},
    #     {"key": "slot", "label": "Session"},
    #     {"key": "status", "label": "Status"},
    #     # {"key": "medicine", "label": "Medicine"},
    #     # {"key": "tests", "label": "Tests"}
        
    # ]
    return results
    return render_template("search.html", title="Search Results", 
                           searchResults_columns=searchResults_columns, 
                           searchResults_rows=results)


    return fromWhere + " " + field + " " + query



if __name__ == "__main__": 
    with app.app_context():
        test()
