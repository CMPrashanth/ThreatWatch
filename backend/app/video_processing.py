import asyncio
import logging
import time
import cv2
from sqlalchemy.orm import Session
from typing import Callable, Optional, Dict
import json
from datetime import datetime, timezone
import threading

from .test import SecurityMonitoringSystem
from . import models, crud, config
from .blob_storage import upload_snapshot
from .notifications import send_sms_alert, send_telegram_alert, send_email_alert

logger = logging.getLogger(__name__)


def get_single_frame(video_source: str) -> Optional[bytes]:
    """
    Captures a single frame from a video source.
    """
    cap = None
    try:
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            logger.error(f"Failed to open video source for snapshot: {video_source}")
            return None
        
        ret, frame = cap.read()
        if not ret:
            logger.error(f"Failed to read frame from video source: {video_source}")
            return None
            
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()
    except Exception as e:
        logger.error(f"Error capturing single frame: {e}")
        return None
    finally:
        if cap:
            cap.release()

def send_notifications_in_thread(
    recipient_email: Optional[str],
    recipient_phone: Optional[str],
    recipient_chat_id: Optional[str],
    alert_details: Dict,
    image_bytes: Optional[bytes] = None
):
    """
    Wrapper function to send all notifications in a separate thread.
    """
    logger.info(f"Starting notification thread for threat: {alert_details.get('threat_type')}")
    try:
        if recipient_phone:
            send_sms_alert(recipient_number=recipient_phone, **alert_details)
        if recipient_chat_id:
            send_telegram_alert(chat_id=recipient_chat_id, image_bytes=image_bytes, **alert_details)
        if recipient_email:
            send_email_alert(recipient_email=recipient_email, image_bytes=image_bytes, **alert_details)
        logger.info("Notification thread finished.")
    except Exception as e:
        logger.error(f"Error in notification thread: {e}", exc_info=True)

def upload_and_save_snapshot_in_thread(
    image_bytes: bytes,
    user_id: int,
    incident_id: int,
    SessionLocal: Callable[[], Session]
):
    """
    Runs in a separate thread to upload a snapshot and save its record to the DB.
    """
    logger.info(f"Starting snapshot upload thread for incident {incident_id}...")
    try:
        image_url = upload_snapshot(image_bytes, user_id, incident_id)

        if image_url:
            db = SessionLocal()
            try:
                snapshot_data = models.SnapshotCreate(image_url=image_url, timestamp=datetime.now(timezone.utc))
                crud.create_snapshot(db, snapshot=snapshot_data, incident_id=incident_id, user_id=user_id)
                logger.info(f"Successfully saved snapshot record for incident {incident_id}.")
            finally:
                db.close()
        else:
            logger.warning(f"Skipping snapshot DB entry for incident {incident_id} due to upload failure.")
    except Exception as e:
        logger.error(f"Error in snapshot upload thread for incident {incident_id}: {e}", exc_info=True)


def video_processing_loop(
    camera: models.Camera,
    user_id: int,
    SessionLocal: Callable[[], Session],
    camera_systems: Dict,
    stop_flag: threading.Event,
    broadcast_callback: Callable,
    pause_event: threading.Event,
):
    """
    The core function that runs in a separate thread for each camera.
    UPDATED: Flags incidents in the DB when a notification is sent.
    """
    cap = None
    try:
        system = SecurityMonitoringSystem(
            model_path=config.settings.YOLO_MODEL_PATH,
            strongsort_config=config.settings.STRONGSORT_CONFIG_PATH,
            strongsort_weights=config.settings.STRONGSORT_WEIGHTS_PATH,
            camera_id=str(camera.id),
            zones_json=camera.zones
        )
        system.loitering_threshold = camera.loitering_threshold
        system.risk_alert_threshold = camera.risk_alert_threshold
        
        camera_systems[camera.id] = system
        
        cap = cv2.VideoCapture(camera.video_source)
        if not cap.isOpened():
            logger.error(f"[{camera.id}] Failed to open video source: {camera.video_source}")
            return

        logger.info(f"[{camera.id}] Started video processing thread for user {user_id}.")

        while not stop_flag.is_set():
            pause_event.wait() 
            
            if stop_flag.is_set():
                break

            ret, frame = cap.read()
            if not ret:
                time.sleep(0.5) 
                continue
            
            current_loop_time = time.time()
            
            _, buffer = cv2.imencode('.jpg', frame)
            image_bytes_for_this_frame = buffer.tobytes()

            incidents_to_log, reportable_alerts = system.process_alerts(current_loop_time)
            
            processed_frame = system.process_frame(frame, current_loop_time)

            if incidents_to_log:
                db = SessionLocal()
                try:
                    for incident_data in incidents_to_log:
                        incident_to_create = models.IncidentCreate(**incident_data)
                        db_incident = crud.create_incident(db, incident=incident_to_create, user_id=user_id, camera_id=camera.id)
                        
                        if db_incident:
                            snapshot_thread = threading.Thread(
                                target=upload_and_save_snapshot_in_thread,
                                args=(
                                    image_bytes_for_this_frame,
                                    user_id,
                                    db_incident.id,
                                    SessionLocal
                                )
                            )
                            snapshot_thread.start()
                finally:
                    db.close()

            if reportable_alerts:
                db = SessionLocal()
                try:
                    camera_owner = crud.get_user(db, user_id=user_id)
                    if not camera_owner:
                        logger.warning(f"Could not find owner with ID {user_id} to send notification.")
                        continue

                    contact_details = {
                        "recipient_email": camera_owner.email,
                        "recipient_phone": camera_owner.phone_number,
                        "recipient_chat_id": camera_owner.telegram_chat_id,
                    }

                    for alert in reportable_alerts:
                        # Flag the corresponding incident in the database
                        db_incident = crud.get_latest_incident_for_track(db, camera.id, alert['track_id'])
                        if db_incident:
                            db_incident.notification_sent = True
                            db.commit()
                            logger.info(f"Flagged incident {db_incident.id} as 'notification_sent'.")

                        # Broadcast the alert to the UI
                        alert_payload = {
                            "type": "alert", 
                            "payload": {**alert, "camera_name": camera.name}
                        }
                        asyncio.run(broadcast_callback(camera.id, json.dumps(alert_payload)))

                        # Send external notifications
                        if alert['level'] == 'CRITICAL':
                            alert_details = {
                                "threat_type": alert.get('threat_type'),
                                "camera_name": camera.name,
                                "risk_score": alert.get('risk_score')
                            }
                            
                            notification_thread = threading.Thread(
                                target=send_notifications_in_thread, 
                                args=(
                                    contact_details["recipient_email"],
                                    contact_details["recipient_phone"],
                                    contact_details["recipient_chat_id"],
                                    alert_details,
                                    image_bytes_for_this_frame
                                )
                            )
                            notification_thread.start()
                finally:
                    db.close()

            _, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            asyncio.run(broadcast_callback(camera.id, frame_bytes))
            time.sleep(0.01)

    except Exception as e:
        logger.error(f"[{camera.id}] Critical error in video processing loop: {e}", exc_info=True)
    finally:
        if cap: cap.release()
        logger.info(f"[{camera.id}] Stopped video processing thread.")
