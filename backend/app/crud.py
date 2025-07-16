from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy import func, case

from . import models, schemas, security

# --- User CRUD Operations ---

def get_user(db: Session, user_id: int) -> Optional[schemas.User]:
    return db.query(schemas.User).filter(schemas.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[schemas.User]:
    return db.query(schemas.User).filter(schemas.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[schemas.User]:
    return db.query(schemas.User).filter(schemas.User.email == email).first()

def get_user_by_telegram_code(db: Session, code: str) -> Optional[schemas.User]:
    return db.query(schemas.User).filter(
        schemas.User.telegram_linking_code == code,
        schemas.User.telegram_linking_code_expires > datetime.now(timezone.utc)
    ).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[schemas.User]:
    return db.query(schemas.User).order_by(schemas.User.id).offset(skip).limit(limit).all()

def create_user(db: Session, user: models.UserCreate) -> schemas.User:
    hashed_password = security.get_password_hash(user.password)
    db_user = schemas.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def promote_user_to_admin(db: Session, user_id: int) -> Optional[schemas.User]:
    db_user = get_user(db, user_id=user_id)
    if db_user:
        db_user.role = models.UserRoleEnum.admin
        db.commit()
        db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: models.UserUpdate) -> Optional[schemas.User]:
    db_user = get_user(db, user_id=user_id)
    if not db_user:
        return None
    update_data = user_update.dict(exclude_unset=True)
    if "username" in update_data:
        existing_user = get_user_by_username(db, username=update_data["username"])
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")
        db_user.username = update_data["username"]
    if "email" in update_data:
        existing_user = get_user_by_email(db, email=update_data["email"])
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered by another user.")
        db_user.email = update_data["email"]
    if "password" in update_data and update_data["password"]:
        db_user.hashed_password = security.get_password_hash(update_data["password"])
    if "phone_number" in update_data:
        db_user.phone_number = update_data["phone_number"]
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Camera CRUD Operations ---
def get_camera(db: Session, camera_id: int, user_id: int) -> Optional[schemas.Camera]:
    return db.query(schemas.Camera).filter(schemas.Camera.id == camera_id, schemas.Camera.owner_id == user_id).first()

def get_cameras_by_user(db: Session, user_id: int) -> List[schemas.Camera]:
    return db.query(schemas.Camera).filter(schemas.Camera.owner_id == user_id).all()

def create_user_camera(db: Session, camera: models.CameraCreate, user_id: int) -> schemas.Camera:
    db_camera = schemas.Camera(**camera.dict(), owner_id=user_id)
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera

def update_camera_settings(db: Session, camera_id: int, user_id: int, settings: models.CameraSettingsUpdate) -> Optional[schemas.Camera]:
    db_camera = get_camera(db, camera_id=camera_id, user_id=user_id)
    if db_camera:
        update_data = settings.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_camera, key, value)
        db.commit()
        db.refresh(db_camera)
    return db_camera

def update_camera_zones(db: Session, camera_id: int, user_id: int, zones_json: str) -> Optional[schemas.Camera]:
    db_camera = get_camera(db, camera_id=camera_id, user_id=user_id)
    if db_camera:
        db_camera.zones = zones_json
        db.commit()
        db.refresh(db_camera)
    return db_camera

def delete_user_camera(db: Session, camera_id: int, user_id: int) -> Optional[schemas.Camera]:
    db_camera = get_camera(db, camera_id=camera_id, user_id=user_id)
    if db_camera:
        db.delete(db_camera)
        db.commit()
    return db_camera

# --- Incident CRUD Operations ---
def get_incidents_by_camera(db: Session, user_id: int, camera_id: int, skip: int = 0, limit: int = 100) -> List[schemas.Incident]:
    return db.query(schemas.Incident).options(
        joinedload(schemas.Incident.snapshots)
    ).filter(
        schemas.Incident.camera_id == camera_id,
        schemas.Incident.user_id == user_id
    ).order_by(schemas.Incident.timestamp.desc()).offset(skip).limit(limit).all()

def get_incidents_for_export(db: Session, user_id: int, start_date: datetime, end_date: datetime, camera_id: Optional[int] = None) -> List[schemas.Incident]:
    end_of_day = end_date + timedelta(days=1)
    query = db.query(schemas.Incident).filter(
        schemas.Incident.user_id == user_id,
        schemas.Incident.timestamp >= start_date,
        schemas.Incident.timestamp < end_of_day
    )
    if camera_id:
        query = query.filter(schemas.Incident.camera_id == camera_id)
    return query.order_by(schemas.Incident.timestamp.asc()).all()

def create_incident(db: Session, incident: models.IncidentCreate, user_id: int, camera_id: int) -> schemas.Incident:
    db_incident = schemas.Incident(**incident.dict(), user_id=user_id, camera_id=camera_id)
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    return db_incident

def update_incident_status(db: Session, incident_id: int, resolved: bool, user_id: int) -> Optional[schemas.Incident]:
    db_incident = db.query(schemas.Incident).filter(schemas.Incident.id == incident_id, schemas.Incident.user_id == user_id).first()
    if db_incident:
        db_incident.resolved = resolved
        db.commit()
        db.refresh(db_incident)
    return db_incident

def get_latest_incident_for_track(db: Session, camera_id: int, track_id: int) -> Optional[schemas.Incident]:
    return db.query(schemas.Incident).filter(
        schemas.Incident.camera_id == camera_id,
        schemas.Incident.track_id == track_id
    ).order_by(schemas.Incident.timestamp.desc()).first()

# --- Snapshot CRUD Operations ---
def create_snapshot(db: Session, snapshot: models.SnapshotCreate, incident_id: int, user_id: int) -> schemas.Snapshot:
    db_snapshot = schemas.Snapshot(**snapshot.dict(), incident_id=incident_id, owner_id=user_id)
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot

def get_snapshots_by_incident(db: Session, incident_id: int, user_id: int) -> List[schemas.Snapshot]:
    return db.query(schemas.Snapshot).filter(
        schemas.Snapshot.incident_id == incident_id,
        schemas.Snapshot.owner_id == user_id
    ).all()

# --- Analytics and Alert CRUD ---
def get_analytics_summary(db: Session, user_id: int) -> dict:
    threat_frequency_query = db.query(
        schemas.Incident.primary_threat,
        func.count(schemas.Incident.id).label("count")
    ).filter(schemas.Incident.user_id == user_id).group_by(schemas.Incident.primary_threat).all()
    threat_frequency = [{"name": threat, "value": count} for threat, count in threat_frequency_query]

    zone_summary_query = db.query(
        schemas.Camera.name,
        func.sum(case((schemas.Incident.primary_threat == 'intrusion', 1), else_=0)).label("intrusion_count"),
        func.sum(case((schemas.Incident.primary_threat == 'suspicious_loitering', 1), else_=0)).label("loitering_count")
    ).join(schemas.Incident, schemas.Camera.id == schemas.Incident.camera_id)\
     .filter(schemas.Camera.owner_id == user_id)\
     .group_by(schemas.Camera.name).all()
    zone_summary = [
        {"zone_name": name, "intrusion": intrusions, "loitering": loitering}
        for name, intrusions, loitering in zone_summary_query
    ]
    return {"threat_frequency": threat_frequency, "zone_summary": zone_summary}

def get_notified_alerts(db: Session, user_id: int) -> List[dict]:
    results = db.query(
        schemas.Incident.id,
        schemas.Incident.primary_threat,
        schemas.Incident.risk_score,
        schemas.Incident.timestamp,
        schemas.Incident.resolved,
        schemas.Camera.name,
        schemas.Snapshot.image_url
    ).select_from(schemas.Incident)\
     .join(schemas.Camera, schemas.Incident.camera_id == schemas.Camera.id)\
     .outerjoin(schemas.Snapshot, schemas.Incident.id == schemas.Snapshot.incident_id)\
     .filter(
        schemas.Incident.user_id == user_id,
        schemas.Incident.notification_sent == True
     )\
     .order_by(schemas.Incident.timestamp.desc())\
     .distinct(schemas.Incident.id)\
     .all()
    alerts = [
        {
            "id": r[0], "threat_type": r[1], "risk_score": r[2], "timestamp": r[3],
            "resolved": r[4], "camera_name": r[5], "snapshot_url": r[6]
        } for r in results
    ]
    return alerts
