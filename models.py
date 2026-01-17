"""
Modèles de Base de Données - Système de Gestion de Parking STEG
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Date, Time, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="employee")  # admin, rh, employee
    is_active = Column(Boolean, default=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Lien avec employé
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="user_account", uselist=False)


class WorkTypeEnum(str, enum.Enum):
    DAY = "DAY"
    NIGHT = "NIGHT"
    BOTH = "BOTH"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(150))
    work_type = Column(SQLEnum(WorkTypeEnum), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicles = relationship("Vehicle", back_populates="employee", cascade="all, delete-orphan")
    work_schedules = relationship("WorkSchedule", back_populates="employee", cascade="all, delete-orphan")
    absences = relationship("Absence", back_populates="employee", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="employee", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="complainant", foreign_keys="Complaint.complainant_employee_id", cascade="all, delete-orphan")
    user_account = relationship("User", back_populates="employee", uselist=False)


class PlateClassEnum(str, enum.Enum):
    TN = "TN"
    RS = "RS"
    ETAT = "ETAT"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number = Column(String(50), unique=True, nullable=False)  # Détecté par OCR
    plate_class = Column(SQLEnum(PlateClassEnum), nullable=False)
    car_type = Column(String(50))  # Type de voiture
    color = Column(String(50))  # Couleur
    parking_spot = Column(Integer)  # Numéro de place
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_authorized = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="vehicles")
    alerts = relationship("Alert", back_populates="vehicle", cascade="all, delete-orphan")
    sanctions = relationship("Sanction", back_populates="vehicle", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="accused_vehicle", foreign_keys="Complaint.accused_vehicle_id")


class DayOfWeekEnum(str, enum.Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class WorkSchedule(Base):
    __tablename__ = "work_schedules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    day_of_week = Column(SQLEnum(DayOfWeekEnum), nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)

    employee = relationship("Employee", back_populates="work_schedules")


class ParkingEntry(Base):
    __tablename__ = "parking_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number = Column(String(50))
    entry_time = Column(DateTime)
    camera_location = Column(String(50))
    detected_class = Column(SQLEnum(PlateClassEnum))
    confidence = Column(Float)


class AlertTypeEnum(str, enum.Enum):
    ABSENCE = "ABSENCE"
    LATE = "LATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    PARKING_VIOLATION = "PARKING_VIOLATION"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    alert_type = Column(SQLEnum(AlertTypeEnum), nullable=False)
    message = Column(Text)
    sent_email = Column(Boolean, default=False)
    sent_sms = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="alerts")
    vehicle = relationship("Vehicle", back_populates="alerts")


class AbsenceStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Absence(Base):
    __tablename__ = "absences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    justification = Column(Text, nullable=True)
    document_path = Column(String(255), nullable=True)  # Chemin vers le justificatif
    status = Column(SQLEnum(AbsenceStatusEnum), default=AbsenceStatusEnum.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="absences")


class ComplaintStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    WARNING_SENT = "WARNING_SENT"
    BANNED = "BANNED"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complainant_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    accused_vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    accused_vehicle_plate = Column(String(50), nullable=True)  # Si le véhicule n'est pas dans la BD
    parking_spot = Column(Integer, nullable=False)
    photo_path = Column(String(255), nullable=True)  # Photo de la réclamation
    status = Column(SQLEnum(ComplaintStatusEnum), default=ComplaintStatusEnum.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)

    complainant = relationship("Employee", back_populates="complaints", foreign_keys=[complainant_employee_id])
    accused_vehicle = relationship("Vehicle", back_populates="complaints", foreign_keys=[accused_vehicle_id])


class Sanction(Base):
    __tablename__ = "sanctions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    reason = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="sanctions")
