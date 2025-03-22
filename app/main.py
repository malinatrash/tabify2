from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from .database import engine, get_db
from .models import Base, User, Project
from sqlalchemy.orm import Session
from os import getenv
from dotenv import load_dotenv

load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tabify")

# Configure Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=getenv("SECRET_KEY"),
    session_cookie="session"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates configuration
templates = Jinja2Templates(directory="templates")

# Добавляем пользовательские фильтры для Jinja2
def dateformat(date):
    if date is None:
        return ""
    if isinstance(date, str):
        from datetime import datetime
        try:
            date = datetime.fromisoformat(date)
        except ValueError:
            return date
    return date.strftime("%d.%m.%Y %H:%M")

templates.env.filters["dateformat"] = dateformat

# Landing page route
@app.get("/")
async def landing_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return RedirectResponse(url="/home")
    
    return templates.TemplateResponse(
        "landing.html",
        {"request": request}
    )

# Include routers
from .routers import auth, users, projects
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)

# Home page route
@app.get("/home")
async def home_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/auth/login")
    
    # Get user's projects
    projects = db.query(Project).filter(Project.owner_id == user_id).all()
    
    # Get popular projects (sorted by likes count)
    popular_projects = (
        db.query(Project)
        .filter(Project.is_public == True)
        .all()
    )
    popular_projects.sort(key=lambda x: len(x.likes), reverse=True)
    
    # Получаем популярных пользователей (по количеству подписчиков)
    all_users = db.query(User).filter(User.id != user_id, User.is_public_profile == True).all()
    # Сортируем по количеству подписчиков
    popular_users = sorted(all_users, key=lambda x: len(x.followers), reverse=True)[:5]
        
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request, 
            "user": user, 
            "projects": projects, 
            "popular_projects": popular_projects,
            "popular_users": popular_users
        }
    )

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 404,
            "error_title": "Page Not Found",
            "error_message": "The page you're looking for doesn't exist."
        },
        status_code=404
    )

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 401,
            "error_title": "Unauthorized",
            "error_message": "Please log in to access this page.",
            "back_url": "/auth/login"
        },
        status_code=401
    )