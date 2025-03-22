from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Project, ProjectShare, Notification, ProjectLike
from .auth import get_current_user
from datetime import datetime
from typing import Optional
import os
import secrets

router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory="templates")

# Функция для получения проекта с проверкой доступа
def get_project_with_access_check(project_id: int, current_user: User, db: Session, allow_public: bool = True):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
        
    # Проверка прав доступа
    has_access = (
        project.owner_id == getattr(current_user, 'id', None) or  # владелец
        (allow_public and project.is_public) or  # публичный проект, если разрешен просмотр публичных
        (current_user and db.query(ProjectShare).filter(
            ProjectShare.project_id == project_id,
            ProjectShare.shared_email == current_user.email,
            ProjectShare.is_accepted == True
        ).first() is not None)  # доступ через приглашение
    )
    
    if not has_access:
        return None
        
    return project

@router.get("/")
async def projects_list(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "projects/list.html",
        {"request": request, "user": current_user, "projects": current_user.projects}
    )

@router.get("/new")
async def new_project_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "projects/new.html",
        {"request": request, "user": current_user}
    )

@router.post("/create")
async def create_project(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    form = await request.form()
    
    project = Project(
        owner_id=current_user.id,
        title=form.get("title"),
        description=form.get("description"),
        is_public=form.get("is_public") is not None
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return {"message": "Project created successfully", "project_id": project.id}

@router.get("/{project_id}")
async def project_detail(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "Project Not Found",
                "error_message": "The project you're looking for doesn't exist.",
                "back_url": "/projects"
            },
            status_code=404
        )
        
    # Check access rights
    if project.owner_id != current_user.id and not project.is_public:
        shared = db.query(ProjectShare).filter(
            ProjectShare.project_id == project_id,
            ProjectShare.shared_email == current_user.email,
            ProjectShare.is_accepted == True
        ).first()
        if not shared:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error_code": 403,
                    "error_title": "Access Denied",
                    "error_message": "You don't have permission to access this project.",
                    "back_url": "/projects"
                },
                status_code=403
            )
    
    return templates.TemplateResponse(
        "projects/detail.html",
        {"request": request, "user": current_user, "project": project}
    )

@router.post("/{project_id}/share")
async def share_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    form = await request.form()
    shared_email = form.get("email")
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create project share
    share = ProjectShare(
        project_id=project.id,
        shared_email=shared_email,
        access_token=secrets.token_urlsafe(32)
    )
    
    # Create notification for shared user
    notification = Notification(
        user_id=current_user.id,
        type="project_invitation",
        title=f"Project Invitation: {project.title}",
        content=f"{current_user.full_name} has invited you to collaborate on project {project.title}"
    )
    
    db.add(share)
    db.add(notification)
    db.commit()
    
    return {"message": "Project shared successfully"}

@router.get("/{project_id}/likes")
async def project_likes(
    project_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Используем функцию для проверки доступа к проекту
    project = get_project_with_access_check(project_id, current_user, db, allow_public=True)
    
    if not project:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "Проект не найден",
                "error_message": "Проект, который вы ищете, не существует или у вас нет доступа к нему.",
                "back_url": "/projects"
            },
            status_code=404
        )
    
    # Получаем пользователей, которые лайкнули проект
    likes = db.query(ProjectLike).filter(ProjectLike.project_id == project_id).all()
    users = [like.user for like in likes]
    
    return templates.TemplateResponse(
        "users/likes_list.html",
        {
            "request": request, 
            "current_user": current_user, 
            "users": users,
            "project": project,
            "title": f"Пользователи, оценившие проект '{project.title}'"
        }
    )