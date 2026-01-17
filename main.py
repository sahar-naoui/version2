"""
API FastAPI - Système de Gestion de Parking STEG
"""

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date, time
import os
import shutil

from database import SessionLocal, engine, Base
from models import (
    User, Employee, Vehicle, WorkSchedule, Alert, Absence, Complaint, Sanction,
    ParkingEntry, WorkTypeEnum, PlateClassEnum, DayOfWeekEnum, AlertTypeEnum,
    AbsenceStatusEnum, ComplaintStatusEnum
)
from schemas import (
    UserCreate, UserResponse, UserUpdate, Token, LoginRequest,
    EmployeeCreate, EmployeeResponse, EmployeeUpdate,
    VehicleCreate, VehicleResponse, VehicleUpdate,
    WorkScheduleCreate, WorkScheduleResponse, WorkScheduleUpdate,
    AbsenceCreate, AbsenceResponse, AbsenceUpdate,
    ComplaintCreate, ComplaintResponse, ComplaintUpdate,
    AlertResponse, SanctionCreate, SanctionResponse,
    ParkingEntryCreate, ParkingEntryResponse,
    StegPhoneNumberResponse
)
from auth import (
    get_db, get_current_active_user, get_optional_user,
    get_password_hash, verify_password, create_access_token,
    require_admin_or_rh, require_admin, require_employee_or_above
)
from services import check_and_send_absence_alerts, check_night_vehicle_presence, process_complaint_sanction

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="STEG Parking Management API",
    description="API de gestion du parking STEG avec système d'alertes automatiques",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dossier pour stocker les fichiers uploadés
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "complaints"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "absences"), exist_ok=True)

# ==================== HEALTH CHECK ====================

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {
        "status": "ok",
        "service": "STEG Parking Management API",
        "version": "2.0.0"
    }

# ==================== AUTHENTIFICATION ====================

from fastapi.security import OAuth2PasswordRequestForm

@app.post("/api/auth/login", response_model=Token, tags=["Authentification"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user:
        user_count = db.query(User).count()
        if user_count == 0:
            admin_user = User(
                username="admin",
                email="admin@steg.tn",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrateur",
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            user = admin_user
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte utilisateur désactivé"
        )

    from datetime import timedelta
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentification"])
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Créer un nouvel utilisateur (inscription)"""
    # Vérifier que l'username n'existe pas déjà
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà utilisé")
    
    # Vérifier que l'email n'existe pas déjà
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    # Créer le nouvel utilisateur
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        employee_id=user_data.employee_id,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/auth/create-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentification"])
async def create_admin(
    username: str = "admin",
    password: str = "admin123",
    db: Session = Depends(get_db)
):
    """Créer un utilisateur admin (utile si la base de données est vide)"""
    # Vérifier si un admin existe déjà
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Utilisateur '{username}' existe déjà")
    
    admin_user = User(
        username=username,
        email=f"{username}@steg.tn",
        hashed_password=get_password_hash(password),
        full_name="Administrateur",
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user

@app.get("/api/auth/me", response_model=UserResponse, tags=["Authentification"])
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Obtenir les informations de l'utilisateur connecté"""
    return current_user

@app.put("/api/auth/profile", response_model=UserResponse, tags=["Authentification"])
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Modifier le profil de l'utilisateur connecté"""
    if user_update.email:
        # Vérifier que l'email n'est pas déjà utilisé
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        current_user.email = user_update.email
    
    if user_update.full_name:
        current_user.full_name = user_update.full_name
    
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(current_user)
    return current_user

# ==================== PUBLIC ENDPOINTS (GUEST) ====================

@app.get("/api/public/work-schedules", response_model=List[WorkScheduleResponse], tags=["Public - Accès libre"])
async def get_work_schedules(
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Consulter les horaires de travail (public - pas d'authentification requise)"""
    query = db.query(WorkSchedule)
    if employee_id:
        query = query.filter(WorkSchedule.employee_id == employee_id)
    schedules = query.all()
    return schedules

@app.get("/api/public/steg-phone", response_model=StegPhoneNumberResponse, tags=["Public - Accès libre"])
async def get_steg_phone_number():
    """Consulter le numéro d'appel de STEG (public - pas d'authentification requise)"""
    # Numéro STEG fixe
    return StegPhoneNumberResponse(phone_number="+216 71 340 211")

# ==================== EMPLOYEE ENDPOINTS (Employee, RH, Admin) ====================

@app.get("/api/employee/parking-spot", response_model=Optional[int], tags=["Espace Employé"])
async def get_my_parking_spot(
    current_user: User = Depends(require_employee_or_above),
    db: Session = Depends(get_db)
):
    """Consulter le numéro de place de l'utilisateur connecté"""
    if not current_user.employee_id:
        return None
    
    vehicle = db.query(Vehicle).filter(Vehicle.employee_id == current_user.employee_id).first()
    if vehicle:
        return vehicle.parking_spot
    return None

@app.post("/api/employee/complaints", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED, tags=["Espace Employé"])
async def create_complaint(
    parking_spot: int = Form(...),
    accused_vehicle_plate: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_employee_or_above),
    db: Session = Depends(get_db)
):
    """Ajouter une réclamation avec photo"""
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="Utilisateur non lié à un employé")
    
    # Vérifier si le véhicule existe
    accused_vehicle = None
    accused_vehicle_id = None
    if accused_vehicle_plate:
        accused_vehicle = db.query(Vehicle).filter(
            Vehicle.plate_number == accused_vehicle_plate
        ).first()
        if accused_vehicle:
            accused_vehicle_id = accused_vehicle.id
    
    # Sauvegarder la photo si fournie
    photo_path = None
    if photo:
        file_ext = os.path.splitext(photo.filename)[1]
        filename = f"complaint_{current_user.employee_id}_{datetime.now().timestamp()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, "complaints", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        photo_path = file_path
    
    complaint = Complaint(
        complainant_employee_id=current_user.employee_id,
        accused_vehicle_id=accused_vehicle_id,
        accused_vehicle_plate=accused_vehicle_plate,
        parking_spot=parking_spot,
        photo_path=photo_path,
        status=ComplaintStatusEnum.OPEN
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    
    # Traiter la réclamation (avertissement ou sanction)
    process_complaint_sanction(db, complaint)
    
    return complaint

@app.get("/api/employee/absences", response_model=List[AbsenceResponse], tags=["Espace Employé"])
async def get_my_absences(
    current_user: User = Depends(require_employee_or_above),
    db: Session = Depends(get_db)
):
    """Consulter les absences de l'utilisateur connecté"""
    if not current_user.employee_id:
        return []
    
    absences = db.query(Absence).filter(
        Absence.employee_id == current_user.employee_id
    ).order_by(Absence.created_at.desc()).all()
    return absences

@app.post("/api/employee/absences", response_model=AbsenceResponse, status_code=status.HTTP_201_CREATED, tags=["Espace Employé"])
async def create_absence_justification(
    start_date: date = Form(...),
    end_date: date = Form(...),
    start_time: Optional[time] = Form(None),
    end_time: Optional[time] = Form(None),
    justification: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_employee_or_above),
    db: Session = Depends(get_db)
):
    """Ajouter une justification d'absence avec document"""
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="Utilisateur non lié à un employé")
    
    # Sauvegarder le document si fourni
    document_path = None
    if document:
        file_ext = os.path.splitext(document.filename)[1]
        filename = f"absence_{current_user.employee_id}_{datetime.now().timestamp()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, "absences", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(document.file, buffer)
        document_path = file_path
    
    absence = Absence(
        employee_id=current_user.employee_id,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        justification=justification,
        document_path=document_path,
        status=AbsenceStatusEnum.PENDING
    )
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return absence

@app.get("/api/employee/alerts", response_model=List[AlertResponse], tags=["Espace Employé"])
async def get_my_alerts(
    current_user: User = Depends(require_employee_or_above),
    db: Session = Depends(get_db)
):
    """Consulter les alertes de l'utilisateur connecté"""
    if not current_user.employee_id:
        return []
    
    alerts = db.query(Alert).filter(
        Alert.employee_id == current_user.employee_id
    ).order_by(Alert.created_at.desc()).all()
    return alerts

# ==================== ADMIN + RH ENDPOINTS ====================

@app.get("/api/admin/employees", response_model=List[EmployeeResponse], tags=["Gérer Employés"])
async def list_employees(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Gérer les employés (liste)"""
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees

@app.post("/api/admin/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, tags=["Gérer Employés"])
async def create_employee(
    employee: EmployeeCreate,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Créer un nouvel employé"""
    db_employee = Employee(**employee.dict())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

@app.get("/api/admin/employees/{employee_id}", response_model=EmployeeResponse, tags=["Gérer Employés"])
async def get_employee(
    employee_id: int,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Obtenir un employé par ID"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employé non trouvé")
    return employee

@app.put("/api/admin/employees/{employee_id}", response_model=EmployeeResponse, tags=["Gérer Employés"])
async def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Modifier un employé"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employé non trouvé")
    
    update_data = employee_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    db.commit()
    db.refresh(employee)
    return employee

@app.delete("/api/admin/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Gérer Employés"])
async def delete_employee(
    employee_id: int,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Supprimer un employé"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employé non trouvé")
    db.delete(employee)
    db.commit()

@app.get("/api/admin/vehicles", response_model=List[VehicleResponse], tags=["Gérer Véhicules"])
async def list_vehicles(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Gérer les véhicules (liste)"""
    vehicles = db.query(Vehicle).offset(skip).limit(limit).all()
    return vehicles

@app.post("/api/admin/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED, tags=["Gérer Véhicules"])
async def create_vehicle(
    vehicle: VehicleCreate,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Créer un nouveau véhicule (avec matricule détecté par OCR)"""
    # Vérifier que le numéro de plaque n'existe pas déjà
    existing = db.query(Vehicle).filter(Vehicle.plate_number == vehicle.plate_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Numéro de plaque déjà enregistré")
    
    db_vehicle = Vehicle(**vehicle.dict())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

@app.get("/api/admin/vehicles/{vehicle_id}", response_model=VehicleResponse, tags=["Gérer Véhicules"])
async def get_vehicle(
    vehicle_id: int,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Obtenir un véhicule par ID"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Véhicule non trouvé")
    return vehicle

@app.put("/api/admin/vehicles/{vehicle_id}", response_model=VehicleResponse, tags=["Gérer Véhicules"])
async def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Modifier un véhicule"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Véhicule non trouvé")
    
    update_data = vehicle_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)
    
    db.commit()
    db.refresh(vehicle)
    return vehicle

@app.delete("/api/admin/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Gérer Véhicules"])
async def delete_vehicle(
    vehicle_id: int,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Supprimer un véhicule"""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Véhicule non trouvé")
    db.delete(vehicle)
    db.commit()

@app.get("/api/admin/complaints", response_model=List[ComplaintResponse], tags=["Gérer Réclamations"])
async def list_complaints(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Gérer les réclamations"""
    complaints = db.query(Complaint).offset(skip).limit(limit).order_by(Complaint.created_at.desc()).all()
    return complaints

@app.put("/api/admin/complaints/{complaint_id}", response_model=ComplaintResponse, tags=["Gérer Réclamations"])
async def update_complaint(
    complaint_id: int,
    complaint_update: ComplaintUpdate,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Modifier le statut d'une réclamation"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Réclamation non trouvée")
    
    if complaint_update.status:
        complaint.status = complaint_update.status
        # Traiter la réclamation si nécessaire
        process_complaint_sanction(db, complaint)
    
    db.commit()
    db.refresh(complaint)
    return complaint

@app.get("/api/admin/absences", response_model=List[AbsenceResponse], tags=["Gérer Absences"])
async def list_absences(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[AbsenceStatusEnum] = None,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Gérer les absences"""
    query = db.query(Absence)
    if status_filter:
        query = query.filter(Absence.status == status_filter)
    absences = query.offset(skip).limit(limit).order_by(Absence.created_at.desc()).all()
    return absences

@app.put("/api/admin/absences/{absence_id}/verify", response_model=AbsenceResponse, tags=["Gérer Absences"])
async def verify_absence(
    absence_id: int,
    status: AbsenceStatusEnum = Form(...),
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Vérifier une justification d'absence (approuver ou rejeter)"""
    absence = db.query(Absence).filter(Absence.id == absence_id).first()
    if not absence:
        raise HTTPException(status_code=404, detail="Absence non trouvée")
    
    absence.status = status
    db.commit()
    db.refresh(absence)
    return absence

@app.post("/api/admin/sanctions", response_model=SanctionResponse, status_code=status.HTTP_201_CREATED, tags=["Gérer Sanctions"])
async def create_sanction(
    sanction: SanctionCreate,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Sanctionner un employé"""
    # Vérifier que le véhicule existe
    vehicle = db.query(Vehicle).filter(Vehicle.id == sanction.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Véhicule non trouvé")
    
    db_sanction = Sanction(**sanction.dict())
    db.add(db_sanction)
    
    # Désautoriser le véhicule pendant la période de sanction
    vehicle.is_authorized = False
    
    db.commit()
    db.refresh(db_sanction)
    return db_sanction

@app.get("/api/admin/sanctions", response_model=List[SanctionResponse], tags=["Gérer Sanctions"])
async def list_sanctions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Liste des sanctions"""
    sanctions = db.query(Sanction).offset(skip).limit(limit).order_by(Sanction.created_at.desc()).all()
    return sanctions

@app.get("/api/admin/profiles", response_model=List[UserResponse], tags=["Gérer Profils"])
async def list_profiles(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Gérer les profils utilisateurs"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.put("/api/admin/profiles/{user_id}", response_model=UserResponse, tags=["Gérer Profils"])
async def update_profile_admin(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin_or_rh),
    db: Session = Depends(get_db)
):
    """Modifier un profil utilisateur (Admin/RH)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

# ==================== ADMIN ONLY ENDPOINTS ====================

@app.get("/api/admin/rh", response_model=List[UserResponse], tags=["Gérer RH"])
async def list_rh_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Gérer les utilisateurs RH"""
    users = db.query(User).filter(User.role == "rh").offset(skip).limit(limit).all()
    return users

@app.post("/api/admin/rh", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Gérer RH"])
async def create_rh_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Créer un utilisateur RH"""
    # Vérifier que l'username n'existe pas
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà utilisé")
    
    # Vérifier que l'email n'existe pas
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role="rh",
        employee_id=user_data.employee_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/api/admin/work-schedules", response_model=List[WorkScheduleResponse], tags=["Gérer Horaires"])
async def list_work_schedules_admin(
    employee_id: Optional[int] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Gérer les horaires de travail"""
    query = db.query(WorkSchedule)
    if employee_id:
        query = query.filter(WorkSchedule.employee_id == employee_id)
    schedules = query.all()
    return schedules

@app.post("/api/admin/work-schedules", response_model=WorkScheduleResponse, status_code=status.HTTP_201_CREATED, tags=["Gérer Horaires"])
async def create_work_schedule(
    schedule: WorkScheduleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Créer un horaire de travail"""
    db_schedule = WorkSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@app.put("/api/admin/work-schedules/{schedule_id}", response_model=WorkScheduleResponse, tags=["Gérer Horaires"])
async def update_work_schedule(
    schedule_id: int,
    schedule_update: WorkScheduleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Modifier un horaire de travail"""
    schedule = db.query(WorkSchedule).filter(WorkSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Horaire non trouvé")
    
    update_data = schedule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)
    
    db.commit()
    db.refresh(schedule)
    return schedule

@app.delete("/api/admin/work-schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Gérer Horaires"])
async def delete_work_schedule(
    schedule_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Supprimer un horaire de travail"""
    schedule = db.query(WorkSchedule).filter(WorkSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Horaire non trouvé")
    db.delete(schedule)
    db.commit()

@app.get("/api/admin/alerts", response_model=List[AlertResponse], tags=["Gérer Alertes"])
async def list_alerts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Liste des alertes"""
    alerts = db.query(Alert).offset(skip).limit(limit).order_by(Alert.created_at.desc()).all()
    return alerts

@app.post("/api/admin/check-alerts", tags=["Gérer Alertes"])
async def trigger_alert_check(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Déclencher manuellement la vérification des alertes"""
    check_and_send_absence_alerts(db)
    check_night_vehicle_presence(db)
    return {"message": "Vérification des alertes effectuée"}

# ==================== PARKING ENTRIES (OCR) ====================

@app.post("/api/parking/entries", response_model=ParkingEntryResponse, status_code=status.HTTP_201_CREATED, tags=["Entrées Parking (OCR)"])
async def create_parking_entry(
    entry: ParkingEntryCreate,
    db: Session = Depends(get_db)
):
    """Créer une entrée parking (appelé par le système OCR)"""
    # Vérifier si le véhicule est autorisé
    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == entry.plate_number).first()
    if vehicle and not vehicle.is_authorized:
        # Créer une alerte pour véhicule non autorisé
        if vehicle.employee_id:
            alert = Alert(
                employee_id=vehicle.employee_id,
                vehicle_id=vehicle.id,
                alert_type=AlertTypeEnum.UNAUTHORIZED,
                message=f"Tentative d'entrée avec un véhicule non autorisé: {entry.plate_number}",
                sent_email=False,
                sent_sms=False
            )
            db.add(alert)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Véhicule {entry.plate_number} non autorisé à entrer dans le parking"
        )
    
    db_entry = ParkingEntry(**entry.dict())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # Déclencher la vérification des alertes
    check_and_send_absence_alerts(db)
    check_night_vehicle_presence(db)
    
    return db_entry


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
