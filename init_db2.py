from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50))

    __mapper_args__ = {
        "polymorphic_identity": "user",
        "polymorphic_on": type
    }

class Admin(User):
    __tablename__ = "admins"
    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "admin"}

class Doctor(User):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    specialty = db.Column(db.String(100))
    __mapper_args__ = {"polymorphic_identity": "doctor"}

class Patient(User):
    __tablename__ = "patients"
    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    medical_history = db.Column(db.Text)
    __mapper_args__ = {"polymorphic_identity": "patient"}
