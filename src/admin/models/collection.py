from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from bson import ObjectId


@dataclass
class Collection:
    """
    Represents a collection of vectorized data (formerly called "institution")
    Each collection can be accessed by multiple users
    """

    data_source_name: str
    welcome_message: str
    owner_id: str  # Owner user ID
    password_required: bool = False
    password: Optional[str] = None
    collection_name: Optional[str] = None  # Name used in vector DB
    created_at: datetime = field(default_factory=datetime.utcnow)
    _id: Optional[str] = None  # MongoDB ObjectId as string

    def __post_init__(self):
        """Initialize derived fields after dataclass initialization"""
        if self.collection_name is None:
            # Generate a collection name based on bot name if not provided
            self.collection_name = f"collection_{self.data_source_name.replace(' ', '_').lower()}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    def to_dict(self) -> Dict:
        """Convert the Collection to a dictionary for database storage"""
        data = {
            "data_source_name": self.data_source_name,
            "welcome_message": self.welcome_message,
            "owner_id": ObjectId(self.owner_id)
            if isinstance(self.owner_id, str)
            else self.owner_id,
            "password_required": self.password_required,
            "password": self.password,
            "collection_name": self.collection_name,
            "created_at": self.created_at,
        }

        # Include _id if it exists (for updates)
        if self._id:
            data["_id"] = ObjectId(self._id) if isinstance(self._id, str) else self._id

        return data

    def to_json(self) -> Dict:
        """Convert the Collection to a dictionary for JSON serialization (API responses)"""
        data = {
            "_id": str(self._id) if self._id else None,  # Ensure _id is always a string
            "data_source_name": self.data_source_name,
            "welcome_message": self.welcome_message,
            "owner_id": str(self.owner_id),
            "password_required": self.password_required,
            "collection_name": self.collection_name,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Collection":
        """Create a Collection from a dictionary retrieved from the database"""
        collection = cls(
            data_source_name=data["data_source_name"],
            welcome_message=data["welcome_message"],
            owner_id=str(data["owner_id"])
            if "owner_id" in data
            else str(data.get("user_id", "")),
            password_required=data.get("password_required", False),
            password=data.get("password", None),
        )

        # Override default values if they exist in the data
        if "created_at" in data:
            collection.created_at = data["created_at"]
        if "collection_name" in data:
            collection.collection_name = data["collection_name"]
        if "_id" in data:
            collection._id = str(data["_id"])

        return collection
