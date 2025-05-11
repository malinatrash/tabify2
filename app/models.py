from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Float, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    phone_number = Column(String)
    avatar_url = Column(String, nullable=True)
    is_email_verified = Column(Boolean, default=False)
    is_email_notifications_enabled = Column(Boolean, default=True)
    is_public_profile = Column(Boolean, default=False)
    last_login = Column(DateTime, default=datetime.utcnow)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    active_subscription = relationship(
        "Subscription", back_populates="user", uselist=False)
    projects = relationship("Project", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")
    liked_projects = relationship("ProjectLike", back_populates="user")
    followers = relationship(
        "UserFollow", foreign_keys="UserFollow.followed_id", back_populates="followed")
    following = relationship(
        "UserFollow", foreign_keys="UserFollow.follower_id", back_populates="follower")
    comments = relationship("Comment", back_populates="user")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    duration_months = Column(Integer)
    price_per_month = Column(Float)
    description = Column(Text)
    features = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String)  # active, expired, cancelled
    payment_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    user = relationship("User", back_populates="active_subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    tempo = Column(Integer, default=120)  # Единый темп для всего проекта (BPM)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    shared_users = relationship("ProjectShare", back_populates="project")
    midi_files = relationship("MidiFile", back_populates="project")

    likes = relationship("ProjectLike", back_populates="project")
    comments = relationship("Comment", back_populates="project")


class ProjectShare(Base):
    __tablename__ = "project_shares"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    shared_email = Column(String)
    access_token = Column(String, unique=True)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="shared_users")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)  # project_invitation, system_notification, etc.
    title = Column(String)
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class ProjectLike(Base):
    __tablename__ = "project_likes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="likes")
    user = relationship("User", back_populates="liked_projects")


class UserFollow(Base):
    __tablename__ = "user_follows"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"))
    followed_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    follower = relationship("User", foreign_keys=[
                            follower_id], back_populates="following")
    followed = relationship("User", foreign_keys=[
                            followed_id], back_populates="followers")


class MidiFile(Base):
    __tablename__ = "midi_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    filename = Column(String)
    original_filename = Column(String)
    file_path = Column(String)  # путь к файлу MIDI
    midi_data = Column(JSON, nullable=True)  # данные о нотах, аккордах и т.д.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="midi_files")
    tablatures = relationship("Tablature", back_populates="midi_file")


class Tablature(Base):
    __tablename__ = "tablatures"

    id = Column(Integer, primary_key=True, index=True)
    midi_file_id = Column(Integer, ForeignKey("midi_files.id"))
    tab_data = Column(JSON, nullable=False)  # Данные табулатуры в JSON формате
    # Текстовое представление табулатуры
    tab_text = Column(Text, nullable=True)
    # Была ли табулатура отредактирована
    is_edited = Column(Boolean, default=False)
    # Время последнего редактирования
    last_edited_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    midi_file = relationship("MidiFile", back_populates="tablatures")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="comments")
    user = relationship("User", back_populates="comments")
