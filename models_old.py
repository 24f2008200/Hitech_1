class Spot(db.Model, myModel):
    __tablename__ = "spots"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(10), nullable=False)  # e.g. morning, afternoon, evening

    appointment = db.relationship("Appointment", back_populates="spot", uselist=False)

    @property
    def is_busy(self):
        """A spot is busy if there's a booked appointment."""
        return self.appointment is not None and self.appointment.status == AppointmentStatus.BOOKED

    @property
    def is_free(self):
        return not self.is_busy
class Appointment(db.Model, myModel):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey("spots.id"), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)

    spot = db.relationship("Spot", back_populates="appointment")
    patient = db.relationship("Patient", back_populates="appointments")
def add_spot(doctor_id, date, session):
    spot = Spot.query.filter_by(doctor_id=doctor_id, date=date, session=session).first()
    if spot:
        raise ValueError("Spot already exists.")
    spot = Spot(doctor_id=doctor_id, date=date, session=session)
    db.session.add(spot)
    db.session.commit()
    return spot
