from src.admin.database import Database
from src.clients.async_vector_client import AsyncVectorClient
from src.admin.models.collection import Collection
from src.admin.models.user import User
from bson import ObjectId
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class CollectionService:
    """Service for managing collections (formerly institutions)"""

    def __init__(self):
        """Initialize the collection service"""
        self.db = Database()
        self.vector_client = AsyncVectorClient()

    async def get_user_collections(self, owner: User):
        """Get all collections or a specific one based on role"""
        if owner.role == "admin":
            # Admin sees all collections
            collections = await self.db.get_all_collections()
            collections = [
                Collection.from_dict(collection) for collection in collections
            ]
            return collections

        else:
            # Faculty sees only their collections
            collections = await self.db.get_collection_by_owner(owner.id)
            if not collections:
                return []
            collections = [
                Collection.from_dict(collection) for collection in collections
            ]
            return collections

    async def get_collection(self, collection_id: str) -> Optional[Collection]:
        """Get a collection by ID"""
        collection_data = await self.db.get_collection(collection_id)
        if not collection_data:
            return None
        return Collection.from_dict(collection_data)

    async def get_collection_or_error(self, collection_id: str) -> Collection:
        """Get a collection by ID or raise error if not found"""
        collection = await self.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")
        return collection

    async def create_collection(
        self,
        data_source_name,
        welcome_message,
        owner_id: str,
        password_required=False,
        collection_password=None,
    ):
        """Create a new collection"""

        # Check if password is required
        password = None
        if password_required:
            if not collection_password:
                raise ValueError("Password is required when enabling protection")
            else:
                password = collection_password

        # Convert owner_id to ObjectId
        owner_id = ObjectId(owner_id)

        collection = Collection(
            data_source_name=data_source_name,
            welcome_message=welcome_message,
            owner_id=owner_id,
            password_required=password_required,
            password=password,
        )

        collection_id = await self.db.create_collection(collection.to_dict())

        # Update collection_name with the collection_id
        collection_name = (
            f"{data_source_name.replace(' ', '_').lower()}_{collection_id}"
        )
        collection.collection_name = collection_name
        await self.db.update_collection(collection_id, collection.to_dict())

        logger.info(f"Creating Qdrant collection: {collection_name}")
        # Create Qdrant collection
        await self.vector_client.create_collection(collection_name)

        return str(collection_id)

    async def delete_collection(self, collection_id: str):
        """Delete a collection and its associated user"""
        # Check if collection exists
        collection_data = await self.db.get_collection(collection_id)
        if not collection_data:
            raise ValueError(f"Collection '{collection_id}' not found")

        # Get collection name for Qdrant deletion
        collection_name = collection_data.get("collection_name")

        # Delete from Qdrant if collection_name exists
        if collection_name:
            try:
                await self.vector_client.delete_collection(collection_name)
            except Exception as e:
                logging.error(f"Error deleting Qdrant collection: {str(e)}")

        # Delete from database
        deleted = await self.db.delete_collection(collection_id)
        if not deleted:
            raise ValueError(
                f"Failed to delete collection '{collection_id}' from database"
            )

        # Delete associated users
        try:
            await self.db.delete_users_by_collection(ObjectId(collection_id))
        except Exception as e:
            logging.warning(f"Error deleting users for collection: {str(e)}")

        return True

    async def update_collection(
        self,
        collection_id: str,
        data_source_name: str = None,
        welcome_message: str = None,
        password_required: bool = None,
        collection_password: str = None,
    ):
        """Update a collection with new values"""
        # Get existing collection
        collection_data = await self.db.get_collection(collection_id)
        if not collection_data:
            raise ValueError(f"Collection '{collection_id}' not found")

        # Create collection object from existing data
        current_collection = Collection.from_dict(collection_data)

        # Update fields if provided
        if data_source_name is not None:
            current_collection.data_source_name = data_source_name

        if welcome_message is not None:
            current_collection.welcome_message = welcome_message

        # Handle password settings
        if password_required is not None:
            current_collection.password_required = password_required

            # Check if password is required and if a password is provided
            if password_required:
                if collection_password:
                    try:
                        current_collection.password = collection_password
                    except Exception as e:
                        raise ValueError(f"Error hashing password: {str(e)}")
                elif not current_collection.password:
                    raise ValueError("Password is required when enabling protection")
            else:
                current_collection.password = None

        # Update the collection
        try:
            updated = await self.db.update_collection(
                collection_id, current_collection.to_dict()
            )
            if not updated:
                raise ValueError(f"Failed to update collection '{collection_id}'")
            return True
        except Exception as e:
            logging.error(f"Error updating collection: {str(e)}")
            raise

    async def get_all_collections(self) -> List[Collection]:
        """Get all collections"""
        return [
            Collection.from_dict(collection)
            for collection in await self.db.get_all_collections()
        ]
