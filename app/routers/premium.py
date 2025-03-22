from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Subscription, SubscriptionPlan
from datetime import datetime, timedelta
from .auth import get_current_user
import json
from typing import Optional

router = APIRouter(tags=["premium"])
templates = Jinja2Templates(directory="templates")

@router.get("/premium")
async def premium_page(request: Request, current_user: User = Depends(get_current_user)):
    """Отображение страницы премиум-подписки"""
    
    user_dict = current_user.__dict__.copy()
    
    # Используем ту же логику, что и в premium_status
    is_premium = False
    if hasattr(current_user, 'active_subscription') and current_user.active_subscription:
        if current_user.active_subscription.status == "active" and current_user.active_subscription.end_date > datetime.utcnow():
            is_premium = True
    
    user_dict['is_premium'] = is_premium
    
    return templates.TemplateResponse(
        "premium/index.html",
        {"request": request, "user": user_dict}
    )

@router.post("/premium/activate-demo")
async def activate_premium_demo(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Эмуляция активации премиум-подписки"""
    try:
        data = await request.json()
        plan_type = data.get("plan")
        
        # Проверяем существование премиум-плана, создаем если нет
        plan = db.query(SubscriptionPlan).filter_by(id=1).first()
        if not plan:
            # Создаем демо-планы подписки, если они не существуют
            monthly_plan = SubscriptionPlan(
                id=1,
                duration_months=1,
                price_per_month=599.0,
                description="Месячный",
                features="Все премиум-функции, 20 ГБ хранилища"
            )
            db.add(monthly_plan)
            
            yearly_plan = SubscriptionPlan(
                id=2,
                duration_months=12,
                price_per_month=416.0,
                description="Годовой",
                features="Все премиум-функции, 50 ГБ хранилища, приоритетная поддержка"
            )
            db.add(yearly_plan)
            
            lifetime_plan = SubscriptionPlan(
                id=3,
                duration_months=999,  # "Пожизненный"
                price_per_month=14999.0 / 999,  # Просто для представления
                description="Пожизненный",
                features="Все премиум-функции, 100 ГБ хранилища, ранний доступ к новым функциям"
            )
            db.add(lifetime_plan)
            db.commit()
            
            # Получаем созданный план
            plan = db.query(SubscriptionPlan).filter_by(id=1).first()
        
        # Определяем выбранный план и длительность
        plan_id = 1  # По умолчанию месячный
        if plan_type == "yearly":
            plan_id = 2
        elif plan_type == "lifetime":
            plan_id = 3
        
        selected_plan = db.query(SubscriptionPlan).filter_by(id=plan_id).first()
        
        # Проверяем, есть ли уже активная подписка
        existing_subscription = db.query(Subscription).filter_by(user_id=current_user.id).first()
        
        if existing_subscription:
            # Обновляем существующую подписку
            existing_subscription.plan_id = plan_id
            existing_subscription.start_date = datetime.utcnow()
            existing_subscription.end_date = datetime.utcnow() + timedelta(days=30 * selected_plan.duration_months)
            existing_subscription.status = "active"
        else:
            # Создаем новую подписку
            new_subscription = Subscription(
                user_id=current_user.id,
                plan_id=plan_id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30 * selected_plan.duration_months),
                status="active"
            )
            db.add(new_subscription)
        
        db.commit()
        
        return JSONResponse({"success": True, "message": "Подписка успешно активирована"})
    
    except Exception as e:
        print(f"Ошибка при активации подписки: {str(e)}")
        return JSONResponse({"success": False, "message": "Произошла ошибка при активации подписки"}, status_code=500)

@router.get("/premium/check")
async def check_premium_status(current_user: User = Depends(get_current_user)):
    """Проверка статуса премиум-подписки"""
    if hasattr(current_user, 'active_subscription') and current_user.active_subscription:
        if current_user.active_subscription.status == "active" and current_user.active_subscription.end_date > datetime.utcnow():
            return {"is_premium": True}
    
    return {"is_premium": False}

@router.get("/premium/status")
async def premium_status(current_user: User = Depends(get_current_user)):
    """Возвращает статус премиум-подписки для обновления интерфейса"""
    if hasattr(current_user, 'active_subscription') and current_user.active_subscription:
        if current_user.active_subscription.status == "active" and current_user.active_subscription.end_date > datetime.utcnow():
            return {"is_premium": True}
    
    return {"is_premium": False}
