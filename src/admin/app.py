import sys
import os
from contextlib import asynccontextmanager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from pathlib import Path

from src.admin.database import Database
from src.admin.routers import auth, dashboard, files, collections, users

# Create a logger for this module
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization"""
    # Startup
    db = Database()
    await db.ensure_admin_user()
    yield


app = FastAPI(title="Admin Frontend", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure static files with absolute path
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Configure templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


# Add template context processor for static URLs
@app.middleware("http")
async def add_static_url(request: Request, call_next):
    # Define a function that logs and returns clean static URLs
    def get_static_url(path):
        clean_path = path.strip()
        url = f"/static/{clean_path}"
        # Log the URL being generated for debugging
        if "script" in path:
            logger.info(f"STATIC URL DEBUG: Generated URL '{url}' for path '{path}'")
        return url

    # Add static_url function to templates
    request.state.static_url = get_static_url
    response = await call_next(request)
    return response


# Configure upload folder
UPLOAD_FOLDER = "uploads"
upload_folder = Path(UPLOAD_FOLDER)
upload_folder.mkdir(exist_ok=True)

# Include routers
app.include_router(auth)
app.include_router(dashboard)
app.include_router(files)
app.include_router(collections)
app.include_router(users)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/auth/login")


# Create a logger for this module
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.admin.app:app", host="0.0.0.0", port=9000, reload=True)
