def search_records(wheretosearch, feature, value):
    value_like = f"%{value}%"
    results = []
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
            for p in query.distinct().all():
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
            for d in query.distinct().all():
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
