from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserFollow
from typing import Optional
from datetime import datetime
import os
from PIL import Image
from .auth import get_current_user, get_optional_user

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
    current_user.phone_number = form.get(
        "phone_number", current_user.phone_number)

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
        {"request": request, "user": current_user,
            "notifications": current_user.notifications}
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
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
    is_edit_mode: bool = False
):
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
    is_own_profile = current_user and current_user.id == user_id

    # Если профиль приватный и это не собственный профиль
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
    is_following = False
    if current_user:
        is_following = any(follow.followed_id ==
                           user_id for follow in current_user.following)

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

# Маршрут для просмотра списка подписчиков пользователя


@router.get("/profile/{user_id}/followers")
async def view_followers(
    user_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Получение пользователя по ID
    user_profile = db.query(User).filter(User.id == user_id).first()
    if not user_profile:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "Пользователь не найден",
                "error_message": "Пользователь, которого вы ищете, не существует.",
                "back_url": "/"
            },
            status_code=404
        )

    # Проверка доступа к профилю (публичный или владелец)
    is_owner = current_user and current_user.id == user_profile.id
    if not user_profile.is_public_profile and not is_owner:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 403,
                "error_title": "Приватный профиль",
                "error_message": "У вас нет доступа к этому профилю.",
                "back_url": "/"
            },
            status_code=403
        )

    # Получение списка подписчиков
    followers = user_profile.followers
    followers_users = [follow.follower for follow in followers]

    return templates.TemplateResponse(
        "users/users_list.html",
        {
            "request": request,
            "current_user": current_user,
            "users": followers_users,
            "user_profile": user_profile,
            "title": f"Подписчики {user_profile.full_name}",
            "empty_message": "У пользователя пока нет подписчиков."
        }
    )

# Маршрут для просмотра списка подписок пользователя


@router.get("/profile/{user_id}/following")
async def view_following(
    user_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Получение пользователя по ID
    user_profile = db.query(User).filter(User.id == user_id).first()
    if not user_profile:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "Пользователь не найден",
                "error_message": "Пользователь, которого вы ищете, не существует.",
                "back_url": "/"
            },
            status_code=404
        )

    # Проверка доступа к профилю (публичный или владелец)
    is_owner = current_user and current_user.id == user_profile.id
    if not user_profile.is_public_profile and not is_owner:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 403,
                "error_title": "Приватный профиль",
                "error_message": "У вас нет доступа к этому профилю.",
                "back_url": "/"
            },
            status_code=403
        )

    # Получение списка подписок
    following = user_profile.following
    following_users = [follow.followed for follow in following]

    return templates.TemplateResponse(
        "users/users_list.html",
        {
            "request": request,
            "current_user": current_user,
            "users": following_users,
            "user_profile": user_profile,
            "title": f"Подписки {user_profile.full_name}",
            "empty_message": "Пользователь пока ни на кого не подписан."
        }
    )

# Маршрут для просмотра списка лайков проекта


@router.get("/projects/{project_id}/likes")
async def view_project_likes(
    project_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    from app.models import Project, ProjectLike

    # Получение проекта по ID
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

    # Проверка доступа к проекту (публичный или владелец)
    is_owner = current_user and current_user.id == project.owner_id
    if not project.is_public and not is_owner:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 403,
                "error_title": "Private Project",
                "error_message": "You don't have access to this project.",
                "back_url": "/projects"
            },
            status_code=403
        )

    # Получение списка пользователей, которые лайкнули проект
    likes = db.query(ProjectLike).filter(
        ProjectLike.project_id == project_id).all()
    users_who_liked = [like.user for like in likes]

    return templates.TemplateResponse(
        "users/likes_list.html",
        {
            "request": request,
            "project": project,
            "users": users_who_liked,
            "current_user": current_user,
            "title": f"Users who liked {project.title}"
        }
    )

# Маршрут для просмотра списка подписчиков


@router.get("/profile/{user_id}/followers")
async def view_followers(
    user_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
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

    # Проверка доступа (публичный профиль или собственный)
    is_own_profile = current_user and current_user.id == user_id
    if not user.is_public_profile and not is_own_profile:
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

    # Получение списка подписчиков
    followers = [follow.follower for follow in user.followers]

    return templates.TemplateResponse(
        "users/users_list.html",
        {
            "request": request,
            "user_profile": user,
            "users": followers,
            "current_user": current_user,
            "title": f"Followers of {user.full_name}",
            "empty_message": "No followers yet."
        }
    )

# Маршрут для просмотра списка подписок


@router.get("/profile/{user_id}/following")
async def view_following(
    user_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
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

    # Проверка доступа (публичный профиль или собственный)
    is_own_profile = current_user and current_user.id == user_id
    if not user.is_public_profile and not is_own_profile:
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

    # Получение списка подписок
    following = [follow.followed for follow in user.following]

    return templates.TemplateResponse(
        "users/users_list.html",
        {
            "request": request,
            "user_profile": user,
            "users": following,
            "current_user": current_user,
            "title": f"Users followed by {user.full_name}",
            "empty_message": "Not following anyone yet."
        }
    )

# API-маршрут для подписки/отписки от пользователя


@router.post("/{user_id}/follow")
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.id == user_id:
        return {"success": False, "message": "Вы не можете подписаться на самого себя"}

    # Проверяем, существует ли пользователь, на которого хотим подписаться
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Импортируем функцию создания уведомлений
    from app.routers.notifications import create_notification

    # Проверяем, подписаны ли мы уже на этого пользователя
    existing_follow = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id,
        UserFollow.followed_id == user_id
    ).first()

    if existing_follow:
        # Отписываемся
        db.delete(existing_follow)
        db.commit()
        return {"status": "success", "message": f"Вы отписались от пользователя {target_user.full_name}", "action": "unfollowed"}
    else:
        # Подписываемся
        new_follow = UserFollow(
            follower_id=current_user.id,
            followed_id=user_id
        )
        db.add(new_follow)

        # Создаем уведомление для пользователя, на которого подписались
        create_notification(
            db=db,
            user_id=user_id,
            notification_type="follow",
            title="Новый подписчик",
            content=f"{current_user.full_name} подписался на вас"
        )

        db.commit()
        return {"status": "success", "message": f"Вы подписались на пользователя {target_user.full_name}", "action": "followed"}
