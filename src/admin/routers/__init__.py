from .auth import router as auth
from .dashboard import router as dashboard
from .files import router as files
from .collections import router as collections
from .users import router as users

__all__ = ["auth", "dashboard", "files", "collections", "users"]
