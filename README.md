# ThreatWatch AI Security Dashboard

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-blue?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.2-purple?style=for-the-badge&logo=vite)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com/)

ThreatWatch is a full-stack, AI-powered security monitoring application designed for real-time threat detection and analysis. It leverages computer vision to analyze video streams, identify potential threats, track subjects, and provide a comprehensive suite of tools for monitoring, incident management, and reporting.

## Key Features

### Core Threat Detection & Monitoring
* **Real-time Video Analysis**: The backend processes multiple video streams concurrently, using YOLOv8 for object detection and StrongSORT for tracking individuals.
* **AI-Powered Risk Assessment**: A sophisticated system calculates a dynamic risk score for tracked individuals based on behaviors like intrusion into restricted zones, suspicious loitering, and detection of potential weapons.
* **Live Dashboard**: A central dashboard provides a live, low-latency video feed from any selected camera via WebSockets.
* **Interactive Zone Editor**: Users can draw, name, and manage polygonal detection zones directly on a camera snapshot. These zones are used to trigger intrusion alerts.
* **Real-time Statistics**: The dashboard displays live stats for each camera, including Frames Per Second (FPS), active trackers, and a distribution of current risk levels.

### Incident Management & Reporting
* **Comprehensive Incident Log**: All detected threats are logged as incidents, which can be reviewed and filtered by camera.
* **Snapshot Gallery**: The system automatically captures and stores snapshots in Azure Blob Storage when incidents are created. These can be viewed in a gallery for each incident.
* **Behavior Path Visualization**: View the tracked movement path of an individual during an incident, drawn over the initial snapshot.
* **Alerts & Notifications**: Delivers critical alerts to users via multiple channels, including Email (SMTP), SMS (Twilio), and Telegram, complete with snapshot images.
* **Data Export**: Export incident logs to CSV format based on a selected date range and camera.
* **Complaint System**: A built-in feature allows users to file a formal complaint via email for a specific incident, automatically attaching relevant details and evidence.

### User and System Management
* **Secure Authentication**: User authentication is handled with JWT (JSON Web Tokens), including password hashing.
* **Role-Based Access Control**: The system distinguishes between standard users and administrators, with a dedicated admin page for user management.
* **Camera & Profile Settings**: Users can manage their camera configurations and personal notification settings (phone number, Telegram linking) through a dedicated settings page.

## Technology Stack

### Backend
* **Framework**: FastAPI
* **Database**: SQLAlchemy ORM (compatible with databases like PostgreSQL, SQL Server, etc.)
* **AI / Computer Vision**: Python, OpenCV, PyTorch, Ultralytics (YOLOv8), ONNX Runtime
* **Authentication**: Passlib (for hashing), Python-JOSE (for JWT)
* **Real-time**: WebSockets
* **File Storage**: Azure Storage Blob

### Frontend
* **Framework**: React 18
* **Build Tool**: Vite
* **Styling**: Tailwind CSS
* **Routing**: React Router DOM
* **API Communication**: Axios
* **UI Components**: Lucide React (Icons), Sonner (Notifications), Recharts (Charts)

## Setup and Installation

### Prerequisites
* Git
* Python 3.10+
* Node.js 18+ and npm

### 1. Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd your-project-root
    ```

2.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

3.  **Create and activate a virtual environment:**
    * On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    * On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

4.  **Install dependencies:**
    The project includes a script to handle PyTorch installation based on GPU availability.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in the `backend/` directory by copying the example below. Fill in your actual credentials.
    ```dotenv
    # .env
    DATABASE_URL="<your-database-connection-string>"
    SECRET_KEY="<a-very-strong-and-secret-key>"
    AZURE_STORAGE_CONNECTION_STRING="<your-azure-blob-storage-connection-string>"

    # AI Model Paths (these are the default paths in the project)
    YOLO_MODEL_PATH="yolov8_best.onnx"
    STRONGSORT_CONFIG_PATH="Yolov5_StrongSORT_OSNet/boxmot/configs/strongsort.yaml"
    STRONGSORT_WEIGHTS_PATH="Yolov5_StrongSORT_OSNet/boxmot/osnet_x0_25_msmt17.onnx"

    # Notification Services (Optional)
    TWILIO_ACCOUNT_SID=""
    TWILIO_AUTH_TOKEN=""
    TWILIO_FROM_NUMBER=""
    TELEGRAM_BOT_TOKEN=""
    SMTP_SERVER=""
    SMTP_PORT=587
    SMTP_USERNAME=""
    SMTP_PASSWORD=""
    ```

6.  **Run the application:**
    The database tables will be created automatically on the first run.
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The backend API will be available at `http://localhost:8000`.

### 2. Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd ../frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the development server:**
    ```bash
    npm run dev
    ```
    The frontend application will be available at `http://localhost:5173` (or another port if 5173 is busy).
