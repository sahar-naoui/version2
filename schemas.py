from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date, time
from enum import Enum

# ==================== ENUMS ====================

class WorkTypeEnum(str, Enum):
    DAY = "DAY"
    NIGHT = "NIGHT"
    BOTH = "BOTH"

class PlateClassEnum(str, Enum):
    TN = "TN"
    RS = "RS"
    ETAT = "ETAT"

class DayOfWeekEnum(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"

class AlertTypeEnum(str, Enum):
    ABSENCE = "ABSENCE"
    LATE = "LATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    PARKING_VIOLATION = "PARKING_VIOLATION"

class AbsenceStatusEnum(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ComplaintStatusEnum(str, Enum):
    OPEN = "OPEN"
    WARNING_SENT = "WARNING_SENT"
    BANNED = "BANNED"

# ==================== USER SCHEMAS ====================

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "employee"

class UserCreate(UserBase):
    password: str
    employee_id: Optional[int] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    employee_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# ==================== EMPLOYEE SCHEMAS ====================

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    work_type: WorkTypeEnum

class EmployeeCreate(EmployeeBase):
    """Schéma pour créer un employé"""
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    work_type: Optional[WorkTypeEnum] = None
    is_active: Optional[bool] = None

class EmployeeResponse(EmployeeBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== VEHICLE SCHEMAS ====================

class VehicleBase(BaseModel):
    plate_number: str
    plate_class: PlateClassEnum
    car_type: Optional[str] = None
    color: Optional[str] = None
    parking_spot: Optional[int] = None
    employee_id: Optional[int] = None

class VehicleCreate(VehicleBase):
    """Schéma pour créer un véhicule - is_authorized permet de définir si le véhicule est autorisé à entrer"""
    is_authorized: Optional[bool] = True  # Par défaut, le véhicule est autorisé

class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    plate_class: Optional[PlateClassEnum] = None
    car_type: Optional[str] = None
    color: Optional[str] = None
    parking_spot: Optional[int] = None
    employee_id: Optional[int] = None
    is_authorized: Optional[bool] = None

class VehicleResponse(VehicleBase):
    id: int
    is_authorized: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== WORK SCHEDULE SCHEMAS ====================

class WorkScheduleBase(BaseModel):
    employee_id: int
    day_of_week: DayOfWeekEnum
    start_time: Optional[time] = None
    end_time: Optional[time] = None

class WorkScheduleCreate(WorkScheduleBase):
    pass

class WorkScheduleUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None

class WorkScheduleResponse(WorkScheduleBase):
    id: int

    class Config:
        from_attributes = True

# ==================== ABSENCE SCHEMAS ====================

class AbsenceBase(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    justification: Optional[str] = None

class AbsenceCreate(AbsenceBase):
    pass

class AbsenceUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    justification: Optional[str] = None
    document_path: Optional[str] = None
    status: Optional[AbsenceStatusEnum] = None

class AbsenceResponse(AbsenceBase):
    id: int
    document_path: Optional[str] = None
    status: AbsenceStatusEnum
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== COMPLAINT SCHEMAS ====================

class ComplaintBase(BaseModel):
    complainant_employee_id: int
    accused_vehicle_plate: Optional[str] = None
    accused_vehicle_id: Optional[int] = None
    parking_spot: int

class ComplaintCreate(ComplaintBase):
    pass

class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatusEnum] = None

class ComplaintResponse(ComplaintBase):
    id: int
    photo_path: Optional[str] = None
    status: ComplaintStatusEnum
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== ALERT SCHEMAS ====================

class AlertBase(BaseModel):
    employee_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    alert_type: AlertTypeEnum
    message: Optional[str] = None

class AlertResponse(AlertBase):
    id: int
    sent_email: bool
    sent_sms: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== SANCTION SCHEMAS ====================

class SanctionBase(BaseModel):
    vehicle_id: int
    reason: str
    start_date: date
    end_date: date

class SanctionCreate(SanctionBase):
    pass

class SanctionResponse(SanctionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== PARKING ENTRY SCHEMAS ====================

class ParkingEntryBase(BaseModel):
    plate_number: str
    entry_time: datetime
    camera_location: Optional[str] = None
    detected_class: Optional[PlateClassEnum] = None
    confidence: Optional[float] = None

class ParkingEntryCreate(ParkingEntryBase):
    pass

class ParkingEntryResponse(ParkingEntryBase):
    id: int

    class Config:
        from_attributes = True

# ==================== STEG PHONE NUMBER SCHEMA ====================

class StegPhoneNumberResponse(BaseModel):
    phone_number: str
