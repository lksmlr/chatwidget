from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.admin.services.auth_service import AuthService
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Configure templates with correct path relative to this file
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard page"""
    try:
        # Verify user is logged in
        current_user = await AuthService.verify_user(request)

        if not current_user:
            logger.warning("No authenticated user found, redirecting to login")
            return RedirectResponse(url="/auth/login", status_code=302)

        logger.info(f"Rendering dashboard for user: {current_user.username}")

        # Prepare context for template
        context = {
            "request": request,
            "user": current_user.to_dict(),
            "is_admin": current_user.role == "admin",
        }

        # Add collections if they exist in cookies
        if user_collections := request.cookies.get("user_collections"):
            context["collections"] = user_collections.split(",")

        return templates.TemplateResponse(
            "index.html",  # Use index.html as the dashboard template
            context,
        )
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return RedirectResponse(url="/auth/login", status_code=302)
