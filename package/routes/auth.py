import os
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, User,  Doctor, Patient
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# def auth_required(fn):
#     """Wrapper around jwt_required(), toggled by ENFORCE_AUTH env var."""
#     if os.getenv("ENFORCE_AUTH", "false").lower() == "true":
#         return jwt_required()(fn)
#     return fn

# def current_user():
#     if os.getenv("ENFORCE_AUTH", "false").lower() != "true":
#         # Dummy user in dev mode
#         return User(id=1, email="dummy@example.com", name="Dummy", password="x")

#     user_id = int(get_jwt_identity())
#     claims = get_jwt()
#     role = claims.get("role")
#     user = db.session.get(User, user_id)
#     # Extra: we could even enforce that user.type == role here
#     return user


def role_required(*role_name):
    """Generic role-based decorator: admin, doctor, patient."""
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            user = current_user
            if user is None:
                return {"msg": "Not authenticated"}, 401

            if user.type not in role_name:
                return {"msg": f"Access denied, must be {role_name}"}, 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Specializations
admin_required = role_required("admin")
doctor_required = role_required("doctor")
patient_required = role_required("patient")
