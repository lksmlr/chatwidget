from src.admin.database import Database
from src.admin.models.user import User
from src.admin.services.collection_service import CollectionService
from datetime import datetime
from typing import List, Optional
from passlib.hash import bcrypt
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users"""

    def __init__(self):
        """Initialize the user service"""
        self.db = Database()
        self.collection_service = CollectionService()

    async def get_all_users(self) -> List[User]:
        """Get all users except admin"""
        users_data = await self.db.get_users_by_role(role="institution")
        return [User.from_dict(user_data) for user_data in users_data]

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        user_data = await self.db.get_user_by_id(user_id)
        if not user_data:
            return None
        return User.from_dict(user_data)

    async def create_user(
        self, username: str, password: str, bot_name: str, role: str = "institution"
    ) -> str:
        """Create a new user"""
        # Check if username already exists
        existing_user = await self.db.get_user(username)
        if existing_user:
            raise ValueError("Username already exists")

        # Hash the password
        hashed_password = bcrypt.hash(password)

        # Create user document
        user_data = {
            "username": username,
            "password": hashed_password,
            "role": role,
            "bot_name": bot_name,
            "created_at": datetime.utcnow(),
        }

        logger.info(f"Creating user: {user_data}")

        # Insert the user
        user_id = await self.db.create_user(user_data)
        if not user_id:
            raise ValueError("Failed to create user")

        return user_id

    async def update_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        role: Optional[str] = None,
    ) -> bool:
        """Update a user's details"""
        # Get existing user
        user = await self.get_user(user_id)
        if not user:
            return False

        # Prepare update data
        update_data = {}
        if username is not None:
            update_data["username"] = username
        if password is not None:
            update_data["password"] = bcrypt.hash(password)
        if role is not None:
            update_data["role"] = role

        if not update_data:
            return True  # Nothing to update

        # Update the user
        return await self.db.update_user(user_id, update_data)

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and their collections"""
        # Get user
        user = await self.get_user(user_id)
        if not user:
            return False

        # Don't allow deleting admin users
        if user.role == "admin":
            raise ValueError("Cannot delete admin user")

        # Delete all collections owned by this user
        collections = await self.collection_service.get_user_collections(user)
        for collection in collections:
            await self.collection_service.delete_collection(str(collection._id))

        # Delete the user
        return await self.db.delete_user(user_id)

    async def change_password(self, user_id: str, new_password: str) -> bool:
        """Change a user's password"""
        # Get user
        user = await self.get_user(user_id)
        if not user:
            return False

        # Hash the new password
        hashed_password = bcrypt.hash(new_password)

        # Update the password
        return await self.db.update_user(user_id, {"password": hashed_password})

    async def get_bot_name(self, user_id: str) -> str:
        """Get the bot name for a user"""
        user = await self.get_user(user_id)
        if not user:
            return ""
        return user.bot_name

    async def update_bot_name(self, user_id: str, bot_name: str) -> bool:
        """Update the bot name for a user"""
        user = await self.get_user(user_id)
        if not user:
            return False
        return await self.db.update_user(user_id, {"bot_name": bot_name})
