from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models
from app.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api", tags=["social"])

@router.post("/projects/{project_id}/like")
async def like_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_like = db.query(models.ProjectLike).filter(
        models.ProjectLike.project_id == project_id,
        models.ProjectLike.user_id == current_user.id
    ).first()

    if existing_like:
        db.delete(existing_like)
        db.commit()
        return {"message": "Project unliked successfully"}

    new_like = models.ProjectLike(
        project_id=project_id,
        user_id=current_user.id
    )
    db.add(new_like)
    db.commit()
    db.refresh(new_like)
    return {"message": "Project liked successfully"}

@router.post("/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself"
        )

    user_to_follow = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_follow:
        raise HTTPException(status_code=404, detail="User not found")

    existing_follow = db.query(models.UserFollow).filter(
        models.UserFollow.follower_id == current_user.id,
        models.UserFollow.followed_id == user_id
    ).first()

    if existing_follow:
        db.delete(existing_follow)
        db.commit()
        return {"message": "User unfollowed successfully"}

    new_follow = models.UserFollow(
        follower_id=current_user.id,
        followed_id=user_id
    )
    db.add(new_follow)
    db.commit()
    db.refresh(new_follow)
    return {"message": "User followed successfully"}

@router.get("/users/{user_id}/followers", response_model=List[dict])
async def get_user_followers(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    followers = [
        {
            "id": follow.follower.id,
            "full_name": follow.follower.full_name,
            "email": follow.follower.email
        }
        for follow in user.followers
    ]
    return followers

@router.get("/users/{user_id}/following", response_model=List[dict])
async def get_user_following(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    following = [
        {
            "id": follow.followed.id,
            "full_name": follow.followed.full_name,
            "email": follow.followed.email
        }
        for follow in user.following
    ]
    return following