from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from .auth import get_current_user
from typing import Optional
from datetime import datetime
import os
from PIL import Image

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="templates")

# Перенаправление /profile на /profile/{id}
@router.get("/profile")
async def profile_redirect(request: Request, current_user: User = Depends(get_current_user)):
    return RedirectResponse(url=f"/users/profile/{current_user.id}")

@router.post("/profile/{user_id}/update")
async def update_profile(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверка, что пользователь обновляет свой профиль
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
    form = await request.form()
    
    # Обновление информации о пользователе
    current_user.full_name = form.get("full_name", current_user.full_name)
    current_user.phone_number = form.get("phone_number", current_user.phone_number)
    
    # Правильная обработка чекбоксов
    # Если чекбокс отмечен, его значение будет в form, если не отмечен - его не будет
    current_user.is_public_profile = "is_public_profile" in form
    current_user.is_email_notifications_enabled = "is_email_notifications_enabled" in form
    
    db.commit()
    
    # Перенаправляем на страницу профиля с уведомлением об успешном обновлении
    return RedirectResponse(
        url=f"/users/profile/{user_id}",
        status_code=status.HTTP_303_SEE_OTHER,
        headers={
            "HX-Trigger": '{"showToast": {"message": "Profile updated successfully", "type": "success"}}'
        }
    )

@router.post("/profile/{user_id}/avatar")
async def update_avatar(
    user_id: int,
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверка, что пользователь обновляет свою аватарку
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own avatar"
        )
    # Validate file type
    if not avatar.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Создаём директорию static/avatars
    static_dir = "static"
    avatar_dir = os.path.join(static_dir, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    
    # Save and process avatar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"avatar_{current_user.id}_{timestamp}.jpg"
    filepath = os.path.join(avatar_dir, filename)
    
    # Save and resize image
    image = Image.open(avatar.file)
    image.thumbnail((200, 200))  # Resize to maximum dimensions
    
    # Конвертируем RGBA в RGB, если необходимо
    if image.mode == 'RGBA':
        # Создаём новое изображение RGB и смешиваем с белым фоном
        rgb_img = Image.new('RGB', image.size, (255, 255, 255))
        rgb_img.paste(image, mask=image.split()[3])  # 3 - это альфа-канал
        image = rgb_img
    
    image.save(filepath, "JPEG", quality=90)
    
    # Update user avatar URL
    current_user.avatar_url = f"/static/avatars/{filename}"
    db.commit()
    
    return {"message": "Avatar updated successfully"}

@router.get("/notifications")
async def notifications_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "users/notifications.html",
        {"request": request, "user": current_user, "notifications": current_user.notifications}
    )

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notification = next(
        (n for n in current_user.notifications if n.id == notification_id),
        None
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.get("/profile/{user_id}")
async def view_user_profile(
    user_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
    is_edit_mode: bool = False
):
    # Проверка авторизации пользователя
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    # Получение пользователя по ID
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "User Not Found",
                "error_message": "The user you're looking for doesn't exist.",
                "back_url": "/home"
            },
            status_code=404
        )
    
    # Проверка, является ли это собственным профилем или публичным
    is_own_profile = current_user.id == user_id
    if not is_own_profile and not user.is_public_profile:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 403,
                "error_title": "Private Profile",
                "error_message": "This user's profile is private.",
                "back_url": "/home"
            },
            status_code=403
        )
    
    # Получение публичных проектов
    public_projects = [p for p in user.projects if p.is_public]
    
    # Проверка, подписан ли текущий пользователь на просматриваемого
    is_following = any(follow.followed_id == user_id for follow in current_user.following)
    
    return templates.TemplateResponse(
        "users/profile.html",
        {
            "request": request,
            "user": user,
            "is_own_profile": is_own_profile,
            "public_projects": public_projects,
            "is_following": is_following,
            "current_user": current_user,
            "is_edit_mode": is_edit_mode
        }
    )

# Маршрут для редактирования профиля
@router.get("/profile/{user_id}/edit")
async def edit_profile(user_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Редактировать можно только свой профиль
    if current_user.id != user_id:
        return RedirectResponse(url=f"/users/profile/{user_id}")
    
    # Используем тот же обработчик, но с флагом редактирования
    return await view_user_profile(user_id, request, current_user, db, is_edit_mode=True)