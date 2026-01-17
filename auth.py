from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
import hashlib

# ==================== CONFIGURATION ====================

SECRET_KEY = "your-secret-key-change-this-in-production-use-env-variable"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)
oauth2_scheme_required = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# ==================== PASSWORD UTILS ====================

def get_password_hash(password: str) -> str:
    """
    Hash sécurisé :
    1) SHA-256 (pas de limite de taille)
    2) bcrypt (sécurisé pour stockage)
    """
    sha_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(sha_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    sha_password = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.verify(sha_password, hashed_password)

# ==================== JWT ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ==================== DATABASE ====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== AUTH ====================

async def get_current_user(
    token: str = Depends(oauth2_scheme_required),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Retourne l'utilisateur si authentifié, None sinon (pour les endpoints publics)
    """
    if token is None:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None

        user = db.query(User).filter(User.username == username).first()
        if user and user.is_active:
            return user

        return None
    except JWTError:
        return None

# ==================== ROLE-BASED PERMISSIONS ====================

def require_role(allowed_roles: list[str]):
    """
    Décorateur pour vérifier les rôles autorisés
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

def require_admin_or_rh(current_user: User = Depends(get_current_active_user)) -> User:
    """Vérifie que l'utilisateur est Admin ou RH"""
    if current_user.role not in ["admin", "rh"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or RH role required"
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Vérifie que l'utilisateur est Admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required"
        )
    return current_user

def require_employee_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    """Vérifie que l'utilisateur est Employee, RH ou Admin"""
    if current_user.role not in ["employee", "rh", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Employee, RH or Admin role required"
        )
    return current_user
