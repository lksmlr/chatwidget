from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from src.admin.services.auth_service import AuthService
from src.admin.database import Database
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Configure templates with correct path relative to this file
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page"""
    logger.info("Rendering login page")
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/me", response_class=JSONResponse)
async def me(user=Depends(AuthService.verify_user)):
    """Get current user"""
    logger.info("Getting current user")
    username = user.username
    user_id = user.id
    return {"username": username, "user_id": user_id}


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handle login request"""
    try:
        logger.info(f"Login attempt for user: {username}")
        is_valid, user, message = await AuthService.authenticate_user(
            username, password
        )

        if is_valid and user:
            logger.info(f"Login successful for user: {username}")

            # Create response with redirect
            response = RedirectResponse(url="/dashboard/", status_code=302)

            # Set session cookies
            AuthService.set_auth_cookies(response, user)

            # If user is not admin, get their collections
            if user.role != "admin":
                db = Database()
                collections = await db.get_collection_by_owner(str(user.id))
                if collections:
                    collection_ids = [str(coll["_id"]) for coll in collections]
                    response.set_cookie(
                        key="user_collections", value=",".join(collection_ids)
                    )

            logger.info(
                f"Set session cookies and redirecting to dashboard for user: {username}"
            )
            return response
        else:
            logger.warning(f"Login failed for user: {username} - {message}")
            return templates.TemplateResponse(
                "login.html", {"request": request, "error": message}, status_code=401
            )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "An error occurred during login. Please try again.",
            },
            status_code=500,
        )


@router.get("/logout")
async def logout():
    """Handle logout request"""
    logger.info("Processing logout request")
    response = RedirectResponse(url="/auth/login", status_code=302)
    AuthService.clear_auth_cookies(response)
    logger.info("Logged out successfully")
    return response
