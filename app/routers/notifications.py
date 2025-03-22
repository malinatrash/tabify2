from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models import Notification, User
from .auth import get_current_user

# Pydantic схема для сериализации уведомлений
class NotificationSchema(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    content: str
    is_read: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/", response_model=dict)
async def get_notifications(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """Получить уведомления пользователя с пагинацией."""
    total = db.query(Notification).filter(Notification.user_id == current_user.id).count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    
    # Преобразуем ORM-модели в схемы Pydantic для сериализации
    notification_schemas = [NotificationSchema.model_validate(n) for n in notifications]
    
    return {
        "total": total,
        "unread_count": unread_count,
        "notifications": notification_schemas
    }

@router.post("/{notification_id}/mark-read", response_model=dict)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметить уведомление как прочитанное."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"status": "success", "message": "Notification marked as read"}

@router.post("/mark-all-read", response_model=dict)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметить все уведомления как прочитанные."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"status": "success", "message": "All notifications marked as read"}

def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    content: str
):
    """Создать новое уведомление."""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        content=content
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification
