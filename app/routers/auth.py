from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from app.database import get_db
from app.models import User
from os import getenv
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")

# Security configuration
SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Helper functions


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = token.split(" ")[1]
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
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Функция для получения текущего пользователя, но без требования авторизации


async def get_optional_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return None

    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.email == email).first()
    return user

# Routes


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request}
    )


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request}
    )


@router.api_route("/logout", methods=["GET", "POST"])
async def logout(request: Request):
    if request.method not in ["GET", "POST"]:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 405,
                "error_title": "Method Not Allowed",
                "error_message": "The method is not allowed for this endpoint.",
                "back_url": "/"
            },
            status_code=405
        )
    response = RedirectResponse(
        url="/auth/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    request.session.clear()
    return response


@router.post("/token")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Incorrect email or password"}
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    user.last_login = datetime.utcnow()
    db.commit()

    response = RedirectResponse(url="/home", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token",
                        value=f"Bearer {access_token}", httponly=True)
    request.session["user_id"] = user.id
    return response


@router.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    # Check if user already exists
    if db.query(User).filter(User.email == form.get("email")).first():
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Email already registered"}
        )

    # Create new user
    user = User(
        email=form.get("email"),
        hashed_password=get_password_hash(form.get("password")),
        full_name=form.get("full_name"),
        phone_number=form.get("phone_number"),
        is_public_profile=form.get("is_public_profile") == "on"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create access token and redirect to home
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/home", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token",
                        value=f"Bearer {access_token}", httponly=True)
    request.session["user_id"] = user.id
    return response
