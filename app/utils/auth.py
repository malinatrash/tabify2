from fastapi import Depends, HTTPException, status, WebSocket, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Optional, Union
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.database import get_db
from app.models import User
import os
from dotenv import load_dotenv

load_dotenv()

# Получение переменных окружения
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Схема OAuth2 для токенов
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Модели данных
class TokenData(BaseModel):
    email: Optional[str] = None


def verify_password(plain_password, hashed_password):
    """Проверяет соответствие пароля хэшу"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Создает хэш пароля"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT токен доступа"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_email(db: Session, email: str):
    """Получает пользователя по email"""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    """Аутентифицирует пользователя по email и паролю"""
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Получает текущего пользователя по JWT токену"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


# Новая функция для WebSocket аутентификации
async def get_current_user_ws(
    websocket: WebSocket,
    session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Получает текущего пользователя по cookie сессии для WebSocket"""
    if not session:
        return None
    
    try:
        # Извлекаем JWT токен из cookie
        token = session
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        
        # Получаем пользователя
        user = get_user_by_email(db, email=email)
        return user
    except Exception:
        return None
