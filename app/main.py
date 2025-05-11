from app.routers import auth, users, projects, notifications, premium, websockets
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.database import engine, get_db
from app.models import Base, User, Project
from sqlalchemy.orm import Session
from os import getenv
from dotenv import load_dotenv
import time
from app.utils.logger import logger, log_endpoint, log_function, log_middleware_timing
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

load_dotenv()

logger.info("Loading environment variables")

# Create database tables
logger.info("Creating database tables")
Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

# Initialize FastAPI application
app = FastAPI(title="Tabify")

# Create a logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Add request ID to request state for tracking
        request.state.request_id = str(uuid.uuid4())
        
        # Log request details
        logger.info(f"REQUEST START: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log response details
            execution_time = time.time() - start_time
            logger.info(f"REQUEST END: {request.method} {request.url.path} - Status: {response.status_code} - Time: {round(execution_time * 1000, 2)}ms")
            
            return response
        except Exception as e:
            # Log exceptions
            execution_time = time.time() - start_time
            logger.error(f"REQUEST ERROR: {request.method} {request.url.path} - {type(e).__name__}: {str(e)} - Time: {round(execution_time * 1000, 2)}ms")
            # Re-raise the exception
            raise

# Add middleware in order (first added = outermost in request processing)
app.add_middleware(LoggingMiddleware)

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

# Log application startup
logger.info("Tabify application starting up")

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
@log_endpoint
async def landing_page(request: Request, db: Session = Depends(get_db)):
    start_time = time.time()
    logger.debug(f"Landing page accessed from {request.client.host if request.client else 'unknown'} with session: {request.session.get('user_id')}")    
    
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            logger.info(f"User {user_id} redirected to home page")
            return RedirectResponse(url="/home")

    execution_time = time.time() - start_time
    logger.debug(f"Landing page rendered in {round(execution_time * 1000, 2)}ms")
    
    return templates.TemplateResponse(
        "landing.html",
        {"request": request}
    )

# Include routers
# Регистрируем все маршруты
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(notifications.router)
app.include_router(premium.router)

# Отдельно регистрируем WebSocket маршруты
app.include_router(websockets.router)

# Выводим все зарегистрированные маршруты
for route in app.routes:
    logger.info(f"Registered route: {route.path} [{','.join(route.methods) if hasattr(route, 'methods') else 'WebSocket'}]")


# Home page route


@app.get("/home")
@log_endpoint
async def home_page(request: Request, db: Session = Depends(get_db)):
    start_time = time.time()
    logger.debug(f"Home page accessed from {request.client.host if request.client else 'unknown'} with session: {request.session.get('user_id')}")
    
    user_id = request.session.get("user_id")
    if not user_id:
        logger.info("Unauthenticated user redirected to login page")
        return RedirectResponse(url="/auth/login")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Session user_id {user_id} not found in database")
        return RedirectResponse(url="/auth/login")

    query_start = time.time()
    # Get user's projects
    projects = db.query(Project).filter(Project.owner_id == user_id).all()
    logger.debug(f"Retrieved {len(projects)} projects for user {user_id} in {round((time.time() - query_start) * 1000, 2)}ms")

    query_start = time.time()
    # Get popular projects (sorted by likes count)
    popular_projects = (
        db.query(Project)
        .filter(Project.is_public == True)
        .all()
    )
    popular_projects.sort(key=lambda x: len(x.likes), reverse=True)
    logger.debug(f"Retrieved {len(popular_projects)} popular projects in {round((time.time() - query_start) * 1000, 2)}ms")

    query_start = time.time()
    # Получаем популярных пользователей (по количеству подписчиков)
    all_users = db.query(User).filter(User.id != user_id,
                                      User.is_public_profile == True).all()
    # Сортируем по количеству подписчиков
    popular_users = sorted(all_users, key=lambda x: len(
        x.followers), reverse=True)[:5]
    logger.debug(f"Retrieved {len(all_users)} users and selected top {len(popular_users)} popular users in {round((time.time() - query_start) * 1000, 2)}ms")

    execution_time = time.time() - start_time
    logger.info(f"Home page rendered for user {user_id} in {round(execution_time * 1000, 2)}ms")
    
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
@log_endpoint
async def not_found_handler(request: Request, exc: HTTPException):
    logger.warning(f"404 Not Found: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
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
@log_endpoint
async def unauthorized_handler(request: Request, exc: HTTPException):
    logger.warning(f"401 Unauthorized: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
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
