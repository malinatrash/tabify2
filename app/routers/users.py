from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
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

@router.get("/profile")
@router.get("/profile/edit")
async def edit_profile_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "users/profile.html",
        {"request": request, "user": current_user, "is_own_profile": True}
    )

@router.post("/profile/update")
async def update_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    form = await request.form()
    
    # Update user information
    current_user.full_name = form.get("full_name", current_user.full_name)
    current_user.phone_number = form.get("phone_number", current_user.phone_number)
    current_user.is_public_profile = form.get("is_public_profile", "false").lower() == "true"
    current_user.is_email_notifications_enabled = form.get("is_email_notifications_enabled", "true").lower() == "true"
    
    db.commit()
    return templates.TemplateResponse(
        "users/profile.html",
        {
            "request": request,
            "user": current_user,
            "toast": {
                "message": "Profile updated successfully",
                "type": "success"
            }
        }
    )

@router.post("/profile/avatar")
async def update_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    if not avatar.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    avatar_dir = os.path.join(upload_dir, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    
    # Save and process avatar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"avatar_{current_user.id}_{timestamp}.jpg"
    filepath = os.path.join(avatar_dir, filename)
    
    # Save and resize image
    image = Image.open(avatar.file)
    image.thumbnail((200, 200))  # Resize to maximum dimensions
    image.save(filepath, "JPEG")
    
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    
    # Check if profile is public or if it's the current user
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
    
    # Get public projects
    public_projects = [p for p in user.projects if p.is_public]
    
    # Check if current user is following this user
    is_following = any(follow.followed_id == user_id for follow in current_user.following)
    
    return templates.TemplateResponse(
        "users/profile.html",
        {
            "request": request,
            "user": user,
            "is_own_profile": is_own_profile,
            "public_projects": public_projects,
            "is_following": is_following,
            "current_user": current_user
        }
    )