import cv2
import numpy as np
import torch
from ultralytics import YOLO
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import json
import logging
from datetime import datetime
import math
import sqlite3
from pathlib import Path
import sys
sys.path.append(r"G:\Downloads\cognizant\Mock Hackathon\tracking\Yolov5_StrongSORT_OSNet")
from .zone_manager import ZoneManager
from boxmot import StrongSort
from Yolov5_StrongSORT_OSNet.boxmot.tracker_zoo import create_tracker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RiskEvent:
    """Represents a single risk event with metadata"""
    event_type: str
    risk_score: float
    confidence: float
    timestamp: float
    duration: float = 0.0
    location: Tuple[int, int] = (0, 0)
    description: str = ""

@dataclass
class PersonTracker:
    """Tracks a person's movement and behavior over time"""
    track_id: int
    positions: deque = field(default_factory=lambda: deque(maxlen=30))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=30))
    detected_objects: deque = field(default_factory=lambda: deque(maxlen=10))
    risk_events: List[RiskEvent] = field(default_factory=list)
    total_risk_score: float = 0.0
    max_risk_score: float = 0.0
    status: str = "normal"
    last_seen: float = 0.0
    zone_entry_time: Optional[float] = None
    stationary_start: Optional[float] = None
    last_bbox: List[int] = field(default_factory=list)
    
    last_notified_threat: str = "normal"
    
    def add_position(self, pos: Tuple[int, int], timestamp: float, bbox: List[int]):
        self.positions.append(pos)
        self.timestamps.append(timestamp)
        self.last_seen = timestamp
        self.last_bbox = bbox
        
    def get_speed(self) -> float:
        if len(self.positions) < 2: return 0.0
        total_distance = 0.0
        total_time = 0.0
        for i in range(1, len(self.positions)):
            dx = self.positions[i][0] - self.positions[i-1][0]
            dy = self.positions[i][1] - self.positions[i-1][1]
            distance = math.sqrt(dx*dx + dy*dy)
            time_diff = self.timestamps[i] - self.timestamps[i-1]
            if time_diff > 0:
                total_distance += distance
                total_time += time_diff
        return total_distance / total_time if total_time > 0 else 0.0
    
    def get_movement_pattern(self) -> str:
        if len(self.positions) < 5: return "insufficient_data"
        speed = self.get_speed()
        direction_changes = 0
        for i in range(2, len(self.positions)):
            prev_angle = math.atan2(self.positions[i-1][1] - self.positions[i-2][1], self.positions[i-1][0] - self.positions[i-2][0])
            curr_angle = math.atan2(self.positions[i][1] - self.positions[i-1][1], self.positions[i][0] - self.positions[i-1][0])
            angle_diff = abs(curr_angle - prev_angle)
            if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff
            if angle_diff > math.pi / 4: direction_changes += 1
        change_rate = direction_changes / len(self.positions)
        if speed < 5: return "stationary"
        elif speed > 50: return "running"
        elif change_rate > 0.3: return "erratic"
        elif change_rate < 0.1: return "linear"
        else: return "normal"
        
class RiskScoreCalculator:
    """Enhanced risk scoring system with dynamic weights and temporal factors"""
    
    def __init__(self):
        # Base risk scores for different events
        self.base_risk_scores = {
            'intrusion': 15.0,          # Unauthorized area access
            'armed_person': 20.0,       # Weapon detected
            'suspicious_loitering': 8.0, # Extended presence in area
            'erratic_movement': 6.0,    # Unusual movement patterns
            'running': 5.0,             # Fast movement (could be fleeing)
            'group_formation': 7.0,     # Multiple people gathering
        }
        
        # Confidence multipliers
        self.confidence_weights = {
            'high': 1.0,
            'medium': 0.8,
            'low': 0.5
        }
        
        # Time-based multipliers
        self.time_multipliers = {
            'immediate': 1.5,    # Happening right now
            'recent': 1.2,       # Within last 30 seconds
            'ongoing': 1.0,      # Continuous behavior
            'historical': 0.7    # Past events
        }
        
        # Zone-based multipliers
        self.zone_multipliers = {
            'critical': 2.0,     # Server room, vault, etc.
            'restricted': 1.5,   # Employee-only areas
            'monitored': 1.2,    # High-security zones
            'public': 1.0,       # General access areas
            'low_risk': 0.8      # Break rooms, etc.
        }
    
    def calculate_risk_score(self, person: PersonTracker, current_time: float) -> Tuple[float, str]:
        """Calculate comprehensive risk score for a person"""
        total_score = 0.0
        primary_threat = "normal"
        max_event_score = 0.0
        
        # Evaluate each risk event
        for event in person.risk_events:
            base_score = self.base_risk_scores.get(event.event_type, 0.0)
            
            # Apply confidence weighting
            confidence_factor = self.confidence_weights.get(self._get_confidence_level(event.confidence), 1.0)
            
            # Apply temporal decay
            time_factor = self._calculate_time_factor(event.timestamp, current_time)
            
            # Apply location multiplier (if location data available)
            location_factor = 1.0  # Can be enhanced with zone detection
            
            # Calculate final event score
            event_score = base_score * confidence_factor * time_factor * location_factor
            
            # Add duration bonus for persistent events
            if event.duration > 30:  # 30 seconds
                duration_bonus = min(event.duration / 60, 2.0)  # Max 2x bonus for 2+ minutes
                event_score *= (1.0 + duration_bonus * 0.3)
            
            total_score += event_score
            
            if event_score > max_event_score:
                max_event_score = event_score
                primary_threat = event.event_type
        
        # Apply behavioral pattern multipliers
        movement_pattern = person.get_movement_pattern()
        if movement_pattern == "erratic":
            total_score *= 1.3
        elif movement_pattern == "running":
            total_score *= 1.2
        elif movement_pattern == "stationary" and len(person.risk_events) > 0:
            total_score *= 1.1
        
        # Escalation for multiple concurrent violations
        if len([e for e in person.risk_events if current_time - e.timestamp < 60]) > 2:
            total_score *= 1.4
        
        return min(total_score, 100.0), primary_threat  # Cap at 100
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert numerical confidence to categorical level"""
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_time_factor(self, event_time: float, current_time: float) -> float:
        """Calculate time-based decay factor"""
        if event_time is None or current_time is None:
            return 1.0
        
        try:
            time_diff = current_time - event_time
            
            if time_diff < 10:  # Immediate
                return 1.5
            elif time_diff < 30:  # Recent
                return 1.2
            elif time_diff < 120:  # Ongoing
                return 1.0
            else:  # Historical - exponential decay
                return max(0.3, math.exp(-time_diff / 300))  # 5-minute half-life
        except (TypeError, ValueError):
            return 1.0

class SecurityZone:
    """Defines security zones with different access levels"""
    
    def __init__(self, name: str, points: List[Dict], access_level: str = "public", **kwargs):
        """
        Initializes a zone, accepting extra keyword arguments to be robust.
        The 'points' are expected as a list of dictionaries, e.g., [{'x': 10, 'y': 20}].
        """
        self.name = name
        self.access_level = access_level
        
        try:
            self.points = np.array([[p['x'], p['y']] for p in points], dtype=np.int32)
        except (KeyError, TypeError):
            logger.error(f"Failed to parse points for zone '{name}'. Invalid format.")
            self.points = np.array([], dtype=np.int32)

    def contains_point(self, point: Tuple[int, int]) -> bool:
        """Check if point is inside the zone"""
        if self.points.size == 0:
            return False
        return cv2.pointPolygonTest(self.points, point, False) >= 0

class SecurityMonitoringSystem:
    """Main security monitoring system"""

    def __init__(self, name: str, points: List[Dict], access_level: str = "public", **kwargs):
        """
        Initializes a zone, accepting extra keyword arguments to be robust.
        The 'points' are expected as a list of dictionaries, e.g., [{'x': 10, 'y': 20}].
        """
        self.name = name
        self.access_level = access_level
        
        try:
            self.points = np.array([[p['x'], p['y']] for p in points], dtype=np.int32)
        except (KeyError, TypeError):
            logger.error(f"Failed to parse points for zone '{name}'. Invalid format.")
            self.points = np.array([], dtype=np.int32)

    def contains_point(self, point: Tuple[int, int]) -> bool:
        """Check if point is inside the zone"""
        if self.points.size == 0:
            return False
        return cv2.pointPolygonTest(self.points, point, False) >= 0

# ... (RiskScoreCalculator remains the same) ...

class SecurityMonitoringSystem:
    def __init__(self, model_path: str, strongsort_config: str, strongsort_weights: str, camera_id: str, zones_json: Optional[str]):
        self.camera_id = camera_id
        self.model_path = model_path
        self.strongsort_config = strongsort_config
        self.strongsort_weights = strongsort_weights
        
        self.yolo_model = None
        self.tracker = None
        self.risk_calculator = RiskScoreCalculator()
        
        self.person_trackers: Dict[int, PersonTracker] = {}
        
        self.loitering_threshold = 10.0
        self.risk_alert_threshold = 20.0
        self.critical_alert_threshold = 40.0
        
        self.frame_count = 0
        self.fps_counter = deque(maxlen=30)
        
        self.security_zones = []
        self.zone_original_width = 1280
        self.zone_original_height = 720
        if zones_json:
            try:
                # --- THIS IS THE FIX ---
                # This logic now correctly handles the format from the frontend.
                data_from_db = json.loads(zones_json)
                if isinstance(data_from_db, dict):
                    # The frontend saves an object like: { zones: {...}, original_width: ..., original_height: ... }
                    # This check makes the parsing robust.
                    zones_dict = data_from_db.get("zones", data_from_db)
                    
                    self.zone_original_width = data_from_db.get("original_width", 1280)
                    self.zone_original_height = data_from_db.get("original_height", 720)
                    
                    if isinstance(zones_dict, dict):
                        zone_list = list(zones_dict.values())
                        self.security_zones = [SecurityZone(**data) for data in zone_list]
                        logging.info(f"Successfully loaded {len(self.security_zones)} zones from database for camera '{self.camera_id}'.")
                    else:
                        logging.warning(f"The 'zones' key in the JSON for camera '{self.camera_id}' did not contain a dictionary.")
                else:
                    logging.warning(f"Zones JSON for camera '{self.camera_id}' was not a dictionary as expected.")
            except (json.JSONDecodeError, TypeError) as e:
                logging.error(f"Failed to parse zones JSON for camera '{self.camera_id}': {e}")
        else:
            logging.warning(f"No zones configured in database for camera '{self.camera_id}'.")

        self.initialize_models()
    
    def initialize_models(self):
        """Initializes YOLO and StrongSORT models."""
        try:
            logger.info("Loading YOLO model...")
            self.yolo_model = YOLO(self.model_path)
            logger.info(f"Model loaded. Class names: {self.yolo_model.names}")
            
            logger.info("Initializing StrongSORT tracker...")
            self.tracker = create_tracker(
                tracker_type='strongsort',
                tracker_config=Path(self.strongsort_config),
                reid_weights=Path(self.strongsort_weights),
                device='cuda' if torch.cuda.is_available() else 'cpu',
                half=False,
                per_class=False
            )
            logger.info("Tracker initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing models: {e}", exc_info=True)
            raise

    # In the SecurityMonitoringSystem class

    def _load_zones_for_camera(self) -> Tuple[List[SecurityZone], int, int]:
        """Loads zones and the original resolution they were drawn on."""
        camera_config = self.zone_manager.get_camera_config(self.camera_id)
        zones_data = camera_config.get("zones", [])
        
        # Load the resolution the zones were created with, providing a default
        original_width = camera_config.get("original_width", 1280)
        original_height = camera_config.get("original_height", 720)
        
        loaded_zones = [SecurityZone(**data) for data in zones_data]
        
        if loaded_zones:
            logging.info(f"Loaded {len(loaded_zones)} zones for camera '{self.camera_id}' (Original Res: {original_width}x{original_height}).")
        else:
            logging.warning(f"No zones found for camera '{self.camera_id}'.")
            
        return loaded_zones, original_width, original_height

    def detect_objects(self, frame: np.ndarray) -> List[Dict]:
        """Run YOLO detection on frame with lower confidence for critical objects"""
        # Use lower confidence for critical detection
        results = self.yolo_model(frame, verbose=False, conf=0.1)
        detections = []
        
        # --- VERBOSE DEBUG LOGGING - THIS IS THE KEY ---
        if results and results[0].boxes:
            raw_detection_count = len(results[0].boxes)
            if raw_detection_count > 0:
                logger.info(f"Frame {self.frame_count}: YOLO found {raw_detection_count} raw objects before filtering.")
                
                # This loop will now print every single thing the model thinks it sees
                for box in results[0].boxes:
                    class_name = self.yolo_model.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    logger.info(f"  -> Found: '{class_name}' with confidence {conf:.2f}")
        else:
            raw_detection_count = 0
        # --- END VERBOSE DEBUG LOGGING ---
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls = int(box.cls[0].cpu().numpy())
                    
                    class_name = self.yolo_model.names[cls] if cls < len(self.yolo_model.names) else "unknown"
                    
                    # Using the lowered threshold from before
                    min_confidence = 0.2
                    if class_name == 'person':
                        min_confidence = 0.10
                    elif class_name in ['knife', 'gun', 'weapon', 'scissors', 'bottle']:
                        min_confidence = 0.15
                    else:
                        min_confidence = 0.3
                    
                    if conf >= min_confidence:
                        detections.append({
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': float(conf),
                            'class': class_name,
                            'center': (int((x1 + x2) / 2), int((y1 + y2) / 2))
                        })

        if raw_detection_count > 0 and not detections:
            logger.warning(f"Frame {self.frame_count}: All {raw_detection_count} raw objects were filtered out by confidence thresholds.")
            
        return detections
    
    # In the SecurityMonitoringSystem class, replace this method

    def update_trackers(self, detections: List[Dict], current_time: float, frame: np.ndarray):
        """Updates person trackers with new detections using StrongSORT."""
        person_detections = [d for d in detections if d['class'] == 'person']
        if not person_detections:
            return

        dets_for_tracker = np.array([[*d['bbox'], d['confidence'], 0] for d in person_detections])
        if dets_for_tracker.size == 0:
            return
            
        try:
            tracks = self.tracker.update(dets_for_tracker, frame)
            if tracks.size > 0:
                for track in tracks:
                    x1, y1, x2, y2, track_id = map(int, track[:5])
                    
                    if track_id not in self.person_trackers:
                        self.person_trackers[track_id] = PersonTracker(track_id=track_id)
                    
                    center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                    bbox = [x1, y1, x2, y2]
                    
                    # --- UPDATED: Pass the bbox along with position and time ---
                    self.person_trackers[track_id].add_position(center, current_time, bbox)

        except Exception as e:
            logger.error(f"Error during tracker.update(): {e}", exc_info=True)
            
    def fallback_simple_tracking(self, person_detections: List[Dict], current_time: float):
        """Fallback simple tracking method"""
        logger.warning("Using fallback simple tracking")
        
        for detection in person_detections:
            track_id = self.assign_track_id(detection)
            
            if track_id not in self.person_trackers:
                self.person_trackers[track_id] = PersonTracker(track_id=track_id)
            
            tracker = self.person_trackers[track_id]
            tracker.add_position(detection['center'], current_time)
            
            # Detect carried objects
            self.detect_carried_objects(tracker, person_detections, detection['bbox'])
    
    def assign_track_id(self, detection: Dict) -> int:
        """Simplified track ID assignment - replace with proper tracking"""
        # This is a placeholder - use actual tracking algorithm
        center = detection['center']
        
        # Find closest existing tracker
        min_distance = float('inf')
        best_id = None
        
        for track_id, tracker in self.person_trackers.items():
            if not tracker.positions:
                continue
                
            last_pos = tracker.positions[-1]
            distance = math.sqrt((center[0] - last_pos[0])**2 + (center[1] - last_pos[1])**2)
            
            if distance < min_distance and distance < 100:  # 100 pixel threshold
                min_distance = distance
                best_id = track_id
        
        if best_id is not None:
            return best_id
        else:
            # Create new ID
            return max(self.person_trackers.keys(), default=0) + 1
    
    def detect_carried_objects(self, tracker: PersonTracker, detections: List[Dict], person_bbox: List[int]):
        """Detect objects carried by a person"""
        px1, py1, px2, py2 = person_bbox
        
        # Look for weapons or suspicious objects near the person
        for detection in detections:
            if detection['class'] in ['knife', 'gun', 'weapon', 'scissors', 'bottle']:
                dx1, dy1, dx2, dy2 = detection['bbox']
                
                # Check if object overlaps with person
                if not (dx2 < px1 or dx1 > px2 or dy2 < py1 or dy1 > py2):
                    tracker.detected_objects.append({
                        'object': detection['class'],
                        'confidence': detection['confidence'],
                        'timestamp': time.time()
                    })
    
    def analyze_behavior(self, person: PersonTracker, current_time: float):
        """Analyze person's behavior and generate risk events"""
        new_events = []
        
        # Check for intrusion
        intrusion_event = self.check_intrusion(person, current_time)
        if intrusion_event:
            new_events.append(intrusion_event)
        
        # Check for weapons
        weapon_event = self.check_weapons(person, current_time)
        if weapon_event:
            new_events.append(weapon_event)
        
        # Check for loitering
        loitering_event = self.check_loitering(person, current_time)
        if loitering_event:
            new_events.append(loitering_event)
        
        # Check movement patterns
        movement_event = self.check_movement_patterns(person, current_time)
        if movement_event:
            new_events.append(movement_event)
        
        # Add new events to tracker
        person.risk_events.extend(new_events)
        
        # Clean up old events (older than 10 minutes)
        person.risk_events = [
            event for event in person.risk_events 
            if current_time - event.timestamp < 600
        ]
    
    def check_intrusion(self, person: PersonTracker, current_time: float) -> Optional[RiskEvent]:
        """Check if person is in restricted area"""
        if not person.positions:
            return None
        
        current_pos = person.positions[-1]
        
        for zone in self.security_zones:
            if zone.contains_point(current_pos):
                if zone.access_level in ['restricted', 'critical']:
                    # Check if this is a new intrusion
                    recent_intrusions = [
                        e for e in person.risk_events 
                        if e.event_type == 'intrusion' and current_time - e.timestamp < 60
                    ]
                    
                    if not recent_intrusions:
                        return RiskEvent(
                            event_type='intrusion',
                            risk_score=15.0 if zone.access_level == 'critical' else 12.0,
                            confidence=0.9,
                            timestamp=current_time,
                            location=current_pos,
                            description=f"Unauthorized access to {zone.name}"
                        )
        
        return None
    
    def check_weapons(self, person: PersonTracker, current_time: float) -> Optional[RiskEvent]:
        """Check for weapon detection - FIXED VERSION with detailed explanation"""
        recent_weapons = [
            obj for obj in person.detected_objects 
            if current_time - obj['timestamp'] < 30 and obj['object'] in ['knife', 'gun', 'weapon', 'scissors', 'bottle']
        ]

        if recent_weapons:
            # Check if we already have a recent weapon event
            recent_events = [
                e for e in person.risk_events 
                if e.event_type == 'armed_person' and current_time - e.timestamp < 30
            ]

            if not recent_events:
                max_confidence = max(w['confidence'] for w in recent_weapons)
                weapon_type = recent_weapons[0]['object']

                # Construct detailed debug info
                debug_info = {
                    'event_type': 'armed_person',
                    'base_score': 0.0,  # will be filled in calculator
                    'confidence': max_confidence,
                    'confidence_factor': 0.0,  # will be filled in calculator
                    'time_factor': 0.0,        # will be filled in calculator
                    'duration': 0.0,
                    'description': f"Weapon detected: {weapon_type} (conf: {max_confidence:.2f})"
                }

                # Attach debug info to description
                return RiskEvent(
                    event_type='armed_person',
                    risk_score=0.0,
                    confidence=max_confidence,
                    timestamp=current_time,
                    location=person.positions[-1] if person.positions else (0, 0),
                    description=json.dumps(debug_info)
                )

        return None

    def check_loitering(self, person: PersonTracker, current_time: float) -> Optional[RiskEvent]:
        """Check for suspicious loitering behavior"""
        if len(person.positions) < 10:
            return None
        
        # Check if person has been stationary
        recent_positions = list(person.positions)[-10:]
        
        # Calculate movement within recent positions
        total_movement = 0
        for i in range(1, len(recent_positions)):
            dx = recent_positions[i][0] - recent_positions[i-1][0]
            dy = recent_positions[i][1] - recent_positions[i-1][1]
            total_movement += math.sqrt(dx*dx + dy*dy)
        
        avg_movement = total_movement / len(recent_positions)
        
        if avg_movement < 10:  # Very little movement
            if person.stationary_start is None:
                person.stationary_start = current_time
            elif current_time - person.stationary_start > self.loitering_threshold:
                # Check for existing loitering event
                recent_loitering = [
                    e for e in person.risk_events 
                    if e.event_type == 'suspicious_loitering' and current_time - e.timestamp < 60
                ]
                
                if not recent_loitering:
                    duration = current_time - person.stationary_start
                    return RiskEvent(
                        event_type='suspicious_loitering',
                        risk_score=8.0,
                        confidence=0.8,
                        timestamp=current_time,
                        duration=duration,
                        location=person.positions[-1],
                        description=f"Loitering for {duration:.0f} seconds"
                    )
        else:
            person.stationary_start = None
        
        return None
    
    def check_movement_patterns(self, person: PersonTracker, current_time: float) -> Optional[RiskEvent]:
        """Check for suspicious movement patterns"""
        pattern = person.get_movement_pattern()
        
        if pattern == "erratic":
            recent_erratic = [
                e for e in person.risk_events 
                if e.event_type == 'erratic_movement' and current_time - e.timestamp < 30
            ]
            
            if not recent_erratic:
                return RiskEvent(
                    event_type='erratic_movement',
                    risk_score=6.0,
                    confidence=0.7,
                    timestamp=current_time,
                    location=person.positions[-1] if person.positions else (0, 0),
                    description="Erratic movement pattern detected"
                )
        
        elif pattern == "running":
            recent_running = [
                e for e in person.risk_events 
                if e.event_type == 'running' and current_time - e.timestamp < 20
            ]
            
            if not recent_running:
                return RiskEvent(
                    event_type='running',
                    risk_score=5.0,
                    confidence=0.8,
                    timestamp=current_time,
                    location=person.positions[-1] if person.positions else (0, 0),
                    description="Fast movement detected"
                )
        
        return None
    
    # In the SecurityMonitoringSystem class

    def draw_visualization(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """Draws all visual elements, including scaled zones and per-person risk scores."""
        output_frame = frame.copy()
        display_height, display_width, _ = frame.shape

        # --- Zone Visualization with Scaling ---
        if self.zone_original_width > 0 and self.zone_original_height > 0:
            x_scale = display_width / self.zone_original_width
            y_scale = display_height / self.zone_original_height
            
            for zone in self.security_zones:
                if zone.points.size > 0:
                    scaled_points = (zone.points.astype(np.float32) * [x_scale, y_scale]).astype(np.int32)
                    cv2.polylines(output_frame, [scaled_points], True, self.get_zone_color(zone.access_level), 2)
                    text_pos = tuple(np.mean(scaled_points, axis=0, dtype=np.int32))
                    cv2.putText(output_frame, zone.name, (text_pos[0], text_pos[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # --- Per-Person Threat Visualization ---
        for person in self.person_trackers.values():
            if not person.positions or current_time - person.last_seen > 5:
                continue

            risk_score, primary_threat = self.risk_calculator.calculate_risk_score(person, current_time)
            color = self.get_risk_color(risk_score)
            
            if person.last_bbox:
                x1, y1, x2, y2 = person.last_bbox
                cv2.rectangle(output_frame, (x1, y1), (x2, y2), color, 2)
            if len(person.positions) > 1:
                points = np.array(list(person.positions), dtype=np.int32)
                cv2.polylines(output_frame, [points], False, color, 2)

            label_id = f"ID: {person.track_id}"
            label_risk = f"Risk: {risk_score:.1f}"
            
            text_pos_x = person.last_bbox[0]
            text_pos_y = person.last_bbox[1] - 10

            cv2.rectangle(output_frame, (text_pos_x, text_pos_y - 45), (text_pos_x + 150, text_pos_y + 10), color, -1)
            
            cv2.putText(output_frame, label_id, (text_pos_x + 5, text_pos_y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(output_frame, label_risk, (text_pos_x + 5, text_pos_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

            if primary_threat != "normal":
                cv2.putText(output_frame, primary_threat.upper(), (person.positions[-1][0] - 30, person.positions[-1][1] + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        self.draw_system_info(output_frame, current_time)

        return output_frame
    
    def calculate_fps(self) -> float:
        """Calculate FPS safely, handling potential empty or invalid time values."""
        if not self.fps_counter or len(self.fps_counter) < 2:
            return 0.0
        
        valid_times = [t for t in self.fps_counter if t is not None]
        
        if len(valid_times) < 2:
            return 0.0
        
        try:
            time_diff = max(valid_times) - min(valid_times)
            if time_diff <= 0:
                return 0.0
            # FPS is the number of frames divided by the time elapsed
            return len(valid_times) / time_diff
        except (TypeError, ValueError):
            # This handles any unexpected data types in the deque
            return 0.0
    
    def get_zone_color(self, access_level: str) -> Tuple[int, int, int]:
        """Get color for security zone based on access level"""
        colors = {
            'public': (0, 255, 0),      # Green
            'monitored': (0, 255, 255), # Yellow
            'restricted': (0, 165, 255), # Orange
            'critical': (0, 0, 255)     # Red
        }
        return colors.get(access_level, (128, 128, 128))
    
    def get_risk_color(self, risk_score: float) -> Tuple[int, int, int]:
        """Get color based on risk score"""
        if risk_score < 10:
            return (0, 255, 0)      # Green - Low risk
        elif risk_score < self.risk_alert_threshold:
            return (0, 255, 255)    # Yellow - Medium risk
        elif risk_score < self.critical_alert_threshold:
            return (0, 165, 255)    # Orange - High risk
        else:
            return (0, 0, 255)      # Red - Critical risk  
    
    def draw_system_info(self, frame: np.ndarray, current_time: float):
        """Draw system information overlay"""
        # FPS counter
        # --- FIXED: Removed the duplicate "fps =" ---
        fps = self.calculate_fps()
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Active trackers
        active_trackers = len([p for p in self.person_trackers.values() if current_time - p.last_seen < 5])
        cv2.putText(frame, f"Tracked: {active_trackers}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Security zones count (only show if zones exist)
        if self.security_zones:
            cv2.putText(frame, f"Zones: {len(self.security_zones)}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            alert_y_offset = 120
        else:
            alert_y_offset = 90
        
        # Alert status
        high_risk_count = len([
            p for p in self.person_trackers.values() 
            if self.risk_calculator.calculate_risk_score(p, current_time)[0] > self.risk_alert_threshold
            and current_time - p.last_seen < 5
        ])
        
        if high_risk_count > 0:
            cv2.putText(frame, f"ALERTS: {high_risk_count}", (10, alert_y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Timestamp
        timestamp = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def process_alerts(self, current_time: float) -> Tuple[List[Dict], List[Dict]]:
        """
        Determines what needs to be logged and what needs to be notified.
        Returns two lists:
        1. incidents_to_log: For every significant threat detected in the frame.
        2. reportable_alerts: For external notifications (only when threat state changes).
        """
        incidents_to_log = []
        reportable_alerts = []
        
        for person in self.person_trackers.values():
            if person.last_seen is None or current_time - person.last_seen > 5:
                continue
            
            try:
                risk_score, primary_threat = self.risk_calculator.calculate_risk_score(person, current_time)
                
                person.status = primary_threat
                is_significant_threat = risk_score >= self.risk_alert_threshold

                if is_significant_threat:
                    # --- LOGGING LOGIC (Original Style) ---
                    # Flag an incident for logging on every frame a threat is active.
                    path_data_json = json.dumps([{"x": p[0], "y": p[1]} for p in person.positions])
                    incident_data = {
                        "timestamp": datetime.fromtimestamp(current_time),
                        "track_id": person.track_id,
                        "risk_score": risk_score,
                        "primary_threat": primary_threat,
                        "location_x": person.positions[-1][0] if person.positions else None,
                        "location_y": person.positions[-1][1] if person.positions else None,
                        "details": json.dumps([e.event_type for e in person.risk_events]),
                        "path_data": path_data_json
                    }
                    incidents_to_log.append(incident_data)
                        
                    # --- NOTIFICATION LOGIC (State-Based) ---
                    # Only flag an alert for notification if the threat type has changed.
                    if primary_threat != person.last_notified_threat:
                        logger.info(f"Flagging new notification for track {person.track_id}: '{primary_threat}'")
                        alert = {
                            'level': 'CRITICAL' if risk_score >= self.critical_alert_threshold else 'HIGH',
                            'track_id': person.track_id,
                            'risk_score': risk_score,
                            'threat_type': primary_threat,
                            'location': person.positions[-1] if person.positions else (0, 0),
                            'timestamp': current_time,
                        }
                        reportable_alerts.append(alert)
                        person.last_notified_threat = primary_threat
                
                else: # Threat is resolved, reset notification state.
                    if person.last_notified_threat != "normal":
                        logger.info(f"Threat for track {person.track_id} resolved. Resetting state.")
                        person.last_notified_threat = "normal"

            except Exception as e:
                logger.warning(f"Error processing alerts for track {person.track_id}: {e}")
                continue
        
        return incidents_to_log, reportable_alerts
    
    def handle_alert(self, alert: Dict):
        """Handle a security alert"""
        logger.warning(f"Security Alert - {alert['level']}: Track {alert['track_id']} "
                      f"Risk: {alert['risk_score']:.1f} Threat: {alert['threat_type']}")
        
        # Here you can add integrations:
        # - Send notifications
        # - Trigger alarms
        # - Send to security dashboard
        # - Email/SMS alerts
        # - Integration with access control systems
    
    def cleanup_trackers(self, current_time: float):
        """Remove inactive trackers to free memory"""
        if current_time is None:
            return
        
        inactive_threshold = 30  # seconds
        
        # Reset tracker every 5 minutes to prevent memory issues
        if not hasattr(self, 'last_tracker_reset') or self.last_tracker_reset is None:
            self.last_tracker_reset = current_time
        elif current_time - self.last_tracker_reset > 300:  # 5 minutes
            try:
                if hasattr(self.tracker, 'reset'):
                    self.tracker.reset()
                self.last_tracker_reset = current_time
                logger.info("Tracker reset performed")
            except Exception as e:
                logger.warning(f"Failed to reset tracker: {e}")
        
        # Remove inactive trackers
        inactive_ids = []
        for track_id, tracker in self.person_trackers.items():
            if tracker.last_seen is None or current_time - tracker.last_seen > inactive_threshold:
                inactive_ids.append(track_id)
        
        for track_id in inactive_ids:
            del self.person_trackers[track_id]

    def get_system_statistics(self, current_time: float) -> Dict:
        """Get current system statistics"""
        active_trackers = [p for p in self.person_trackers.values() if current_time - p.last_seen < 5]
        
        risk_distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        
        for person in active_trackers:
            risk_score, _ = self.risk_calculator.calculate_risk_score(person, current_time)
            
            if risk_score < 10:
                risk_distribution['low'] += 1
            elif risk_score < 25:
                risk_distribution['medium'] += 1
            elif risk_score < 50:
                risk_distribution['high'] += 1
            else:
                risk_distribution['critical'] += 1
        
        return {
            'active_trackers': len(active_trackers),
            'total_trackers': len(self.person_trackers),
            'risk_distribution': risk_distribution,
            'fps': self.calculate_fps(),
            'frame_count': self.frame_count,
            'zones': len(self.security_zones)
        }
    
    # In the SecurityMonitoringSystem class


    def run_video_analysis(self, video_source, output_path: str = None):
        """
        Runs the full security analysis with a user-friendly display and saves the output to a video file.
        """
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            logger.error(f"FATAL: Failed to open video source: {video_source}")
            return

        # --- Display Configuration ---
        DISPLAY_WIDTH, DISPLAY_HEIGHT = 1280, 720
        window_name = f'Security Monitoring - {self.camera_id}'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        
        # --- Video Saving Setup ---
        writer = None
        if output_path:
            # Get the frames per second (FPS) from the source video
            fps = cap.get(cv2.CAP_PROP_FPS)
            # If FPS is not available (e.g., some IP cameras), use a default
            if fps is None or fps == 0:
                fps = 25.0
                logger.warning(f"Could not determine video FPS. Defaulting to {fps} FPS for output.")
            
            # Define the codec and create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Use 'mp4v' for .mp4 files
            writer = cv2.VideoWriter(output_path, fourcc, fps, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
            logger.info(f"Output video will be saved to: {output_path}")

        # --- Main Loop ---
        is_fullscreen = False
        logger.info(f"Starting monitoring for '{self.camera_id}'. Press 'q' to quit.")
        print("  Press 'f' to toggle full-screen.")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.info("End of video stream.")
                    break
                
                # 1. Resize the frame to our standard display size
                resized_frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
                
                # 2. Run the full processing pipeline on the resized frame
                processed_frame = self.process_frame(resized_frame, time.time())
                
                # 3. Write the processed frame to the output file (if enabled)
                if writer:
                    writer.write(processed_frame)
                
                # 4. Display the result
                cv2.imshow(window_name, processed_frame)
                
                # 5. Handle user input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('f'):
                    is_fullscreen = not is_fullscreen
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if is_fullscreen else cv2.WINDOW_NORMAL)
        finally:
            # --- Cleanup ---
            cap.release()
            # 6. IMPORTANT: Release the writer to finalize the video file
            if writer:
                writer.release()
                logger.info("Output video saved successfully.")
            cv2.destroyAllWindows()
            logger.info(f"Stopped monitoring for '{self.camera_id}'.")

    # In the SecurityMonitoringSystem class, replace this method

    def process_frame(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """The main processing pipeline for a single frame."""
        # 1. Detect all objects in the frame
        detections = self.detect_objects(frame)

        # 2. Update person trackers with the new detections
        self.update_trackers(detections, current_time, frame)

        # 3. Analyze the behavior of each tracked person
        for person in self.person_trackers.values():
            if current_time - person.last_seen < 5:
                self.analyze_behavior(person, current_time)
                if person.last_bbox:
                    self.detect_carried_objects(person, detections, person.last_bbox)

        # 4. Draw the main visualization
        output_frame = self.draw_visualization(frame, current_time)

        # 5. Get a list of currently active threats for visualization purposes only
        active_alerts_to_draw = []
        for person in self.person_trackers.values():
            if person.status != "normal" and (current_time - person.last_seen < 5):
                risk_score, primary_threat = self.risk_calculator.calculate_risk_score(person, current_time)
                if risk_score >= self.risk_alert_threshold:
                    active_alerts_to_draw.append({
                        'level': 'CRITICAL' if risk_score >= self.critical_alert_threshold else 'HIGH',
                        'track_id': person.track_id,
                        'threat_type': primary_threat,
                        'risk_score': risk_score,
                    })

        # 6. If there are active threats, draw the notifications at the top
        if active_alerts_to_draw:
            self.draw_alert_notifications(output_frame, active_alerts_to_draw)

        return output_frame
    
    def draw_alert_notifications(self, frame: np.ndarray, alerts: List[Dict]):
        """Draw alert notifications on frame"""
        y_offset = 150  # Adjusted y-offset to not overlap with other info

        for i, alert in enumerate(alerts[:5]):  # Show max 5 alerts
            level = alert['level']
            color = (0, 0, 255) if level == 'CRITICAL' else (0, 165, 255)

            text = f"{level}: Track {alert['track_id']} - {alert['threat_type']} (Risk: {alert['risk_score']:.1f})"
            cv2.putText(frame, text, (10, y_offset + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Draw blinking effect for critical alerts
            if level == 'CRITICAL' and int(time.time() * 2) % 2:
                cv2.rectangle(frame, (5, y_offset + i * 30 - 20),
                             (frame.shape[1] - 5, y_offset + i * 30 + 10), color, 2)
    
    def detect_carried_objects(self, tracker: PersonTracker, detections: List[Dict], person_bbox: List[int]):
        """Detect objects carried by a person - ENHANCED VERSION"""
        px1, py1, px2, py2 = person_bbox
        
        # Expand person bbox slightly for better detection
        margin = 20
        px1 -= margin
        py1 -= margin
        px2 += margin
        py2 += margin
        
        # Look for weapons or suspicious objects near the person
        for detection in detections:
            if detection['class'] in ['knife', 'gun', 'weapon', 'scissors', 'bottle']:
                dx1, dy1, dx2, dy2 = detection['bbox']
                
                # Check if object overlaps with expanded person bbox
                if not (dx2 < px1 or dx1 > px2 or dy2 < py1 or dy1 > py2):
                    # Log the detection
                    obj_info = {
                        'object': detection['class'],
                        'confidence': detection['confidence'],
                        'timestamp': time.time()
                    }
                    tracker.detected_objects.append(obj_info)
                    
                    logger.warning(f"WEAPON DETECTED: {detection['class']} "
                                f"(conf: {detection['confidence']:.2f}) "
                                f"for track {tracker.track_id}")


# Configuration and Usage Example
def main():
    """Main entry point for the application."""

    MODEL_PATH = r"G:\Downloads\cognizant\Mock Hackathon\tracking\backend\yolov8_best.onnx"
    STRONGSORT_CONFIG = r"G:\Downloads\cognizant\Mock Hackathon\tracking\backend\Yolov5_StrongSORT_OSNet\boxmot\configs\strongsort.yaml"
    STRONGSORT_WEIGHTS = r"G:\Downloads\cognizant\Mock Hackathon\tracking\backend\Yolov5_StrongSORT_OSNet\boxmot\osnet_x0_25_msmt17.onnx"

    zone_manager = ZoneManager("camera_zones.json")
    configured_cameras = list(zone_manager.config.keys())

    if not configured_cameras:
        print("\n[ERROR] No cameras have been configured yet.")
        print("Please run 'python zone_manager.py' first to set up your cameras and zones.")
        return

    print("\n--- Select a Camera to Monitor ---")
    for i, cam_id in enumerate(configured_cameras):
        print(f"  {i+1}: {cam_id}")
    
    try:
        choice_input = input(f"Enter your choice (1-{len(configured_cameras)}): ")
        choice = int(choice_input) - 1
        
        if not 0 <= choice < len(configured_cameras):
            raise ValueError("Choice out of range.")
        
        selected_camera_id = configured_cameras[choice]
        camera_config = zone_manager.config[selected_camera_id]
        video_source = camera_config['video_source']
        
        if isinstance(video_source, str) and video_source.isdigit():
            video_source = int(video_source)

    except (ValueError, IndexError):
        print("Invalid choice. Please enter a valid number from the list. Exiting.")
        return

    try:
        security_system = SecurityMonitoringSystem(
            model_path=MODEL_PATH,
            strongsort_config=STRONGSORT_CONFIG,
            strongsort_weights=STRONGSORT_WEIGHTS,
            camera_id=selected_camera_id
        )
        
        security_system.run_video_analysis(
            video_source=video_source,
            output_path=f"{selected_camera_id}_output.mp4"
        )
        
    except Exception as e:
        logger.error(f"A critical error occurred while running the security system: {e}", exc_info=True)

if __name__ == "__main__":
    main()
