from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie, BackgroundTasks, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Project, ProjectShare, Notification, ProjectLike, MidiFile, Tablature, Comment
from datetime import datetime
from typing import Optional
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta
import re  # Для использования регулярных выражений в валидации time

# Import logging utilities
from app.utils.logger import logger, log_endpoint, log_function
import time
import tempfile
import httpx
from app.routers.auth import get_current_user
from pydantic import BaseModel

class TempoUpdate(BaseModel):
    tempo: int

# Импортируем наш модуль для конвертации MIDI в табулатуру
from app.utils import midi_to_tab
from app.utils.midi_to_tab import midi_to_tablature, get_text, create_empty_tablature
# Импортируем утилиту для валидации табулатуры
from app.utils.tab_validation import validate_tablature_text

# Configure router-specific logger
projects_logger = logger.getChild('projects')

router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory="templates")

# Функция для получения проекта с проверкой доступа


@log_function
def get_project_with_access_check(project_id: int, current_user: User, db: Session, allow_public: bool = True):
    start_time = time.time()
    projects_logger.debug(
        f"Checking access for project_id={project_id}, user_id={getattr(current_user, 'id', None)}, allow_public={allow_public}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        projects_logger.warning(f"Project with id={project_id} not found")
        return None

    # Проверка прав доступа
    has_access = (
        project.owner_id == getattr(current_user, 'id', None) or  # владелец
        # публичный проект, если разрешен просмотр публичных
        (allow_public and project.is_public) or
        (current_user and db.query(ProjectShare).filter(
            ProjectShare.project_id == project_id,
            ProjectShare.shared_email == current_user.email,
            ProjectShare.is_accepted == True
        ).first() is not None)  # доступ через приглашение
    )

    if not has_access:
        projects_logger.warning(
            f"Access denied for user_id={getattr(current_user, 'id', None)} to project_id={project_id}")
        return None

    execution_time = time.time() - start_time
    projects_logger.debug(
        f"Access check completed in {round(execution_time * 1000, 2)}ms: user_id={getattr(current_user, 'id', None)} has access to project_id={project_id}")
    return project


@router.get("/")
@log_endpoint
async def projects_list(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "projects/list.html",
        {"request": request, "user": current_user,
            "projects": current_user.projects}
    )


@router.get("/new")
@log_endpoint
async def new_project_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "projects/new.html",
        {"request": request, "user": current_user}
    )


@router.post("/create")
@log_endpoint
async def create_project(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    form = await request.form()

    # Получаем темп из формы и преобразуем в число
    try:
        tempo = int(form.get("tempo", 120))
        # Проверяем диапазон
        tempo = max(20, min(300, tempo))
    except (ValueError, TypeError):
        # Если не удалось получить значение, используем значение по умолчанию
        tempo = 120
    
    project = Project(
        owner_id=current_user.id,
        title=form.get("title"),
        description=form.get("description"),
        is_public=form.get("is_public") is not None,
        tempo=tempo
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Перенаправляем на страницу проекта
    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)


@router.get("/{project_id}")
@log_endpoint
async def project_detail(
    project_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Используем функцию для проверки доступа. Неавторизованные пользователи могут просматривать публичные проекты
    project = get_project_with_access_check(project_id, current_user, db)

    if not project:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 403 if current_user else 401,
                "error_title": "Доступ запрещен" if current_user else "Требуется авторизация",
                "error_message": "У вас нет доступа к этому проекту." if current_user else "Этот проект приватный. Пожалуйста, авторизуйтесь для доступа.",
                "back_url": "/projects" if current_user else "/login"
            },
            status_code=403 if current_user else 401
        )

    # Получаем MIDI-файлы проекта
    midi_files = db.query(MidiFile).filter(
        MidiFile.project_id == project_id).all()

    # Определяем, является ли пользователь владельцем проекта
    is_owner = current_user and project.owner_id == current_user.id

    # Определяем, лайкнул ли пользователь проект
    has_liked = False
    if current_user:
        like = db.query(ProjectLike).filter(
            ProjectLike.project_id == project_id,
            ProjectLike.user_id == current_user.id
        ).first()
        has_liked = like is not None

    return templates.TemplateResponse(
        "projects/detail.html",
        {
            "request": request,
            "user": current_user,
            "current_user": current_user,  # Добавляем current_user для совместимости с шаблоном
            "project": project,
            "midi_files": midi_files,
            "is_owner": is_owner,
            "is_liked": has_liked  # Переименовываем has_liked в is_liked для соответствия шаблону
        }
    )


@router.post("/{project_id}/share")
@log_endpoint
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
@log_endpoint
async def project_likes(
    project_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Используем функцию для проверки доступа к проекту
    project = get_project_with_access_check(
        project_id, current_user, db, allow_public=True)

    if not project:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "Project not found",
                "error_message": "The project you are looking for does not exist or you don't have access to it.",
                "back_url": "/projects"
            },
            status_code=404
        )

    # Получаем лайки для проекта с детальной информацией
    likes = db.query(ProjectLike).filter(
        ProjectLike.project_id == project_id).order_by(ProjectLike.created_at.desc()).all()

    # Если пользователь авторизован, получаем список пользователей, на которых он подписан
    following_ids = []
    if current_user:
        # Получаем список ID пользователей, на которых подписан текущий пользователь
        followings = db.query(UserFollow).filter(
            UserFollow.follower_id == current_user.id).all()
        following_ids = [follow.followed_id for follow in followings]

    # Проверяем, лайкнул ли текущий пользователь проект
    is_liked = False
    if current_user:
        is_liked = any(like.user_id == current_user.id for like in likes)

    return templates.TemplateResponse(
        "projects/likes_list.html",
        {
            "request": request,
            "current_user": current_user,
            "project": project,
            "likes": likes,  # Передаем сами объекты лайков вместо пользователей
            # ID пользователей, на которых подписан текущий пользователь
            "following_ids": following_ids,
            "is_liked": is_liked,  # Лайкнул ли текущий пользователь проект
            "title": f"Users who liked '{project.title}'"
        }
    )

# Маршрут для загрузки аудиофайла и преобразования в MIDI


@router.post("/{project_id}/upload-audio")
@log_endpoint
async def upload_audio(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем доступ к проекту
    project = get_project_with_access_check(
        project_id, current_user, db, allow_public=False)
    if not project:
        return JSONResponse(
            content={"error": "Проект не найден или у вас нет доступа к нему"},
            status_code=403
        )

    # Проверяем формат файла
    allowed_formats = [".wav", ".mp3", ".ogg", ".flac", ".m4a"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_formats:
        return JSONResponse(
            content={
                "error": f"Неподдерживаемый формат файла. Поддерживаются только: {', '.join(allowed_formats)}"},
            status_code=400
        )

    # Создаем временную директорию для файла
    temp_dir = tempfile.mkdtemp()
    try:
        # Сохраняем файл
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)

        # Отправляем файл на обработку в сервис basic-pitch
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Открываем файл с правильным режимом
                with open(temp_file_path, "rb") as file_data:
                    files = {"file": (file.filename, file_data, "audio/mpeg")}
                    # Добавляем больше информации о запросе для диагностики
                    print(
                        f"Отправка файла {file.filename} на обработку в basic-pitch...")
                    response = await client.post("http://basic-pitch-service:8001/audio-to-midi", files=files)

                print(
                    f"Получен ответ от basic-pitch: статус {response.status_code}")
                if response.status_code != 200:
                    # Попробуем получить детали ошибки
                    try:
                        error_content = response.json() if response.headers.get(
                            "content-type") == "application/json" else {"error": "Ошибка при обработке файла"}
                    except Exception as json_err:
                        error_content = {
                            "error": f"Ошибка при обработке файла: {str(response.content)[:100]}..."}

                    print(
                        f"Ошибка при обработке в basic-pitch: {error_content}")
                    return JSONResponse(
                        content=error_content,
                        status_code=response.status_code
                    )
        except Exception as http_error:
            error_msg = f"Ошибка при отправке запроса к сервису basic-pitch: {str(http_error)}"
            print(error_msg)
            return JSONResponse(
                content={"error": error_msg},
                status_code=500
            )

        # Создаем директорию для MIDI-файлов, если она не существует
        midi_dir = os.path.join("static", "midi")
        os.makedirs(midi_dir, exist_ok=True)

        # Генерируем уникальное имя для файла
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"midi_{project_id}_{now}_{uuid.uuid4().hex[:8]}.mid"
        file_path = os.path.join(midi_dir, filename)

        # Сохраняем MIDI-файл
        with open(file_path, "wb") as f:
            f.write(response.content)

        # Создаем запись в БД
        midi_file = MidiFile(
            project_id=project_id,
            filename=filename,
            original_filename=os.path.splitext(file.filename)[0] + ".mid",
            file_path=file_path
        )

        db.add(midi_file)
        db.commit()
        db.refresh(midi_file)

        # Создаем табулатуру для MIDI-файла
        try:
            # Получаем проект для извлечения темпа
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError("Проект не найден")
            
            # Конвертируем MIDI в табулатуру с учетом темпа проекта
            tablature_data = midi_to_tablature(file_path, project_tempo=project.tempo)
            if not tablature_data:
                raise ValueError("Не удалось создать табулатуру из MIDI файла")

            # Получаем текстовое представление
            tab_text = midi_to_tab.get_text(tablature_data)

            # Создаем запись табулатуры в БД
            tablature = Tablature(
                midi_file_id=midi_file.id,
                tab_data={},  # Пустой JSON, так как теперь используем текстовый формат
                tab_text=tab_text,
            )

            db.add(tablature)
            db.commit()
        except Exception as tab_error:
            print(
                f"Ошибка при конвертации MIDI в табулатуру: {str(tab_error)}")
            # Продолжаем выполнение, так как MIDI файл уже сохранен

        # Добавляем задачу на удаление временных файлов
        background_tasks.add_task(lambda: shutil.rmtree(
            temp_dir) if os.path.exists(temp_dir) else None)

        # Возвращаем результат
        return JSONResponse({
            "id": midi_file.id,
            "filename": midi_file.filename,
            "original_filename": midi_file.original_filename,
            "file_path": f"/static/midi/{midi_file.filename}"
        })

    except Exception as e:
        # В случае ошибки удаляем временные файлы и выводим детальную информацию
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Ошибка при обработке аудиофайла: {str(e)}")
        print(f"Трассировка: {error_traceback}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(
            content={"error": f"Ошибка при обработке аудиофайла: {str(e)}"},
            status_code=500
        )

# Маршрут для получения MIDI-файла


@router.get("/{project_id}/midi/{midi_id}")
@log_endpoint
async def get_midi_file(
    project_id: int,
    midi_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем доступ к проекту (в том числе для неавторизованных пользователей)
    project = get_project_with_access_check(project_id, current_user, db)
    if not project:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 403 if current_user else 401,
                "error_title": "Доступ запрещен" if current_user else "Требуется авторизация",
                "error_message": "У вас нет доступа к этому проекту." if current_user else "Этот проект приватный. Пожалуйста, авторизуйтесь для доступа.",
                "back_url": "/projects" if current_user else "/login"
            },
            status_code=403 if current_user else 401
        )

    # Получаем MIDI-файл
    midi_file = db.query(MidiFile).filter(
        MidiFile.id == midi_id,
        MidiFile.project_id == project_id
    ).first()

    if not midi_file:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_title": "Файл не найден",
                "error_message": "Запрашиваемый MIDI-файл не найден.",
                "back_url": f"/projects/{project_id}"
            },
            status_code=404
        )

    # Возвращаем файл
    return FileResponse(
        path=midi_file.file_path,
        filename=midi_file.original_filename,
        media_type="audio/midi"
    )

# Маршрут для удаления MIDI-файла


@router.post("/{project_id}/midi/{midi_id}/delete")
# Оставляем DELETE для обратной совместимости
@router.delete("/{project_id}/midi/{midi_id}")
@log_endpoint
async def delete_midi_file(
    project_id: int,
    midi_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем, что пользователь имеет права на удаление файла
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        return JSONResponse(
            content={
                "error": "Проект не найден или у вас нет прав для его редактирования"},
            status_code=403
        )

    # Получаем MIDI-файл
    midi_file = db.query(MidiFile).filter(
        MidiFile.id == midi_id,
        MidiFile.project_id == project_id
    ).first()

    if not midi_file:
        return JSONResponse(
            content={"error": "MIDI-файл не найден"},
            status_code=404
        )

    # Удаляем файл с диска
    if os.path.exists(midi_file.file_path):
        os.remove(midi_file.file_path)

    # Удаляем запись из БД
    db.delete(midi_file)
    db.commit()

    return JSONResponse({"success": True})

# Маршруты для работы с табулатурами


@router.get("/{project_id}/midi/{midi_id}/generate-tab")
@log_endpoint
async def generate_tab_page(project_id: int, midi_id: int, request: Request, current_user: Optional[User] = Depends(get_current_user), db: Session = Depends(get_db)):
    """Страница генерации табулатуры из MIDI-файла"""
    # Проверка доступа к проекту
    project = get_project_with_access_check(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Проект не найден или у вас нет к нему доступа")

    # Проверка наличия MIDI-файла
    midi_file = db.query(MidiFile).filter(
        MidiFile.id == midi_id, MidiFile.project_id == project_id).first()
    if not midi_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MIDI-файл не найден")

    # Проверяем, есть ли уже табулатура для этого MIDI
    existing_tab = db.query(Tablature).filter(
        Tablature.midi_file_id == midi_id).first()

    # Если табулатура существует, перенаправляем на её просмотр
    if existing_tab:
        return RedirectResponse(url=f"/projects/{project_id}/midi/{midi_id}/tab/view", status_code=303)

    return templates.TemplateResponse(
        "projects/generate_tab.html",
        {
            "request": request,
            "user": current_user,
            "project": project,
            "midi_file": midi_file
        }
    )


@router.post("/{project_id}/midi/{midi_id}/generate-tab")
@log_endpoint
async def generate_tab(project_id: int, midi_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Генерация табулатуры из MIDI-файла"""
    # Проверка доступа к проекту
    project = get_project_with_access_check(project_id, current_user, db)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Проект не найден или у вас нет к нему доступа"}
        )

    # Проверка наличия MIDI-файла
    midi_file = db.query(MidiFile).filter(
        MidiFile.id == midi_id, MidiFile.project_id == project_id).first()
    if not midi_file:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "MIDI-файл не найден"}
        )

    # Проверяем, есть ли уже табулатура для этого MIDI
    existing_tab = db.query(Tablature).filter(
        Tablature.midi_file_id == midi_id).first()
    if existing_tab:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Табулатура уже существует",
                "redirect_url": f"/projects/{project_id}/midi/{midi_id}/tab/view"
            }
        )

    try:
        # Получаем путь к MIDI-файлу
        midi_path = os.path.join("uploads", "midi", f"{midi_file.filename}")

        # Конвертируем MIDI в табулатуру
        tab_data = convert_midi_to_tab(midi_path)

        # Создаем текстовое представление табулатуры
        tab_text = midi_to_tab.get_text(tab_data)

        # Сохраняем в базу данных
        new_tab = Tablature(
            midi_file_id=midi_id,
            tab_data={},  # Пустой JSON формат, так как теперь используем текстовый формат
            tab_text=tab_text,
            is_edited=False
        )
        db.add(new_tab)
        db.commit()
        db.refresh(new_tab)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Табулатура успешно создана",
                "redirect_url": f"/projects/{project_id}/midi/{midi_id}/tab/view"
            }
        )
    except Exception as e:
        # В случае ошибки возвращаем JSON с описанием ошибки
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Ошибка при генерации табулатуры: {str(e)}"}
        )


@router.get("/{project_id}/midi/{midi_id}/tab")
@log_endpoint
async def view_tab(project_id: int, midi_id: int, request: Request, current_user: Optional[User] = Depends(get_current_user), db: Session = Depends(get_db)):
    """Просмотр табулатуры"""
    # Проверка доступа к проекту
    project = get_project_with_access_check(
        project_id, current_user, db, allow_public=True)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Проект не найден или у вас нет к нему доступа")

    # Проверка наличия MIDI-файла
    midi_file = db.query(MidiFile).filter(
        MidiFile.id == midi_id, MidiFile.project_id == project_id).first()
    if not midi_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MIDI-файл не найден")

    # Проверяем наличие табулатуры
    tablature = db.query(Tablature).filter(
        Tablature.midi_file_id == midi_id).first()
    if not tablature:
        # Если табулатуры нет, перенаправляем на страницу генерации
        return RedirectResponse(url=f"/projects/{project_id}/midi/{midi_id}/tab", status_code=303)

    return templates.TemplateResponse(
        "projects/view_tab.html",
        {
            "request": request,
            "user": current_user,
            "project": project,
            "midi_file": midi_file,
            "tablature": tablature
        }
    )


@router.post("/{project_id}/midi/{midi_id}/tab")
@log_endpoint
async def update_tab(project_id: int, midi_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Обновление табулатуры"""
    # Проверка доступа к проекту (только владелец может редактировать)
    project = db.query(Project).filter(
        Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Только владелец проекта может редактировать табулатуру"}
        )

    # Проверка наличия MIDI и табулатуры
    midi_file = db.query(MidiFile).filter(
        MidiFile.id == midi_id, MidiFile.project_id == project_id).first()
    if not midi_file:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "MIDI-файл не найден"}
        )

    tablature = db.query(Tablature).filter(
        Tablature.midi_file_id == midi_id).first()
    if not tablature:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Табулатура не найдена"}
        )

    try:
        # Получаем данные из запроса
        request_data = await request.json()

        # Получаем текстовое представление табулатуры
        tab_text = request_data.get('tab_text')
        if not tab_text:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Текст табулатуры не указан"}
            )

        # Серверная валидация табулатуры с использованием регулярных выражений
        validation_result = validate_tablature_text(
            tab_text, tablature.tab_text)
        if not validation_result["valid"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": f"Ошибка валидации табулатуры: {validation_result['error']}"}
            )

        # Обновляем данные табулатуры
        tablature.tab_text = tab_text
        tablature.is_edited = True
        tablature.last_edited_at = datetime.utcnow()

        db.commit()
        db.refresh(tablature)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Табулатура успешно обновлена"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Ошибка при обновлении табулатуры: {str(e)}"}
        )


@router.post("/{project_id}/create-empty-tab", response_model=dict)
@log_endpoint
async def create_empty_tab(
    project_id: int,
    tab_width: int = Form(80),  # Ширина табулатуры по умолчанию 80 символов
    midi_name: str = Form(...),  # Название для MIDI файла
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создает пустую табулатуру без загрузки аудиофайла.
    """
    # Проверяем доступ к проекту
    project = get_project_with_access_check(
        project_id, current_user, db, allow_public=False)
    if not project:
        return JSONResponse(
            content={"error": "Проект не найден или у вас нет доступа к нему"},
            status_code=403
        )
    
    try:
        # Создаем директорию для MIDI файлов, если она не существует
        midi_dir = os.path.join("static", "midi")
        os.makedirs(midi_dir, exist_ok=True)

        # Генерируем уникальное имя для файла
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"empty_{project_id}_{now}_{uuid.uuid4().hex[:8]}.mid"
        file_path = os.path.join(midi_dir, filename)

        # Создаем пустой MIDI файл (minimal MIDI file)
        with open(file_path, 'wb') as f:
            # Создаем минимальный пустой MIDI файл
            # MThd (header)
            f.write(bytes.fromhex('4D546864000000060001000100F00490'))
            # MTrk (empty track)
            f.write(bytes.fromhex('4D54726B0000000600FF2F00'))

        # Создаем запись в БД
        midi_file = MidiFile(
            project_id=project_id,
            filename=filename,
            original_filename=midi_name + ".mid",
            file_path=file_path
        )

        db.add(midi_file)
        db.commit()
        db.refresh(midi_file)

        # Создаем пустую табулатуру
        tab_text = create_empty_tablature(tab_width)

        # Создаем запись табулатуры в БД
        tablature = Tablature(
            midi_file_id=midi_file.id,
            tab_data={},  # Пустой JSON, так как используем текстовый формат
            tab_text=tab_text,
            is_edited=True  # Помечаем как отредактированную, чтобы не перегенерировалась
        )

        db.add(tablature)
        db.commit()

        return JSONResponse({
            "id": midi_file.id,
            "filename": midi_file.filename,
            "original_filename": midi_file.original_filename,
            "file_path": f"/static/midi/{midi_file.filename}"
        })

    except Exception as e:
        db.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Ошибка при создании пустой табулатуры: {str(e)}")
        print(f"Трассировка: {error_traceback}")
        return JSONResponse(
            content={
                "error": f"Ошибка при создании пустой табулатуры: {str(e)}"
            },
            status_code=500
        )

@router.post("/{project_id}/update-tempo", response_model=dict)
async def update_project_tempo(
    project_id: int,
    tempo_data: TempoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновление темпа проекта
    """
    # Получаем проект
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )
    
    # Проверяем права доступа (только владелец может менять темп)
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для изменения темпа проекта"
        )
    
    # Проверяем корректность темпа
    if tempo_data.tempo < 20 or tempo_data.tempo > 300:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Темп должен быть в диапазоне от 20 до 300 BPM"
        )
    
    try:
        # Обновляем темп проекта
        project.tempo = tempo_data.tempo
        db.commit()
        
        # Теперь нужно обновить все табулатуры в проекте
        # Получаем все MIDI файлы проекта
        midi_files = db.query(MidiFile).filter(MidiFile.project_id == project_id).all()
        
        # Для каждого MIDI файла перегенерируем табулатуру с новым темпом
        for midi_file in midi_files:
            # Получаем существующую табулатуру
            tablature = db.query(Tablature).filter(Tablature.midi_file_id == midi_file.id).first()
            if tablature and not tablature.is_edited:  # Только для неотредактированных табулатур
                try:
                    # Генерируем новую табулатуру с учетом нового темпа
                    tablature_data = midi_to_tablature(midi_file.file_path, project_tempo=project.tempo)
                    if tablature_data:
                        # Обновляем текстовое представление
                        tab_text = midi_to_tab.get_text(tablature_data)
                        tablature.tab_text = tab_text
                        db.commit()
                except Exception as tab_error:
                    # Логируем ошибку, но продолжаем работу
                    print(f"Ошибка при обновлении табулатуры: {str(tab_error)}")
        
        return {"message": "Темп проекта успешно обновлен", "tempo": project.tempo}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении темпа: {str(e)}"
        )


# API-маршрут для лайка проекта
@router.post("/{project_id}/like")
@log_endpoint
async def like_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем, существует ли проект
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    # Проверяем, есть ли уже лайк от этого пользователя
    existing_like = db.query(ProjectLike).filter(
        ProjectLike.project_id == project_id,
        ProjectLike.user_id == current_user.id
    ).first()

    # Импортируем функцию создания уведомлений
    from app.routers.notifications import create_notification

    if existing_like:
        # Если лайк уже существует, удаляем его (отменяем лайк)
        db.delete(existing_like)
        db.commit()
        return {"status": "success", "message": "Лайк удален", "action": "unliked", "likes_count": len(project.likes) - 1}
    else:
        # Создаем новый лайк
        new_like = ProjectLike(
            project_id=project_id,
            user_id=current_user.id,
        )
        db.add(new_like)

        # Добавляем уведомление владельцу проекта, если он не является тем, кто лайкнул
        if project.owner_id != current_user.id:
            create_notification(
                db=db,
                user_id=project.owner_id,
                notification_type="like",
                title="Новый лайк",
                content=f"{current_user.full_name} оценил ваш проект '{project.title}'"
            )

        db.commit()
        return {"status": "success", "message": "Лайк добавлен", "action": "liked", "likes_count": len(project.likes) + 1}


# Маршрут для получения комментариев к проекту
@router.get("/{project_id}/comments")
@log_endpoint
async def get_project_comments(
    project_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем доступ к проекту
    project = get_project_with_access_check(
        project_id, current_user, db, allow_public=True)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Проект не найден или у вас нет к нему доступа"}
        )

    # Получаем комментарии к проекту
    comments = db.query(Comment).filter(
        Comment.project_id == project_id).order_by(Comment.created_at).all()

    # Преобразуем комментарии в формат для JSON
    comments_data = [{
        "id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat(),
        "user": {
            "id": comment.user.id,
            "full_name": comment.user.full_name,
            "avatar_url": comment.user.avatar_url
        }
    } for comment in comments]

    return JSONResponse(content=comments_data)


# Маршрут для добавления комментария к проекту
@router.post("/{project_id}/comments")
@log_endpoint
async def add_project_comment(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем доступ к проекту
    project = get_project_with_access_check(project_id, current_user, db)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Проект не найден или у вас нет к нему доступа"}
        )

    # Получаем данные комментария из запроса
    try:
        data = await request.json()
        content = data.get("content")

        if not content or not content.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Содержание комментария не может быть пустым"}
            )

        # Создаем новый комментарий
        comment = Comment(
            project_id=project_id,
            user_id=current_user.id,
            content=content
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)

        # Добавляем уведомление владельцу проекта, если он не является автором комментария
        from app.routers.notifications import create_notification
        if project.owner_id != current_user.id:
            create_notification(
                db=db,
                user_id=project.owner_id,
                notification_type="comment",
                title="Новый комментарий",
                content=f"{current_user.full_name} оставил комментарий к вашему проекту '{project.title}'"
            )

        # Возвращаем данные созданного комментария
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "user": {
                    "id": current_user.id,
                    "full_name": current_user.full_name,
                    "avatar_url": current_user.avatar_url
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Ошибка при добавлении комментария: {str(e)}"}
        )
