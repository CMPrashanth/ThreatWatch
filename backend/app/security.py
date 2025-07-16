from passlib.context import CryptContext

# --- Password Hashing Setup ---

# We use CryptContext from the passlib library to handle password hashing.
# "bcrypt" is the recommended hashing algorithm.
# The 'schemes' list specifies the hashing algorithms to be used.
# 'deprecated="auto"' means that older hashes will be automatically updated
# if a user logs in with an older hash format.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.

    Args:
        plain_password: The password entered by the user during login.
        hashed_password: The hashed password stored in the database.

    Returns:
        True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password.

    Args:
        password: The plain-text password from the user registration form.

    Returns:
        A securely hashed version of the password.
    """
    return pwd_context.hash(password)

