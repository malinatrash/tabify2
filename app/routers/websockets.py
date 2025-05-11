from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Union
import json

from app.database import get_db
from app.models import Project, MidiFile, Tablature, User
from app.utils.auth import get_current_user_ws

# Создаем роутер для WebSocket
router = APIRouter(prefix="", tags=["websocket"])

# Класс для управления соединениями
class ConnectionManager:
    def __init__(self):
        # Хранилище активных соединений: {project_id -> {client_id -> WebSocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
    
    def add_connection(self, project_id: int, client_id: str, websocket: WebSocket):
        """Добавляет соединение в хранилище"""
        if project_id not in self.active_connections:
            self.active_connections[project_id] = {}
        self.active_connections[project_id][client_id] = websocket
    
    def disconnect(self, project_id: int, client_id: str):
        """Удаляет соединение из хранилища"""
        if project_id in self.active_connections:
            if client_id in self.active_connections[project_id]:
                del self.active_connections[project_id][client_id]
            # Если нет больше соединений для проекта, удаляем проект из хранилища
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
    
    async def broadcast(self, project_id: int, message: dict, exclude_client: Optional[str] = None):
        """Отправляет сообщение всем подключенным клиентам для указанного проекта"""
        if project_id in self.active_connections:
            for client_id, connection in self.active_connections[project_id].items():
                if exclude_client and client_id == exclude_client:
                    continue
                await connection.send_json(message)

# Создаем экземпляр менеджера соединений
connection_manager = ConnectionManager()

@router.websocket("/ws/project/{project_id}/tab/{midi_id}")
async def websocket_tab_endpoint(
    websocket: WebSocket, 
    project_id: int, 
    midi_id: int,
    db: Session = Depends(get_db)
):
    # Получаем client_id из параметров запроса
    client_id = websocket.query_params.get("client_id", f"client_{id(websocket)}")
    await websocket.accept()
    user = None
    
    try:
        # Проверяем доступ к проекту
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            await websocket.close(code=4004, reason="Project not found")
            return
        
        # Проверяем доступ к MIDI файлу
        midi_file = db.query(MidiFile).filter(
            MidiFile.id == midi_id,
            MidiFile.project_id == project_id
        ).first()
        
        if not midi_file:
            await websocket.close(code=4004, reason="MIDI file not found")
            return
        
        # Добавляем соединение в менеджер
        connection_manager.add_connection(project_id, client_id, websocket)
        
        # Отправляем уведомление о подключении нового пользователя
        await connection_manager.broadcast(
            project_id,
            {
                "type": "user_connected",
                "user_id": client_id,
                "midi_id": midi_id
            }
        )
        
        # Обработка сообщений от клиента
        while True:
            data = await websocket.receive_json()
            
            # Определяем тип сообщения
            message_type = data.get("type")
            
            if message_type == "tab_update":
                tab_text = data.get("tab_text")
                midi_id = data.get("midi_id")
                
                # Проверяем наличие табулатуры
                tablature = db.query(Tablature).filter(
                    Tablature.midi_file_id == midi_id
                ).first()
                
                # Обновляем текст табулатуры в базе данных
                if tablature:
                    tablature.tab_text = tab_text
                    tablature.is_edited = True
                    db.commit()
                    
                    # Отправляем обновление всем клиентам, кроме отправителя
                    await connection_manager.broadcast(
                        project_id,
                        {
                            "type": "tab_update",
                            "midi_id": midi_id,
                            "tab_text": tab_text,
                            "sender_id": client_id
                        },
                        exclude_client=client_id
                    )
            
            elif message_type == "ping":
                # Отправляем pong для поддержания соединения
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        # Обрабатываем отключение клиента
        connection_manager.disconnect(project_id, client_id)
        await connection_manager.broadcast(
            project_id,
            {
                "type": "user_disconnected",
                "user_id": client_id,
                "midi_id": midi_id
            }
        )
    except Exception as e:
        # Обрабатываем другие ошибки
        print(f"WebSocket error: {str(e)}")
        connection_manager.disconnect(project_id, client_id)
