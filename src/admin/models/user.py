from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class User:
    """
    Represents a user in the system (which is also an institution)
    For example, "Faculty of Architecture" would be a user
    """

    id: str
    username: str
    password: str  # This is stored hashed
    bot_name: str
    role: str  # 'admin' or 'institution'
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert the User to a dictionary for database storage"""
        return {
            "_id": self.id,  # Use _id to match frontend expectations
            "username": self.username,
            "role": self.role,
            "bot_name": self.bot_name,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
        }

    def to_json(self) -> Dict:
        """Alias for to_dict for API responses"""
        return self.to_dict()

    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        """Create a User from a dictionary retrieved from the database"""
        user = cls(
            id=str(data["_id"]),
            username=data["username"],
            password=data["password"],  # Already hashed
            role=data.get("role", "institution"),
            bot_name=data.get("bot_name", ""),
        )

        # Handle other optional fields
        if "created_at" in data:
            user.created_at = data["created_at"]

        return user

    def verify_password(self, plain_password: str) -> bool:
        """Verify a plain password against the hashed password"""
        return pwd_context.verify(plain_password, self.password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage"""
        return pwd_context.hash(password)

    def is_admin(self) -> bool:
        """Check if the user is an admin"""
        return self.role == "admin"

    def is_institution(self) -> bool:
        """Check if the user is an institution"""
        return self.role == "institution"
