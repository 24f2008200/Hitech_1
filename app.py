import os
import calendar
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
from sqlalchemy.orm import with_loader_criteria
from package.routes.utils import *
from package.routes.doctor import doctor_bp
from package.routes.patient import patient_bp
from package.routes.admin import admin_bp 



app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///api_database.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret-key"  
app.config['SECRET_KEY'] = 'supersecretkey'  



db.init_app(app)
# jwt = JWTManager(app)
# csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  
login_manager.login_message = "Please log in to access this page."

app.register_blueprint(doctor_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(admin_bp)




@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/")
def index():
    return render_template("login.html")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)  # stores ID in session
            role = user.role
            dashboard = "admin.admin_dashboard" if role =="admin" else "doctor.doctor_dashboard" if role =="doctor" else "patient.patient_dashboard"
            return redirect(url_for(dashboard, tab_id=1))
        return "Invalid credentials", 401
    return render_template("login.html")

@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith("/static/") or request.path.startswith("/api/"):
        return "Not Found", 404
    return redirect(url_for("login"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return render_template("login.html")




if __name__ == "__main__":
    app.run(debug=True)