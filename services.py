"""
Services pour la gestion des alertes automatiques et des sanctions
"""

from sqlalchemy.orm import Session
from datetime import datetime, date, time, timedelta
from typing import Optional
from models import (
    Employee, Vehicle, WorkSchedule, Alert, Complaint, Sanction, Absence,
    AlertTypeEnum, ComplaintStatusEnum, DayOfWeekEnum, PlateClassEnum,
    AbsenceStatusEnum
)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration email (à configurer selon votre serveur SMTP)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your-email@gmail.com"
SMTP_PASSWORD = "your-password"

# Configuration SMS (à configurer selon votre fournisseur SMS)
SMS_API_URL = "https://api.sms-provider.com/send"
SMS_API_KEY = "your-sms-api-key"


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Envoie un email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False


def send_sms(to_phone: str, message: str) -> bool:
    """Envoie un SMS (implémentation basique - à adapter selon votre fournisseur)"""
    try:
        # TODO: Implémenter l'envoi SMS selon votre fournisseur
        # Exemple avec requests:
        # import requests
        # response = requests.post(SMS_API_URL, json={
        #     "api_key": SMS_API_KEY,
        #     "to": to_phone,
        #     "message": message
        # })
        # return response.status_code == 200
        print(f"SMS envoyé à {to_phone}: {message}")
        return True
    except Exception as e:
        print(f"Erreur envoi SMS: {e}")
        return False


def check_vehicle_presence(db: Session, vehicle: Vehicle, check_time: datetime):
    """
    Vérifie si un véhicule est présent à l'heure prévue
    Retourne True si présent, False sinon
    """
    # Vérifier les entrées parking dans les 30 dernières minutes
    time_threshold = check_time - timedelta(minutes=30)
    
    from models import ParkingEntry
    recent_entry = db.query(ParkingEntry).filter(
        ParkingEntry.plate_number == vehicle.plate_number,
        ParkingEntry.entry_time >= time_threshold,
        ParkingEntry.entry_time <= check_time
    ).first()
    
    return recent_entry is not None


def check_and_send_absence_alerts(db: Session):
    """
    Vérifie les absences et envoie des alertes pour les véhicules non présents
    à l'heure prévue (ex: 9:01 pour les employés de jour)
    """
    now = datetime.now()
    current_time = now.time()
    current_date = now.date()
    current_day = now.strftime("%A").upper()
    
    # Mapper les jours en anglais vers notre enum
    day_mapping = {
        "MONDAY": DayOfWeekEnum.MONDAY,
        "TUESDAY": DayOfWeekEnum.TUESDAY,
        "WEDNESDAY": DayOfWeekEnum.WEDNESDAY,
        "THURSDAY": DayOfWeekEnum.THURSDAY,
        "FRIDAY": DayOfWeekEnum.FRIDAY,
        "SATURDAY": DayOfWeekEnum.SATURDAY,
        "SUNDAY": DayOfWeekEnum.SUNDAY,
    }
    
    current_day_enum = day_mapping.get(current_day)
    if not current_day_enum:
        return
    
    # Récupérer tous les employés actifs avec leurs horaires
    employees = db.query(Employee).filter(Employee.is_active == True).all()
    
    for employee in employees:
        # Récupérer l'horaire pour aujourd'hui
        schedule = db.query(WorkSchedule).filter(
            WorkSchedule.employee_id == employee.id,
            WorkSchedule.day_of_week == current_day_enum
        ).first()
        
        if not schedule or not schedule.start_time:
            continue
        
        # Vérifier si on est à 1 minute après l'heure de début
        start_time = schedule.start_time
        check_time = time(start_time.hour, start_time.minute + 1)
        
        if current_time.hour == check_time.hour and current_time.minute == check_time.minute:
            # Vérifier si l'employé a une absence approuvée
            absence = db.query(Absence).filter(
                Absence.employee_id == employee.id,
                Absence.start_date <= current_date,
                Absence.end_date >= current_date,
                Absence.status == AbsenceStatusEnum.APPROVED
            ).first()
            
            if absence:
                continue  # L'employé est en congé approuvé
            
            # Vérifier les véhicules de l'employé
            vehicles = db.query(Vehicle).filter(Vehicle.employee_id == employee.id).all()
            
            for vehicle in vehicles:
                if not check_vehicle_presence(db, vehicle, now):
                    # Créer une alerte
                    alert = Alert(
                        employee_id=employee.id,
                        vehicle_id=vehicle.id,
                        alert_type=AlertTypeEnum.LATE,
                        message=f"Véhicule {vehicle.plate_number} non présent à {start_time}",
                        sent_email=False,
                        sent_sms=False
                    )
                    db.add(alert)
                    db.flush()
                    
                    # Envoyer email
                    if employee.email:
                        email_sent = send_email(
                            employee.email,
                            f"Alerte - Retard détecté - {vehicle.plate_number}",
                            f"Bonjour {employee.first_name} {employee.last_name},\n\n"
                            f"Votre véhicule {vehicle.plate_number} n'a pas été détecté dans le parking "
                            f"à {start_time}.\n\n"
                            f"Veuillez contacter l'administration si vous avez une justification."
                        )
                        alert.sent_email = email_sent
                    
                    # Envoyer SMS
                    if employee.phone:
                        sms_sent = send_sms(
                            employee.phone,
                            f"ALERTE STEG: Votre véhicule {vehicle.plate_number} n'a pas été détecté à {start_time}"
                        )
                        alert.sent_sms = sms_sent
                    
                    db.commit()


def check_night_vehicle_presence(db: Session):
    """
    Vérifie que les véhicules de classe ÉTAT sont présents la nuit
    """
    now = datetime.now()
    current_hour = now.hour
    
    # Vérifier si on est dans la période de nuit (20h-8h)
    is_night = current_hour >= 20 or current_hour < 8
    
    if not is_night:
        return
    
    # Récupérer tous les véhicules de classe ÉTAT
    etat_vehicles = db.query(Vehicle).filter(
        Vehicle.plate_class == PlateClassEnum.ETAT,
        Vehicle.is_authorized == True
    ).all()
    
    for vehicle in etat_vehicles:
        if vehicle.employee_id:
            employee = db.query(Employee).filter(Employee.id == vehicle.employee_id).first()
            if employee and employee.work_type in ["NIGHT", "BOTH"]:
                # Vérifier la présence dans les 2 dernières heures
                time_threshold = now - timedelta(hours=2)
                
                from models import ParkingEntry
                recent_entry = db.query(ParkingEntry).filter(
                    ParkingEntry.plate_number == vehicle.plate_number,
                    ParkingEntry.entry_time >= time_threshold,
                    ParkingEntry.entry_time <= now
                ).first()
                
                if not recent_entry:
                    # Créer une alerte
                    alert = Alert(
                        employee_id=employee.id,
                        vehicle_id=vehicle.id,
                        alert_type=AlertTypeEnum.ABSENCE,
                        message=f"Véhicule ÉTAT {vehicle.plate_number} absent pendant la nuit",
                        sent_email=False,
                        sent_sms=False
                    )
                    db.add(alert)
                    db.flush()
                    
                    # Envoyer alertes
                    if employee.email:
                        send_email(
                            employee.email,
                            f"Alerte - Véhicule ÉTAT absent la nuit",
                            f"Votre véhicule ÉTAT {vehicle.plate_number} n'a pas été détecté pendant la nuit."
                        )
                        alert.sent_email = True
                    
                    if employee.phone:
                        send_sms(
                            employee.phone,
                            f"ALERTE STEG: Véhicule ÉTAT {vehicle.plate_number} absent la nuit"
                        )
                        alert.sent_sms = True
                    
                    db.commit()


def process_complaint_alert(db: Session, complaint: Complaint):
    """
    Traite une réclamation approuvée : crée une alerte PARKING_VIOLATION pour l'employé accusé.
    Si c'est la 3ème alerte, crée automatiquement une sanction (bannissement 3 jours) et envoie un email.
    """
    # Trouver le véhicule accusé
    accused_vehicle = None
    if complaint.accused_vehicle_id:
        accused_vehicle = db.query(Vehicle).filter(Vehicle.id == complaint.accused_vehicle_id).first()
    elif complaint.accused_vehicle_plate:
        accused_vehicle = db.query(Vehicle).filter(
            Vehicle.plate_number == complaint.accused_vehicle_plate
        ).first()
    
    if not accused_vehicle or not accused_vehicle.employee_id:
        return  # Pas de véhicule trouvé ou pas d'employé associé
    
    employee = db.query(Employee).filter(Employee.id == accused_vehicle.employee_id).first()
    if not employee:
        return
    
    # Créer une alerte PARKING_VIOLATION
    alert = Alert(
        employee_id=employee.id,
        vehicle_id=accused_vehicle.id,
        alert_type=AlertTypeEnum.PARKING_VIOLATION,
        message=f"Occupation de la place de parking n°{complaint.parking_spot} réservée à un collègue (réclamation #{complaint.id})",
        sent_email=False,
        sent_sms=False
    )
    db.add(alert)
    db.flush()
    
    # Envoyer email d'alerte
    if employee.email:
        email_sent = send_email(
            employee.email,
            "Alerte - Occupation de place réservée",
            f"Bonjour {employee.first_name} {employee.last_name},\n\n"
            f"Vous avez reçu une alerte pour avoir occupé la place de parking "
            f"n°{complaint.parking_spot} réservée à un collègue.\n\n"
            f"Votre véhicule : {accused_vehicle.plate_number}\n\n"
            f"Attention : Après 3 alertes, vous serez automatiquement banni du parking pour 3 jours."
        )
        alert.sent_email = email_sent
    
    # Envoyer SMS
    if employee.phone:
        sms_sent = send_sms(
            employee.phone,
            f"ALERTE STEG: Occupation place réservée n°{complaint.parking_spot}. Attention: 3 alertes = sanction 3 jours"
        )
        alert.sent_sms = sms_sent
    
    db.flush()
    
    # Compter les alertes PARKING_VIOLATION pour ce véhicule
    alert_count = db.query(Alert).filter(
        Alert.vehicle_id == accused_vehicle.id,
        Alert.alert_type == AlertTypeEnum.PARKING_VIOLATION
    ).count()
    
    # Si c'est la 3ème alerte, créer une sanction automatique
    if alert_count >= 3:
        # Vérifier s'il n'y a pas déjà une sanction active
        today = date.today()
        existing_sanction = db.query(Sanction).filter(
            Sanction.vehicle_id == accused_vehicle.id,
            Sanction.start_date <= today,
            Sanction.end_date >= today
        ).first()
        
        if not existing_sanction:
            # Créer une sanction de 3 jours
            start_date = date.today()
            end_date = start_date + timedelta(days=3)
            
            sanction = Sanction(
                vehicle_id=accused_vehicle.id,
                reason=f"3 alertes PARKING_VIOLATION reçues. Bannissement automatique pour occupation répétée de places réservées.",
                start_date=start_date,
                end_date=end_date
            )
            db.add(sanction)
            
            # Désautoriser le véhicule
            accused_vehicle.is_authorized = False
            
            # Envoyer email de sanction
            if employee.email:
                send_email(
                    employee.email,
                    "SANCTION - Bannissement du parking (3 alertes reçues)",
                    f"Bonjour {employee.first_name} {employee.last_name},\n\n"
                    f"Vous avez reçu 3 alertes pour occupation de places réservées.\n\n"
                    f"Votre véhicule {accused_vehicle.plate_number} est donc automatiquement banni du parking "
                    f"du {start_date} au {end_date} (3 jours).\n\n"
                    f"Durant cette période, l'accès au parking vous sera refusé.\n\n"
                    f"Cordialement,\nL'administration STEG"
                )
    
    db.commit()


def process_complaint_sanction(db: Session, complaint: Complaint):
    """
    ANCIENNE FONCTION - CONSERVÉE POUR COMPATIBILITÉ
    Cette fonction n'est plus utilisée car le système fonctionne maintenant avec des alertes.
    """
    pass
