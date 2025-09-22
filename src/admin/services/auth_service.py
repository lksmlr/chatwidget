from fastapi import HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer
from src.admin.database import Database
from src.admin.models.user import User
from src.settings import Settings
from typing import Optional, Tuple
import jwt
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OAuth2 with the correct token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class AuthService:
    """Handles authentication and authorization for the admin frontend"""

    _settings = Settings()
    SECRET_KEY = _settings.secret_key.get_secret_value()
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    @staticmethod
    async def create_access_token(data: dict) -> str:
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(
                minutes=AuthService.ACCESS_TOKEN_EXPIRE_MINUTES
            )
            to_encode.update({"exp": expire})
            logger.info(f"Creating access token for user: {data.get('sub')}")
            encoded_jwt = jwt.encode(
                payload=to_encode,
                key=AuthService.SECRET_KEY,
                algorithm=AuthService.ALGORITHM,
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not create access token")

    @staticmethod
    async def authenticate_user(
        username: str, password: str
    ) -> Tuple[bool, Optional[User], str]:
        """Validates user credentials and returns (success, user, message)"""
        try:
            logger.info(f"Attempting to authenticate user: {username}")
            db = Database()
            user_data = await db.get_user(username)

            if not user_data:
                logger.warning(f"User not found: {username}")
                return False, None, "Invalid username or password"

            user = User.from_dict(user_data)
            if user.verify_password(password):
                logger.info(f"User authenticated successfully: {username}")
                return True, user, "Login successful!"

            logger.warning(f"Invalid password for user: {username}")
            return False, None, "Invalid username or password"
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False, None, f"Authentication error: {str(e)}"

    @staticmethod
    async def verify_user(request: Request) -> Optional[User]:
        """Verifies if the user has valid session data in cookies"""
        try:
            # Get user data from session cookie
            user_id = request.cookies.get("user_id")
            username = request.cookies.get("username")
            role = request.cookies.get("user_role")

            if not user_id or not username or not role:
                logger.warning("Missing session data in cookies")
                return None

            logger.info(f"Found session data for user: {username}")

            # Verify user exists in database
            db = Database()
            user_data = await db.get_user(username)

            if not user_data:
                logger.warning(f"User from session not found in database: {username}")
                return None

            # Create and return user object
            user = User.from_dict(user_data)
            logger.info(f"User verified successfully: {username}")
            return user

        except Exception as e:
            logger.error(f"Error verifying user: {str(e)}")
            return None

    @staticmethod
    def set_auth_cookies(response: Response, user: User):
        """Set authentication cookies for the user"""
        # Set simple cookies without secure flag for local development
        response.set_cookie(key="user_id", value=str(user.id), httponly=True)
        response.set_cookie(key="username", value=user.username, httponly=True)
        response.set_cookie(key="user_role", value=user.role, httponly=True)

    @staticmethod
    def clear_auth_cookies(response: Response):
        """Clear all authentication cookies"""
        response.delete_cookie(key="user_id")
        response.delete_cookie(key="username")
        response.delete_cookie(key="user_role")
