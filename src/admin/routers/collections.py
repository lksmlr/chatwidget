from fastapi import APIRouter, HTTPException, Depends, Form, Request
from typing import Optional
from pydantic import BaseModel
from src.admin.database import Database
from src.admin.services.auth_service import AuthService
from src.admin.services.collection_service import CollectionService
import logging

router = APIRouter(prefix="/admin/collections", tags=["collections"])
db = Database()
collection_service = CollectionService()
logger = logging.getLogger(__name__)


class CollectionCreate(BaseModel):
    data_source_name: str
    welcome_message: str
    owner_id: Optional[str] = None
    password_required: bool = False
    collection_password: Optional[str] = None


class CollectionUpdate(BaseModel):
    data_source_name: Optional[str] = None
    welcome_message: Optional[str] = None
    password_required: Optional[bool] = None
    password: Optional[str] = None


@router.get("/")
async def get_collections(user=Depends(AuthService.verify_user)):
    """Get all collections the user has access to"""
    try:
        collections = []

        if user.role == "admin":
            # Admin can see all collections
            collections = await collection_service.get_all_collections()
        else:
            # Regular users can only see their collections
            collections = await collection_service.get_user_collections(user)

        # Use the to_json method to ensure _id is included properly
        return [collection.to_json() for collection in collections]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def add_collection(
    request: Request,
    data_source_name: str = Form(...),
    welcome_message: str = Form(...),
    owner_id: Optional[str] = Form(None),
    password_required: Optional[bool] = Form(False),
    collection_password: Optional[str] = Form(None),
):
    """Add a new collection"""
    try:
        # Verify user is logged in
        user = await AuthService.verify_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Handle password_required coming as string "on" from form
        if isinstance(password_required, str):
            password_required = password_required == "on"

        # Basic validation
        if not data_source_name or not welcome_message:
            raise HTTPException(
                status_code=400,
                detail="Data source name and welcome message are required",
            )

        # Check if password protection is enabled
        if password_required and not collection_password:
            raise HTTPException(
                status_code=400,
                detail="Password is required when protection is enabled",
            )

        # Check if password is already in use
        if (
            collection_password
            and await db.get_collection_by_key(collection_password) is not None
        ):
            raise HTTPException(status_code=400, detail="Please use a different key")

        # Determine owner ID
        final_owner_id = None
        if user.role == "admin" and owner_id:
            final_owner_id = owner_id
        else:
            final_owner_id = user.id

        logger.info(
            f"Creating collection with data_source_name: {data_source_name}, welcome_message: {welcome_message}, owner_id: {final_owner_id}, password_required: {password_required}, collection_password: {collection_password}"
        )

        # Create the collection
        collection_id = await collection_service.create_collection(
            data_source_name,
            welcome_message,
            final_owner_id,
            password_required,
            collection_password,
        )

        if not collection_id:
            raise HTTPException(status_code=500, detail="Failed to create collection")

        return {
            "success": True,
            "id": str(collection_id),
            "message": "Collection created successfully",
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str, user=Depends(AuthService.verify_user)):
    """Delete a collection"""
    try:
        # Check if user can delete this collection
        if user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        # Delete the collection
        await collection_service.delete_collection(collection_id)
        return {"success": True}

    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_id}/settings")
async def get_collection_settings(
    collection_id: str, user=Depends(AuthService.verify_user)
):
    """Get collection settings"""
    try:
        # Check if user has access to this collection
        if user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        collection = await collection_service.get_collection(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Don't return the password to the frontend
        collection_dict = collection.to_json()
        collection_dict["password"] = collection.password
        return collection_dict

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{collection_id}/settings")
async def update_collection_settings(
    collection_id: str,
    settings: CollectionUpdate,
    user=Depends(AuthService.verify_user),
):
    """Update collection settings"""
    try:
        # Check if user has access to this collection
        if user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        # Get existing collection
        existing_collection = await collection_service.get_collection(collection_id)
        if not existing_collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Check if password is already in use
        if (
            settings.password
            and await db.get_collection_by_key(settings.password) is not None
        ):
            raise HTTPException(status_code=400, detail="Please use a different key")

        logger.info(f"Updating collection with settings: {settings}")

        # Update in database
        await collection_service.update_collection(
            collection_id,
            settings.data_source_name or existing_collection.data_source_name,
            settings.welcome_message or existing_collection.welcome_message,
            settings.password_required
            if settings.password_required is not None
            else existing_collection.password_required,
            settings.password,
        )

        return {"success": True}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating collection settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_id}/users")
async def get_collection_users(
    collection_id: str, user=Depends(AuthService.verify_user)
):
    """Get all users that have access to a collection"""
    try:
        # Check if user has access to this collection
        if user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        users = await collection_service.get_collection_users(collection_id)
        collection = await collection_service.get_collection(collection_id)

        if collection:
            owner_id = str(collection.owner_id)
            return [
                {**user.to_json(), "is_owner": str(user.id) == owner_id}
                for user in users
            ]
        return []

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
