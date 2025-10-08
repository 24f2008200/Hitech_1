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

class myModel(db.Model):
    __abstract__ = True

    def to_dict(self, include_relationships=False, seen=None, depth=1):
        if seen is None:
            seen = set()

        identity = (self.__class__, getattr(self, "id", None))
        if identity in seen:
            return {"id": getattr(self, "id", None)}
        seen.add(identity)

        result = {}
        mapper = self.__class__.__mapper__

        # Columns
        for column in mapper.columns:
            result[column.key] = getattr(self, column.key)

        # Relationships
        if include_relationships and depth > 0:
            for rel in mapper.relationships:
                value = getattr(self, rel.key)
                if value is not None:
                    if rel.uselist:
                        result[rel.key] = [
                            obj.to_dict(True, seen, depth - 1) for obj in value
                        ]
                    else:
                        result[rel.key] = value.to_dict(True, seen, depth - 1)

        return result

    # ---------------------------------------
    @classmethod
    def from_dict(cls, data, include_relationships=False, seen=None, depth=1, session=None):
        if seen is None:
            seen = set()

        # Detect polymorphic type (for User/Doctor/Patient)
        subtype = data.get("type")
        if subtype and subtype != cls.__mapper_args__.get("polymorphic_identity"):
            for subclass in cls.__subclasses__():
                if hasattr(subclass, "__mapper_args__"):
                    if subclass.__mapper_args__.get("polymorphic_identity") == subtype:
                        return subclass.from_dict(
                            data, include_relationships, seen, depth, session
                        )

        identity = (cls, data.get("id"))
        if identity in seen:
            return None
        seen.add(identity)

        obj = cls()
        mapper = cls.__mapper__

        # Simple columns
        for column in mapper.columns:
            key = column.key
            if key in data:
                setattr(obj, key, data[key])

        # Relationships
        if include_relationships and depth > 0:
            for rel in mapper.relationships:
                rel_name = rel.key
                if rel_name in data and data[rel_name] is not None:
                    rel_cls = rel.mapper.class_
                    if rel.uselist:
                        setattr(
                            obj,
                            rel_name,
                            [
                                rel_cls.from_dict(item, True, seen, depth - 1, session)
                                for item in data[rel_name]
                            ],
                        )
                    else:
                        setattr(
                            obj,
                            rel_name,
                            rel_cls.from_dict(data[rel_name], True, seen, depth - 1, session),
                        )

        if session:
            session.add(obj)
        return obj
