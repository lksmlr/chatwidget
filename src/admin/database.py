from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import List, Dict, Optional
import datetime
from src.admin.models.user import User
from src.settings import Settings
import logging

logger = logging.getLogger(__name__)


class Database:
    _instance = None
    _settings = Settings()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.mongo_uri = f"mongodb://{self._settings.mongo_username.get_secret_value()}:{self._settings.mongo_password.get_secret_value()}@{self._settings.mongo.url}:{self._settings.mongo.port}"
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client["admin_panel"]
        self.users_collection = self.db["users"]
        self.collections_collection = self.db["collections"]
        self._initialized = True

    async def ensure_admin_user(self) -> None:
        """
        Ensures that at least one admin user exists in the database.
        This is automatically called during initialization in production.
        """
        # Check if any admin user exists
        admin_user = await self.users_collection.find_one({"role": "admin"})

        if not admin_user:
            # Create default admin user if none exists
            admin_username = "admin"
            admin_password = self._settings.admin_password.get_secret_value()

            if not admin_password:
                raise EnvironmentError(
                    "ADMIN_PASSWORD environment variable must be set in production"
                )

            # Hash the password using the User model's hash_password method
            hashed_password = User.hash_password(admin_password)
            admin_data = {
                "username": admin_username,
                "password": hashed_password,
                "role": "admin",
                "created_at": datetime.datetime.now(),
            }

            await self.create_user(admin_data)
            logger.info(f"Default admin user '{admin_username}' created successfully")

    # User-related methods
    async def get_user(self, username: str) -> Optional[Dict]:
        """Get a user by username"""
        return await self.users_collection.find_one({"username": username})

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID"""
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            user = await self.users_collection.find_one({"_id": user_id})
            return user
        except Exception:
            return None

    async def get_users(self) -> List[Dict]:
        """Get all users"""
        cursor = self.users_collection.find()
        return await cursor.to_list(length=None)

    async def get_users_by_role(self, role: str) -> List[Dict]:
        """Get all users by role"""
        cursor = self.users_collection.find({"role": role})
        return await cursor.to_list(length=None)

    async def create_user(self, user_data: Dict) -> str:
        """Create a new user"""
        result = await self.users_collection.insert_one(user_data)
        return str(result.inserted_id)

    async def update_user(self, user_id: str, update_data: Dict) -> bool:
        """Update a user by ID"""
        result = await self.users_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user by ID"""
        result = await self.users_collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    async def delete_users_by_collection(self, collection_id: ObjectId) -> int:
        """Delete all users associated with a collection (backward compatibility)"""
        result = await self.users_collection.delete_many(
            {"collection_id": collection_id}
        )
        return result.deleted_count

    async def get_collection(self, collection_id: str) -> Optional[Dict]:
        """Get a collection by ID"""
        return await self.collections_collection.find_one(
            {"_id": ObjectId(collection_id)}
        )

    async def get_collection_by_owner(self, owner_id: str) -> List[Dict]:
        """Get collections by owner ID"""
        cursor = self.collections_collection.find({"owner_id": ObjectId(owner_id)})
        return await cursor.to_list(length=None)

    async def get_collection_by_key(self, key: str) -> Optional[Dict]:
        """Get a collection by key"""
        return await self.collections_collection.find_one({"password": key})

    async def create_collection(self, collection_data: Dict) -> str:
        """Create a new collection"""
        result = await self.collections_collection.insert_one(collection_data)
        return str(result.inserted_id)

    async def update_collection(self, collection_id: str, update_data: Dict) -> bool:
        """Update a collection by ID"""
        result = await self.collections_collection.update_one(
            {"_id": ObjectId(collection_id)}, {"$set": update_data}
        )
        return result.matched_count > 0

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection by ID"""
        result = await self.collections_collection.delete_one(
            {"_id": ObjectId(collection_id)}
        )
        return result.deleted_count > 0

    async def get_all_collections(self) -> List[Dict]:
        """Get all collections"""
        cursor = self.collections_collection.find()
        collections = await cursor.to_list(length=None)
        for coll in collections:
            coll["_id"] = str(coll["_id"])
        return collections

    async def close(self):
        """Close the MongoDB connection"""
        await self.client.close()

    @classmethod
    async def reset(cls):
        """Reset the singleton instance - primarily useful for testing"""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
