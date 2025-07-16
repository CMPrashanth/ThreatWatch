import cv2
import numpy as np
import json
from pathlib import Path
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ZoneManager:
    """Handles loading and saving zone configurations from a JSON file."""
    def __init__(self, config_path: str = "camera_zones.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.exists() and self.config_path.stat().st_size > 0:
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from {self.config_path}. Starting fresh.")
        return {}

    def get_camera_config(self, camera_id: str) -> dict:
        return self.config.get(camera_id, {})

    def save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logging.info(f"Configuration successfully saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")
    
    def delete_camera(self, camera_id: str):
        """Deletes a camera configuration and saves the file."""
        if camera_id in self.config:
            del self.config[camera_id]
            self.save_config()
            logging.info(f"Camera configuration for '{camera_id}' deleted.")
            return True
        logging.warning(f"Attempted to delete non-existent camera ID: {camera_id}")
        return False

class ZoneCreator:
    """A robust, fully interactive tool to draw, edit, and define security zones."""
    def __init__(self, video_source, camera_id: str, config_path: str = "camera_zones.json"):
        self.video_source = video_source
        self.camera_id = camera_id
        self.zone_manager = ZoneManager(config_path)
        
        camera_config = self.zone_manager.get_camera_config(self.camera_id)
        self.zones = camera_config.get("zones", [])
        
        self.window_name = f"Zone Creator: {self.camera_id}"
        self.state = "NORMAL"
        self.is_paused = True
        
        self.current_points = []
        self.input_text = ""
        self.prompt_message = ""
        self.temp_zone_points = []
        self.access_levels = ["public", "monitored", "restricted", "critical"]
        self.original_frame_shape = None

    def _handle_mouse(self, event, x, y, flags, param):
        if self.state == "DRAWING" and event == cv2.EVENT_LBUTTONDOWN:
            self.current_points.append([x, y])
        elif self.state == "DELETING" and event == cv2.EVENT_LBUTTONDOWN:
            self._delete_zone_at_point((x, y))

    def _delete_zone_at_point(self, point: tuple):
        for i, zone in reversed(list(enumerate(self.zones))):
            if cv2.pointPolygonTest(np.array(zone['points']), point, False) >= 0:
                deleted_zone = self.zones.pop(i)
                logging.info(f"Zone '{deleted_zone['name']}' deleted.")
                return

    def _start_naming_zone(self, points: list):
        if len(points) < 3: return
        self.state = "NAMING"
        self.temp_zone_points = points
        self.input_text = ""
        self.prompt_message = "Enter Zone Name (then press ENTER):"

    def _draw_ui(self, frame):
        # Draw existing zones
        for zone in self.zones:
            points = np.array(zone['points'], np.int32)
            color = (0, 0, 255) if self.state == "DELETING" else (0, 255, 0)
            cv2.polylines(frame, [points], True, color, 2)
            text_pos = tuple(np.mean(points, axis=0, dtype=np.int32))
            cv2.putText(frame, f"{zone['name']} [{zone['access_level'][0].upper()}]", text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        if self.state == "DRAWING" and self.current_points:
            cv2.polylines(frame, [np.array(self.current_points)], False, (0, 165, 255), 2)

        if self.state in ["NAMING", "SELECTING_ACCESS"]:
            h, w, _ = frame.shape
            box_x, box_y, box_w, box_h = w // 4, h // 3, w // 2, h // 3
            cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (20, 20, 20), -1)
            cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 255, 255), 2)
            cv2.putText(frame, self.prompt_message, (box_x + 15, box_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            if self.state == "NAMING":
                cv2.putText(frame, self.input_text + "_", (box_x + 15, box_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            elif self.state == "SELECTING_ACCESS":
                for i, level in enumerate(self.access_levels):
                    cv2.putText(frame, f"{i+1}. {level.capitalize()}", (box_x + 15, box_y + 80 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        self._draw_instructions(frame)

    def _draw_instructions(self, frame):
        y_offset = 30
        status_text = f"MODE: {self.state} | {'PAUSED' if self.is_paused else 'PLAYING'}"
        cv2.putText(frame, status_text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        instructions = {
            "NORMAL": ["N: New Zone", "D: Delete Zone", "F: Full Frame Zone", "SPACE: Play/Pause", "S: Save", "Q: Quit"],
            "DRAWING": ["Left-Click: Add Point", "ENTER: Finish Zone", "ESC: Cancel"],
            "DELETING": ["Left-Click: Delete Zone", "D or ESC: Exit Delete Mode"],
            "NAMING": ["Type name", "ENTER: Confirm", "ESC: Cancel"],
            "SELECTING_ACCESS": ["Select 1-4", "ESC: Cancel"]
        }
        for i, text in enumerate(instructions.get(self.state, [])):
            cv2.putText(frame, text, (10, y_offset + 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def run(self):
        """
        Runs the main loop for the Zone Creator, handling video streams robustly
        and maintaining a standard window size.
        """
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            print(f"Error: Could not open video source: {self.video_source}")
            return

        # --- Standard Display Size ---
        DISPLAY_WIDTH, DISPLAY_HEIGHT = 1280, 720
        cv2.namedWindow(self.window_name)
        cv2.resizeWindow(self.window_name, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        cv2.setMouseCallback(self.window_name, self._handle_mouse)

        # --- Fetch the first valid frame ---
        frame = None
        while frame is None:
            ret, frame = cap.read()
            if not ret:
                print("Attempting to connect to the video stream... Ensure the camera is active.")
                cv2.waitKey(1000) # Wait 1 second before retrying
                # Provide a way to exit if connection fails repeatedly
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return

        self.original_frame_shape = frame.shape
        print("Successfully connected to video source.")

        while True:
            if not self.is_paused:
                ret, current_frame = cap.read()
                if ret:
                    frame = current_frame # Only update the main frame if read was successful
            
            # --- Ensure we always have a valid frame to display ---
            if frame is None:
                print("Lost video stream. Attempting to reconnect...")
                # Create a black frame with an error message
                display_frame = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)
                cv2.putText(display_frame, "Connection Lost...", (100, DISPLAY_HEIGHT // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            else:
                # --- Resize frame for consistent display ---
                display_frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))

            # Draw the UI on the resized frame
            self._draw_ui(display_frame)
            cv2.imshow(self.window_name, display_frame)

            key = cv2.waitKey(30 if not self.is_paused else 0) & 0xFF

            if key == ord('q'):
                break
            if key == ord('s'):
                # Note: Points are saved relative to the original frame size.
                # Here we assume points were drawn on the resized view. We need to scale them back.
                h_orig, w_orig, _ = self.original_frame_shape
                h_display, w_display = DISPLAY_HEIGHT, DISPLAY_WIDTH
                
                for zone in self.zones:
                    for point in zone['points']:
                        point[0] = int(point[0] * w_orig / w_display)
                        point[1] = int(point[1] * h_orig / h_display)

                self.zone_manager.config[self.camera_id] = {
                    "video_source": str(self.video_source), # Save as string
                    "original_height": self.original_frame_shape[0],
                    "original_width": self.original_frame_shape[1],
                    "zones": self.zones
                }
                self.zone_manager.save_config()
                print("Configuration saved successfully!")
                break
                
            if key == ord(' '):
                self.is_paused = not self.is_paused

            # --- State machine logic from your original code ---
            if self.state == "NORMAL":
                if key == ord('n'): self.state = "DRAWING"; self.current_points = []
                elif key == ord('d'): self.state = "DELETING"
                elif key == ord('f'):
                    self._start_naming_zone([[0, 0], [DISPLAY_WIDTH - 1, 0], [DISPLAY_WIDTH - 1, DISPLAY_HEIGHT - 1], [0, DISPLAY_HEIGHT - 1]])
            elif self.state == "DRAWING":
                if key == 13: self._start_naming_zone(self.current_points)
                elif key == 27: self.state = "NORMAL"; self.current_points = []
            elif self.state == "DELETING":
                if key == ord('d') or key == 27: self.state = "NORMAL"
            elif self.state == "NAMING":
                if key == 27: self.state = "NORMAL"
                elif key == 8: self.input_text = self.input_text[:-1]
                elif key == 13 and self.input_text:
                    self.state = "SELECTING_ACCESS"
                    self.prompt_message = f"Access Level for '{self.input_text}':"
                elif 32 <= key <= 126: self.input_text += chr(key)
            elif self.state == "SELECTING_ACCESS":
                if key == 27: self.state = "NORMAL"
                elif ord('1') <= key <= ord(str(len(self.access_levels))):
                    level = self.access_levels[key - ord('1')]
                    self.zones.append({"name": self.input_text, "access_level": level, "points": self.temp_zone_points})
                    self.state = "NORMAL"

        cap.release()
        cv2.destroyAllWindows()

def interactive_setup_main():
    """The main interactive utility for creating, editing, and deleting camera zone configs."""
    print("--- Security Zone Configuration Utility ---")
    
    while True:
        # Refresh the config manager in each loop to get the latest data
        zone_manager = ZoneManager()
        
        print("\n--- Main Menu ---")
        print("1. Create new camera config")
        print("2. Edit existing camera config")
        print("3. Delete camera config")
        print("4. Exit")
        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            camera_id = input("\nEnter a unique Camera ID (or type 'c' to cancel): ")
            if camera_id.lower() in ['c', 'cancel']:
                print("Creation cancelled.")
                continue
            if not camera_id:
                print("Camera ID cannot be empty.")
                continue
            if camera_id in zone_manager.config:
                print(f"Error: Camera ID '{camera_id}' already exists.")
                continue
                
            video_source = input("Enter Video Source (URL, path, or '0') (or type 'c' to cancel): ")
            if video_source.lower() in ['c', 'cancel']:
                print("Creation cancelled.")
                continue
            if video_source.isdigit():
                video_source = int(video_source)
                
            creator = ZoneCreator(video_source=video_source, camera_id=camera_id)
            creator.run()

        elif choice == '2':
            cameras = list(zone_manager.config.keys())
            if not cameras:
                print("\nNo existing configurations found to edit.")
                continue
            
            print("\n--- Select Camera to Edit ---")
            for i, cam_id in enumerate(cameras):
                print(f"  {i+1}: {cam_id}")
            
            edit_choice_input = input(f"Enter choice (1-{len(cameras)}) or 'c' to cancel: ")
            if edit_choice_input.lower() in ['c', 'cancel']:
                print("Edit cancelled.")
                continue
            
            try:
                edit_choice = int(edit_choice_input) - 1
                if not 0 <= edit_choice < len(cameras):
                    raise ValueError
                    
                cam_id = cameras[edit_choice]
                config = zone_manager.get_camera_config(cam_id)
                video_source = config.get('video_source')
                
                if not video_source:
                    print(f"Error: Video source not found for {cam_id}")
                    continue
                
                if isinstance(video_source, str) and video_source.isdigit():
                    video_source = int(video_source)
                    
                creator = ZoneCreator(video_source=video_source, camera_id=cam_id)
                creator.run()
            except (ValueError, IndexError):
                print("Invalid choice.")

        elif choice == '3':
            cameras = list(zone_manager.config.keys())
            if not cameras:
                print("\nNo existing configurations found to delete.")
                continue

            print("\n--- Select Camera to Delete ---")
            for i, cam_id in enumerate(cameras):
                print(f"  {i+1}: {cam_id}")

            delete_choice_input = input(f"Enter choice (1-{len(cameras)}) or 'c' to cancel: ")
            if delete_choice_input.lower() in ['c', 'cancel']:
                print("Deletion cancelled.")
                continue
            
            try:
                delete_choice_idx = int(delete_choice_input) - 1
                if not 0 <= delete_choice_idx < len(cameras):
                    raise ValueError
                
                cam_to_delete = cameras[delete_choice_idx]
                
                confirm = input(f"WARNING: Are you sure you want to permanently delete '{cam_to_delete}'? (y/n): ").lower()
                
                if confirm == 'y':
                    if zone_manager.delete_camera(cam_to_delete):
                        print(f"Successfully deleted '{cam_to_delete}'.")
                else:
                    print("Deletion cancelled.")
            except (ValueError, IndexError):
                print("Invalid choice.")

        elif choice == '4':
            print("Exiting utility.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")

if __name__ == '__main__':
    interactive_setup_main()
