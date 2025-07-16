from .database import SessionLocal

def get_db():
    """
    A dependency function that provides a database session to API endpoints.
    It ensures that the database connection is always closed after a request is finished.
    This is identical to the one in database.py and is placed here for structural clarity
    as the application grows.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# You could add other dependencies here in the future, for example:
#
# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     # Logic to get user from token
#     ...
#     return user
