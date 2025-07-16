from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- Enums for Roles and Settings ---
class UserRoleEnum(str, Enum):
    user = 'user'
    admin = 'admin'

class SensitivityEnum(str, Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'

# --- Snapshot Models ---
class SnapshotBase(BaseModel):
    image_url: str
    timestamp: datetime

class SnapshotCreate(SnapshotBase):
    pass

class Snapshot(SnapshotBase):
    id: int
    incident_id: int
    owner_id: int
    model_config = ConfigDict(from_attributes=True)


# --- Camera Models ---
class CameraSettingsUpdate(BaseModel):
    sensitivity: Optional[SensitivityEnum] = None
    loitering_threshold: Optional[float] = Field(None, gt=0, description="Time in seconds for loitering alert.")
    risk_alert_threshold: Optional[float] = Field(None, gt=0, lt=100, description="Risk score to trigger a high alert.")

class CameraBase(BaseModel):
    name: str = Field(..., description="User-friendly name for the camera.")
    video_source: str = Field(..., description="URL or path for the video feed.")
    zones: Optional[str] = Field(None, description="JSON string of zone configurations.")

class CameraCreate(CameraBase):
    pass

class Camera(CameraBase, CameraSettingsUpdate):
    id: int
    owner_id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# --- Incident Models ---
class IncidentBase(BaseModel):
    timestamp: datetime
    track_id: int
    risk_score: float
    primary_threat: str
    location_x: Optional[int] = None
    location_y: Optional[int] = None
    details: Optional[str] = None
    resolved: bool = False
    path_data: Optional[str] = Field(None, description="JSON string of tracked coordinates.")

class IncidentCreate(IncidentBase):
    pass

class Incident(IncidentBase):
    id: int
    camera_id: int
    user_id: int
    snapshots: List[Snapshot] = []
    notification_sent: bool = False
    model_config = ConfigDict(from_attributes=True)


# --- User Models ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    phone_number: Optional[str] = Field(None, max_length=20)

class User(UserBase):
    id: int
    created_at: datetime
    role: UserRoleEnum
    phone_number: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    cameras: List[Camera] = []
    model_config = ConfigDict(from_attributes=True)

# --- System Statistics Models ---
class RiskDistribution(BaseModel):
    low: int
    medium: int
    high: int
    critical: int

class SystemStats(BaseModel):
    active_trackers: int
    total_trackers: int
    risk_distribution: RiskDistribution
    fps: float
    zones: int

# --- Authentication Token Models ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRoleEnum] = None

# --- Models for Telegram Webhook ---
class TelegramUser(BaseModel):
    id: int
    first_name: str
    username: Optional[str] = None

class TelegramChat(BaseModel):
    id: int
    type: str

class TelegramMessage(BaseModel):
    message_id: int
    from_user: TelegramUser = Field(..., alias='from')
    chat: TelegramChat
    date: int
    text: str

class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage

# --- Analytics Models ---
class ThreatFrequency(BaseModel):
    name: str
    value: int

class ZoneSummary(BaseModel):
    zone_name: str
    intrusion: int
    loitering: int

class AnalyticsData(BaseModel):
    threat_frequency: List[ThreatFrequency]
    zone_summary: List[ZoneSummary]

# --- Alerts Page Models ---
class Alert(BaseModel):
    id: int
    threat_type: str
    risk_score: float
    timestamp: datetime
    camera_name: str
    snapshot_url: Optional[str] = None
    resolved: bool

class AlertsResponse(BaseModel):
    alerts: List[Alert]
