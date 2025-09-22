from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import Optional
from src.admin.services.auth_service import AuthService
from src.admin.services.user_service import UserService
import logging
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/users", tags=["users"])
user_service = UserService()


class UserCreate(BaseModel):
    username: str
    password: str
    bot_name: str
    role: str = "institution"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


class PasswordChange(BaseModel):
    password: str


class BotNameUpdate(BaseModel):
    bot_name: str
    user_id: Optional[str] = None


@router.get("/")
async def get_users(request: Request):
    """Get all users (admin only)"""
    try:
        # Verify user is logged in and is admin
        current_user = await AuthService.verify_user(request)
        if not current_user:
            logger.warning("Unauthorized access attempt to users list")
            raise HTTPException(status_code=401, detail="Authentication required")

        if current_user.role != "admin":
            logger.warning(
                f"Non-admin user {current_user.username} attempted to access users list"
            )
            raise HTTPException(status_code=403, detail="Admin access required")

        logger.info("Getting all users for admin")
        users = await user_service.get_all_users()
        return [user.to_dict() for user in users]
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    bot_name: str = Form(...),
    role: str = Form("institution"),
):
    """Create a new user (admin only)"""
    try:
        # Verify user is logged in and is admin
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        logger.info(
            f"Creating new user with username: {username}, bot_name: {bot_name}, role: {role}"
        )

        logger.info(
            f"Creating user with username: {username}, password: {password}, bot_name: {bot_name}, role: {role}"
        )

        user_id = await user_service.create_user(username, password, bot_name, role)

        return {
            "success": True,
            "id": str(user_id),
            "message": "User created successfully",
        }
    except ValueError as ve:
        logger.error(f"Validation error creating user: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bot-name")
async def get_bot_name(request: Request, user_id: Optional[str] = None):
    """Get the bot name for a user"""
    try:
        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Determine which user's bot name to fetch
        target_user_id = None

        if current_user.role == "admin":
            # Admin can get any user's bot name
            target_user_id = user_id if user_id else current_user.id
        else:
            # Institution users can only get their own bot name
            if user_id and user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to access other user's bot name",
                )
            target_user_id = current_user.id

        # Get the user and their bot name
        user = await user_service.get_user(target_user_id)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User not found with ID: {target_user_id}"
            )

        return JSONResponse({"bot_name": user.bot_name if user.bot_name else ""})
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting bot name for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bot-name")
async def update_bot_name(request: Request, update_data: BotNameUpdate):
    """Update the bot name for a user (admin only)"""
    try:
        # Verify user is logged in and is admin
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Determine which user's bot name to update
        target_user_id = None

        if current_user.role == "admin":
            # Admin can update any user's bot name
            target_user_id = (
                update_data.user_id if update_data.user_id else current_user.id
            )
        else:
            # Institution users can only update their own bot name
            if update_data.user_id and update_data.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to update other user's bot name",
                )
            target_user_id = current_user.id

        logger.info(
            f"Updating bot name for user {target_user_id} to {update_data.bot_name}"
        )
        success = await user_service.update_bot_name(
            target_user_id, update_data.bot_name
        )
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return {"success": True}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(
            f"Error updating bot name for user {update_data.user_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user(request: Request, user_id: str):
    """Get user details (admin only)"""
    try:
        # Verify user is logged in and is admin
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user.to_dict()
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}")
async def update_user(request: Request, user_id: str, user_update: UserUpdate):
    """Update user details (admin only)"""
    try:
        # Verify user is logged in and is admin
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        success = await user_service.update_user(
            user_id, user_update.username, user_update.password, user_update.role
        )

        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return {"success": True}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_user(request: Request, user_id: str):
    """Delete a user (admin only)"""
    try:
        # Verify user is logged
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this user"
            )

        try:
            success = await user_service.delete_user(user_id)
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
            return {
                "success": True,
                "message": "User and associated collections deleted successfully",
            }
        except ValueError as ve:
            raise HTTPException(status_code=403, detail=str(ve))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/password")
async def change_user_password(
    request: Request, user_id: str, password_data: PasswordChange
):
    """Change a user's password (admin only)"""
    try:
        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        success = await user_service.change_password(user_id, password_data.password)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return {"success": True, "message": "Password changed successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error changing password for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/collections")
async def get_user_collections(request: Request, user_id: str):
    """Get all collections for a user (admin only)"""
    try:
        # Verify user is logged in and is admin
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        collections = await user_service.collection_service.get_user_collections(user)

        # Ensure we use the proper serialization method
        return [collection.to_json() for collection in collections]
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting collections for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
