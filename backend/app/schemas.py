from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base
import datetime
from datetime import timezone

# --- SQLAlchemy ORM Models with Admin Role ---

class User(Base):
    """
    SQLAlchemy model for the 'users' table.
    UPDATED: Removed the separate notification_email column.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    
    role = Column(String(50), nullable=False, default='user')

    phone_number = Column(String(20), nullable=True)
    telegram_chat_id = Column(String(50), nullable=True)

    telegram_linking_code = Column(String(50), nullable=True, unique=True)
    telegram_linking_code_expires = Column(DateTime, nullable=True)


    cameras = relationship("Camera", back_populates="owner", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="user", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="owner", cascade="all, delete-orphan")


class Camera(Base):
    """
    SQLAlchemy model for the 'cameras' table.
    """
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    video_source = Column(String(255), nullable=False)
    zones = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))

    sensitivity = Column(String(50), default='medium')
    loitering_threshold = Column(Float, default=10.0)
    risk_alert_threshold = Column(Float, default=20.0)

    owner = relationship("User", back_populates="cameras")
    incidents = relationship("Incident", back_populates="camera_config", cascade="all, delete-orphan")


class Incident(Base):
    """
    SQLAlchemy model for the 'incidents' table.
    """
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), nullable=False)
    track_id = Column(Integer, nullable=False)
    risk_score = Column(Float, nullable=False)
    primary_threat = Column(String(100), nullable=False)
    location_x = Column(Integer, nullable=True)
    location_y = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    path_data = Column(Text, nullable=True)
    notification_sent = Column(Boolean, default=False, nullable=False)
    user = relationship("User", back_populates="incidents")
    camera_config = relationship("Camera", back_populates="incidents")
    snapshots = relationship("Snapshot", back_populates="incident", cascade="all, delete-orphan")


class Snapshot(Base):
    """
    SQLAlchemy model for the 'snapshots' table.
    """
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_url = Column(String(512), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="snapshots")
    owner = relationship("User", back_populates="snapshots")