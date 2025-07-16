import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# --- Database Configuration ---

# Load environment variables from a .env file
# Your .env file should contain a line like:
# DATABASE_URL="mssql+pyodbc://<user>:<password>@<server-name>.database.windows.net/<db-name>?driver=ODBC+Driver+17+for+SQL+Server"
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL set for the connection. Please check your .env file.")

# The create_engine() function is the starting point for any SQLAlchemy application.
# It establishes a connection pool to the database.
# `connect_args` can be used to pass driver-specific parameters.
# For Azure SQL, it's good practice to set a timeout.
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"timeout": 30}
    )
except Exception as e:
    print(f"Error creating database engine: {e}")
    # In a real app, you might want to handle this more gracefully
    exit(1)


# SessionLocal is a factory for creating new Session objects.
# A Session is the primary interface for all database operations.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is a factory for creating declarative base classes.
# Our ORM models (database tables) will inherit from this class.
Base = declarative_base()


# --- Dependency for FastAPI ---
def get_db():
    """
    A dependency function that provides a database session to API endpoints.
    It ensures that the database connection is always closed after a request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

