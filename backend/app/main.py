import asyncio
import logging
import threading
from typing import Dict, List, Any, Union, Optional
from datetime import datetime, timedelta, timezone
from io import BytesIO
import pandas as pd
import json
import shutil
from pathlib import Path
import time
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import requests

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, APIRouter, status, Body, UploadFile, File, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse, Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware


# --- Application Imports ---
from . import models, schemas, crud, auth
from .database import engine, Base, get_db, SessionLocal
from .config import settings
from .video_processing import video_processing_loop, get_single_frame
from .telegram_bot import handle_start_command
from .blob_storage import blob_service_client, container_name

# --- Setup ---
Base.metadata.create_all(bind=engine)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.PROJECT_NAME)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    try:
        first_error = exc.errors()[0]
        field = " -> ".join(str(loc) for loc in first_error['loc'] if loc != 'body')
        message = first_error['msg']
        detail = f"Validation Error for field '{field}': {message}"
    except (IndexError, KeyError):
        detail = "Invalid input data provided."
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )

# --- In-memory state for persistent threads ---
video_processing_threads: Dict[int, threading.Thread] = {}
active_websockets: Dict[int, List[WebSocket]] = {}
camera_systems: Dict[int, Any] = {}
pause_events: Dict[int, threading.Event] = {}
thread_stop_flags: Dict[int, threading.Event] = {}


# --- API Routers ---
api_router = APIRouter(prefix="/api", dependencies=[Depends(auth.get_current_active_user)])
auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])
admin_router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(auth.get_current_admin_user)])
public_router = APIRouter(prefix="/api/public", tags=["Public"])


# --- Helper and Callback Functions ---
async def broadcast_data(camera_id: int, data: Union[bytes, str]):
    sockets_to_send = active_websockets.get(camera_id, [])[:]
    for websocket in sockets_to_send:
        try:
            if isinstance(data, bytes):
                await websocket.send_bytes(data)
            else:
                await websocket.send_text(data)
        except (WebSocketDisconnect, RuntimeError):
            if camera_id in active_websockets and websocket in active_websockets[camera_id]:
                active_websockets[camera_id].remove(websocket)
            logger.info(f"Removed disconnected client from camera {camera_id}")
        except Exception as e:
            logger.error(f"Error sending data to client for camera {camera_id}: {e}")

# --- Authentication Endpoints ---
@auth_router.post("/register", response_model=models.User, status_code=status.HTTP_201_CREATED)
def register_user(user: models.UserCreate, db: Session = Depends(get_db)):
    db_user_by_username = crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@auth_router.post("/login", response_model=models.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Admin Endpoints ---
@admin_router.get("/users", response_model=List[models.User])
def read_all_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

@admin_router.post("/users/{user_id}/promote", response_model=models.User)
def promote_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.promote_user_to_admin(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# --- Standard User Endpoints ---
@api_router.get("/users/me", response_model=models.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@api_router.patch("/users/me", response_model=models.User)
def update_current_user(user_update: models.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    updated_user = crud.update_user(db, user_id=current_user.id, user_update=user_update)
    if updated_user is None:
        raise HTTPException(status_code=409, detail="Username already taken.")
    return updated_user

@api_router.post("/users/me/generate-telegram-link", response_model=Dict[str, str])
def generate_telegram_link(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    user = crud.get_user(db, user_id=current_user.id)
    
    code = secrets.token_urlsafe(16)
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    user.telegram_linking_code = code
    user.telegram_linking_code_expires = expires
    db.commit()
    
    bot_username = "AICCTVBot"
    link = f"https://t.me/{bot_username}?start={code}"
    
    logger.info(f"Generated Telegram link for user '{user.username}' with code '{code}'")
    return {"link": link}

# --- Endpoints to Control Analysis Threads ---
@api_router.post("/cameras/{camera_id}/start", status_code=status.HTTP_200_OK)
def start_camera_analysis(camera_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if camera_id in video_processing_threads and video_processing_threads[camera_id].is_alive():
        raise HTTPException(status_code=409, detail="Analysis is already running for this camera.")

    camera = crud.get_camera(db, camera_id=camera_id, user_id=current_user.id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found or access denied.")

    stop_flag = threading.Event()
    pause_event = threading.Event()
    pause_event.set()

    thread = threading.Thread(
        target=video_processing_loop,
        args=(camera, current_user.id, SessionLocal, camera_systems, stop_flag, broadcast_data, pause_event),
        daemon=True
    )
    
    thread_stop_flags[camera_id] = stop_flag
    pause_events[camera_id] = pause_event
    video_processing_threads[camera_id] = thread
    
    thread.start()
    logger.info(f"Started persistent analysis thread for camera {camera_id}")
    return {"message": "Camera analysis started."}

@api_router.post("/cameras/{camera_id}/stop", status_code=status.HTTP_200_OK)
def stop_camera_analysis(camera_id: int):
    if camera_id not in thread_stop_flags:
        raise HTTPException(status_code=404, detail="Analysis not running for this camera.")
    
    logger.info(f"Signaling stop for camera {camera_id}")
    thread_stop_flags[camera_id].set()
    
    video_processing_threads.pop(camera_id, None)
    thread_stop_flags.pop(camera_id, None)
    pause_events.pop(camera_id, None)
    camera_systems.pop(camera_id, None)
    
    return {"message": "Camera analysis stopped."}

@api_router.post("/cameras/{camera_id}/pause", status_code=status.HTTP_200_OK)
def pause_camera_analysis(camera_id: int):
    if camera_id not in pause_events:
        raise HTTPException(status_code=404, detail="Analysis not running for this camera.")
    pause_events[camera_id].clear()
    return {"message": "Camera analysis paused."}

@api_router.post("/cameras/{camera_id}/play", status_code=status.HTTP_200_OK)
def play_camera_analysis(camera_id: int):
    if camera_id not in pause_events:
        raise HTTPException(status_code=404, detail="Analysis not running for this camera.")
    pause_events[camera_id].set()
    return {"message": "Camera analysis resumed."}

@api_router.get("/cameras/status", response_model=Dict[int, str])
def get_all_camera_statuses():
    statuses = {}
    for cam_id, thread in list(video_processing_threads.items()):
        if thread.is_alive():
            if cam_id in pause_events and not pause_events[cam_id].is_set():
                statuses[cam_id] = "paused"
            else:
                statuses[cam_id] = "running"
    return statuses

# --- Camera CRUD and Other Endpoints ---
@api_router.post("/cameras/url", response_model=models.Camera, status_code=status.HTTP_201_CREATED)
def create_camera_from_url(camera: models.CameraCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.create_user_camera(db=db, camera=camera, user_id=current_user.id)

@api_router.post("/cameras/upload", response_model=models.Camera, status_code=status.HTTP_201_CREATED)
def create_camera_from_upload(name: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    file_path = UPLOADS_DIR / f"{current_user.id}_{datetime.now(timezone.utc).timestamp()}_{file.filename}"
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
    camera_data = models.CameraCreate(name=name, video_source=str(file_path))
    return crud.create_user_camera(db=db, camera=camera_data, user_id=current_user.id)

@api_router.get("/cameras", response_model=List[models.Camera])
def get_user_cameras(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_cameras_by_user(db=db, user_id=current_user.id)

@api_router.delete("/cameras/{camera_id}", response_model=models.Camera)
def delete_camera_for_user(camera_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    deleted_camera = crud.delete_user_camera(db, camera_id=camera_id, user_id=current_user.id)
    if not deleted_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return deleted_camera

@api_router.get("/cameras/{camera_id}/snapshot")
def get_camera_snapshot(camera_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    camera = crud.get_camera(db, camera_id=camera_id, user_id=current_user.id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    image_bytes = get_single_frame(camera.video_source)
    if not image_bytes:
        raise HTTPException(status_code=500, detail="Could not capture frame from video source")
    return Response(content=image_bytes, media_type="image/jpeg")

@api_router.put("/cameras/{camera_id}/settings", response_model=models.Camera)
def update_camera_settings(camera_id: int, settings: models.CameraSettingsUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    updated_camera = crud.update_camera_settings(db, camera_id=camera_id, user_id=current_user.id, settings=settings)
    if not updated_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return updated_camera

@api_router.put("/cameras/{camera_id}/zones", response_model=models.Camera)
def update_camera_zones(camera_id: int, zones: Dict[str, Any] = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    zones_json = json.dumps(zones)
    updated_camera = crud.update_camera_zones(db, camera_id=camera_id, user_id=current_user.id, zones_json=zones_json)
    if not updated_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return updated_camera

@api_router.get("/stats/{camera_id}", response_model=models.SystemStats)
def get_system_stats(camera_id: int):
    if camera_id in camera_systems:
        system = camera_systems[camera_id]
        stats = system.get_system_statistics(time.time())
        return models.SystemStats(**stats)
    raise HTTPException(status_code=404, detail="Analysis not running or camera system not found")

@api_router.get("/incidents/{camera_id}", response_model=List[models.Incident])
def read_incidents_for_camera(camera_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_incidents_by_camera(db, user_id=current_user.id, camera_id=camera_id)

@api_router.patch("/incidents/{incident_id}/resolve", response_model=models.Incident)
def resolve_incident_endpoint(incident_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    updated_incident = crud.update_incident_status(db, incident_id=incident_id, resolved=True, user_id=current_user.id)
    if not updated_incident:
        raise HTTPException(status_code=404, detail="Incident not found or access denied.")
    return updated_incident

@api_router.get("/incidents/{incident_id}/snapshots", response_model=List[models.Snapshot])
def get_incident_snapshots(incident_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_snapshots_by_incident(db, incident_id=incident_id, user_id=current_user.id)

@api_router.get("/export/incidents", response_class=StreamingResponse)
def export_incidents_to_csv(start_date: datetime, end_date: datetime, camera_id: int = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    incidents = crud.get_incidents_for_export(db, user_id=current_user.id, start_date=start_date, end_date=end_date, camera_id=camera_id)
    export_data = [{"Incident ID": inc.id, "Timestamp": inc.timestamp.isoformat(), "Camera ID": inc.camera_id, "Threat Type": inc.primary_threat, "Risk Score": inc.risk_score, "Resolved": inc.resolved, "Details": inc.details} for inc in incidents]
    df = pd.DataFrame(export_data)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=incidents_export_{datetime.now().date()}.csv"
    return response

@public_router.get("/snapshot-proxy")
async def snapshot_proxy(url: str):
    if not blob_service_client:
        raise HTTPException(status_code=503, detail="Blob storage service is not configured.")
    try:
        blob_name = url.split(f'/{container_name}/')[1]
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        stream = BytesIO()
        blob_client.download_blob().readinto(stream)
        stream.seek(0)
        return StreamingResponse(stream, media_type="image/jpeg")
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid snapshot URL format.")
    except Exception as e:
        logger.error(f"Failed to retrieve blob '{blob_name}' from Azure: {e}")
        raise HTTPException(status_code=404, detail="Could not retrieve snapshot image from storage.")

@api_router.post("/complaint", status_code=status.HTTP_201_CREATED)
async def submit_complaint(
    current_user: models.User = Depends(auth.get_current_active_user),
    to_email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    incident_id: Optional[int] = Form(None),
    evidence: Optional[UploadFile] = File(None)
):
    logger.info(f"Received complaint from user: {current_user.username} to {to_email}")
    if not all([settings.SMTP_SERVER, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
        logger.error("Cannot send complaint email: SMTP settings are not fully configured.")
        raise HTTPException(status_code=500, detail="Complaint system is not configured.")
    official_email = to_email
    sender_email = settings.SMTP_USERNAME
    msg = MIMEMultipart()
    msg["Subject"] = f"New Complaint Submitted: {subject}"
    msg["From"] = f"{current_user.username} <{sender_email}>"
    msg["To"] = official_email
    incident_info = f"Regarding Incident ID: {incident_id}\n\n" if incident_id else ""
    body = f"A new complaint has been submitted by a user.\n\nFrom User: {current_user.username} (ID: {current_user.id})\nUser Email: {current_user.email}\n{incident_info}Subject: {subject}\n-----------------------------------\n\nMessage:\n{message}"
    msg.attach(MIMEText(body, 'plain'))
    if evidence:
        file_content = await evidence.read()
        attachment = MIMEApplication(file_content, Name=evidence.filename)
        attachment['Content-Disposition'] = f'attachment; filename="{evidence.filename}"'
        msg.attach(attachment)
        logger.info(f"Attached evidence file: {evidence.filename}")
    try:
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(sender_email, official_email, msg.as_string())
            logger.info(f"Successfully sent complaint email to {official_email}")
    except Exception as e:
        logger.error(f"Failed to send complaint email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send the complaint email.")
    return {"message": "Complaint submitted successfully."}

@public_router.post("/telegram/webhook")
async def telegram_webhook(update: models.TelegramUpdate, db: Session = Depends(get_db)):
    if update.message and update.message.text:
        chat_id = update.message.chat.id
        text = update.message.text
        logger.info(f"Received message from Telegram Chat ID {chat_id}: '{text}'")
        if text.startswith("/start"):
            handle_start_command(db, chat_id, text)
    return {"ok": True}

# --- NEW ENDPOINTS FOR ANALYTICS AND ALERTS ---
@api_router.get("/analytics/summary", response_model=models.AnalyticsData)
def get_analytics(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    summary_data = crud.get_analytics_summary(db, user_id=current_user.id)
    return summary_data

@api_router.get("/alerts", response_model=models.AlertsResponse)
def get_all_notified_alerts(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    alerts_data = crud.get_notified_alerts(db, user_id=current_user.id)
    return {"alerts": alerts_data}

# --- WEBSOCKET ENDPOINT ---
@app.websocket("/ws/video_feed/{camera_id}")
async def websocket_endpoint(websocket: WebSocket, camera_id: int, token: str):
    db: Session = next(get_db())
    try:
        current_user = await auth.get_current_user(token=token, db=db)
        camera = crud.get_camera(db, camera_id=camera_id, user_id=current_user.id)
        if not camera:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Camera not found or access denied")
            return
        if camera_id not in video_processing_threads or not video_processing_threads[camera_id].is_alive():
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Analysis is not running for this camera.")
            return
        await websocket.accept()
        logger.info(f"User '{current_user.username}' connected to watch camera '{camera.name}'")
        if camera_id not in active_websockets:
            active_websockets[camera_id] = []
        active_websockets[camera_id].append(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from watching camera {camera_id}")
    except Exception as e:
        logger.error(f"An error occurred in the websocket for camera {camera_id}: {e}", exc_info=True)
    finally:
        db.close()
        if camera_id in active_websockets and websocket in active_websockets[camera_id]:
            active_websockets[camera_id].remove(websocket)

# --- Include all routers in the main app ---
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(admin_router)
app.include_router(public_router)
