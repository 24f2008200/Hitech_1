from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, app as base_app, User, Role, Doctor, Patient, Department, Appointment

# App Config
app = base_app
app.secret_key = "super-secret-key"


# Routes
@app.route("/")
def home():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    print("hi" ,username,password)
    user = User.query.filter_by(username=username).first()
    print("hi" ,username,password)
    if user and user.check_password(password):
        session["user_id"] = user.id
        session["role"] = user.role.name
        flash("Login successful!", "success")
        # Redirect based on role
        if session["role"] == "ADMIN":
            return redirect(url_for("admin_dashboard"))
        elif session["role"] == "DOCTOR":
            return redirect(url_for("doctor_dashboard"))
        elif session["role"] == "PATIENT":
            return redirect(url_for("patient_dashboard"))
    else:
        flash("❌ Invalid username or password", "danger")
        return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("home"))


@app.route("/register_patient", methods=["GET", "POST"])
def register_patient():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        username = request.form["username"]
        password = request.form["password"]

        # Create Patient
        patient = Patient(first_name=first_name, last_name=last_name,
                          email=email, phone=phone)
        db.session.add(patient)
        db.session.flush()  

        # Create User
        user = User(username=username, password=password, role=Role.PATIENT, patient_id=patient.id)
        db.session.add(user)
        db.session.commit()

        flash("Patient registered successfully! Please login.", "success")
        return redirect(url_for("home"))

    return render_template("register_patient.html")


# ---------- Dashboards ----------
@app.route("/dashboard/admin")
def admin_dashboard():
    # ensure logged-in admin
    if session.get("role") != "ADMIN":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("home"))

    # Summary counts
    total_doctors = db.session.query(Doctor).count()
    total_patients = db.session.query(Patient).count()
    total_appointments = db.session.query(Appointment).count()


    return render_template(
        "admin_dashboard.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        results=None,
        entity=None,
        query=None,
        search_by=None
    )

@app.route("/admin/search", methods=["POST"])
def admin_search():
    if session.get("role") != "ADMIN":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("home"))

    entity = request.form.get("entity")          # 'doctor' or 'patient'
    search_by = request.form.get("search_by")    # 'name', 'id', 'contact'
    q = request.form.get("q", "").strip()

    results = []

    if not q:
        flash("Please enter a search query.", "warning")
        return redirect(url_for("admin_dashboard"))

    # ----- Search Doctors -----
    if entity == "doctor":
        if search_by == "id":
            if q.isdigit():
                doc = db.session.get(Doctor, int(q))
                if doc:
                    results = [doc]
            else:
                results = []
        elif search_by == "name":
            # search first OR last name
            results = db.session.query(Doctor).filter(
                (Doctor.first_name.ilike(f"%{q}%")) |
                (Doctor.last_name.ilike(f"%{q}%"))
            ).all()
        elif search_by == "contact":
            results = db.session.query(Doctor).filter(
                (Doctor.email.ilike(f"%{q}%")) |
                (Doctor.phone.ilike(f"%{q}%"))
            ).all()

    # ----- Search Patients -----
    elif entity == "patient":
        if search_by == "id":
            if q.isdigit():
                pat = db.session.get(Patient, int(q))
                if pat:
                    results = [pat]
            else:
                results = []
        elif search_by == "name":
            results = db.session.query(Patient).filter(
                (Patient.first_name.ilike(f"%{q}%")) |
                (Patient.last_name.ilike(f"%{q}%"))
            ).all()
        elif search_by == "contact":
            results = db.session.query(Patient).filter(
                (Patient.email.ilike(f"%{q}%")) |
                (Patient.phone.ilike(f"%{q}%"))
            ).all()

    # Get fresh counts for the dashboard summary
    total_doctors = db.session.query(Doctor).count()
    total_patients = db.session.query(Patient).count()
    total_appointments = db.session.query(Appointment).count()

    if not results:
        flash("No results found.", "info")

    return render_template(
        "admin_dashboard.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        results=results,
        entity=entity,
        query=q,
        search_by=search_by
    )


# ------------------ Edit doctor ------------------
@app.route("/admin/edit_doctor/<int:doctor_id>", methods=["GET", "POST"])
def edit_doctor(doctor_id):
    if session.get("role") != "ADMIN":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("home"))

    doctor = db.session.get(Doctor, doctor_id)
    if not doctor:
        flash("Doctor not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        doctor.first_name = request.form.get("first_name", doctor.first_name)
        doctor.last_name = request.form.get("last_name", doctor.last_name)
        doctor.email = request.form.get("email", doctor.email)
        doctor.phone = request.form.get("phone", doctor.phone)
        doctor.license_number = request.form.get("license_number", doctor.license_number)
        specialization_id = request.form.get("specialization_id")
        if specialization_id:
            doctor.specialization_id = int(specialization_id)
        new_password = request.form.get("password")
        if new_password:
            doctor.user.set_password(new_password)
        db.session.commit()
        flash("✅ Doctor updated successfully", "success")
        return redirect(url_for("admin_dashboard"))

    departments = db.session.query(Department).all()
    return render_template("edit_doctor.html", doctor=doctor, departments=departments ,user=doctor.user)


# ------------------ Edit patient ------------------
@app.route("/admin/edit_patient/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    if session.get("role") != "ADMIN":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("home"))

    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        patient.first_name = request.form.get("first_name", patient.first_name)
        patient.last_name = request.form.get("last_name", patient.last_name)
        patient.email = request.form.get("email", patient.email)
        patient.phone = request.form.get("phone", patient.phone)
        patient.address = request.form.get("address", patient.address)
        new_password = request.form.get("password")
        if new_password:
            patient.user.set_password(new_password)
        db.session.commit()
        flash("✅ Patient updated successfully", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_patient.html", patient=patient ,user=patient.user)

@app.route("/admin/blacklist_user/<int:user_id>", methods=["POST"])
def blacklist_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    flash(f"User {user.username} has been blacklisted.", "warning")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    # Link doctor/patient if exists
    doctor = Doctor.query.get(user.doctor_id) if user.doctor_id else None
    patient = Patient.query.get(user.patient_id) if user.patient_id else None

    if request.method == "POST":
        # Update core User fields
        user.username = request.form.get("username")
        user.role = request.form.get("role")

        # Update doctor fields if applicable
        if doctor:
            doctor.first_name = request.form.get("first_name")
            doctor.last_name = request.form.get("last_name")
            doctor.email = request.form.get("email")
            doctor.phone = request.form.get("phone")
            doctor.license_number = request.form.get("license_number")
            doctor.specialization_id = request.form.get("specialization_id")

        # Update patient fields if applicable
        if patient:
            patient.first_name = request.form.get("first_name")
            patient.last_name = request.form.get("last_name")
            patient.email = request.form.get("email")
            patient.phone = request.form.get("phone")

        # Password reset (only if provided)
        new_password = request.form.get("password")
        if new_password:
            user.set_password(new_password)

        db.session.commit()
        flash("✅ User details updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_user.html", user=user, doctor=doctor, patient=patient)



@app.route("/dashboard/doctor")
def doctor_dashboard():
    if session.get("role") != "DOCTOR":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("home"))
    user = db.session.get(User, session.get("user_id"))
    doctor = user.doctor_account if user else None
    appointments = doctor.appointments if doctor else []
    return render_template("doctor_dashboard.html", doctor=doctor, appointments=appointments)


@app.route("/dashboard/patient")
def patient_dashboard():
    if session.get("role") != "PATIENT":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("home"))
    user = db.session.get(User, session.get("user_id"))
    patient = user.patient_account if user else None
    appointments = patient.appointments if patient else []
    return render_template("patient_dashboard.html", patient=patient, appointments=appointments)


# ---------- Admin Functions ----------
@app.route("/admin/add_doctor", methods=["GET", "POST"])
def add_doctor():
    if session.get("role") != "ADMIN":
        flash("❌ Unauthorized", "danger")
        return redirect(url_for("home"))

    departments = Department.query.all()

    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        license_number = request.form["license_number"]
        specialization_id = request.form["specialization_id"]
        username = request.form["username"]
        password = request.form["password"]

        # Create Doctor
        doctor = Doctor(first_name=first_name, last_name=last_name,
                        email=email, phone=phone, license_number=license_number,
                        specialization_id=specialization_id)
        db.session.add(doctor)
        db.session.flush()

        # Create User
        user = User(username=username, password=password, role=Role.DOCTOR, doctor_id=doctor.id)
        db.session.add(user)
        db.session.commit()

        flash("✅ Doctor added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_doctor.html", departments=departments)



if __name__ == "__main__":
    app.run(debug=True)
