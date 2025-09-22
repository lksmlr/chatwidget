from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from typing import List
import urllib.parse
from src.admin.services.auth_service import AuthService
from src.admin.services.file_service import FileService
from src.admin.services.collection_service import CollectionService
from src.admin.services.scraper_service import ScraperService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["files"])
file_service = FileService()
collection_service = CollectionService()
scraper_service = ScraperService()


@router.post("/admin/upload")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(alias="files[]"),
    collection_id: str = Form(...),
):
    """Upload files to a collection"""
    try:
        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        logger.info(f"Uploading {len(files)} files to collection {collection_id}")

        # Check if files were uploaded
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="No files uploaded")

        # Process the uploaded files
        success, errors = await file_service.upload_files(files, collection_id)

        if not success or errors:
            logger.error(f"File upload errors: {errors}")
            return {"success": False, "errors": errors}
        else:
            logger.info(
                f"Successfully uploaded {len(files)} files to collection {collection_id}"
            )
            return {"success": True, "errors": []}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error uploading files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/points/{collection_id}")
async def get_points(request: Request, collection_id: str):
    """Get all files in a collection"""
    try:
        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        files = await file_service.get_collection_files(collection_id)
        return files
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting files for collection {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/points/{collection_id}/{filename}")
async def delete_file(request: Request, collection_id: str, filename: str):
    """Delete a file from a collection"""
    try:
        # Decode the URL-encoded filename
        decoded_filename = urllib.parse.unquote(filename)

        # Special handling for URLs - if the filename contains %2F, it was a URL
        if "%2F" in decoded_filename:
            # Replace %2F with actual slashes to restore the original URL
            decoded_filename = decoded_filename.replace("%2F", "/")
            logger.info(
                f"Detected URL in filename, restored slashes: {decoded_filename}"
            )

        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        success = await file_service.delete_file(collection_id, decoded_filename)
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(
            f"Error deleting file {filename} from collection {collection_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/points/{collection_id}/{filename}")
async def get_points_for_file(request: Request, collection_id: str, filename: str):
    """Get all points for a filename for a given collection"""
    try:
        # Decode the URL-encoded filename
        decoded_filename = urllib.parse.unquote(filename)

        # Special handling for URLs - if the filename is a URL that was encoded,
        # it might have had its slashes replaced with %2F before encoding
        if "%2F" in decoded_filename:
            # Replace %2F with actual slashes
            decoded_filename = decoded_filename.replace("%2F", "/")
            logger.info(
                f"Detected URL in filename, restored slashes: {decoded_filename}"
            )

        logger.info(
            f"Getting points for file: {decoded_filename} in collection: {collection_id}"
        )

        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        points = await file_service.get_points_for_file(collection_id, decoded_filename)
        return points
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(
            f"Error getting points for file {filename} in collection {collection_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/points/{collection_id}/{chunk_id}")
async def update_file_chunk(
    request: Request, collection_id: str, chunk_id: str, payload: dict
):
    """Update a specific chunk of a file"""
    try:
        new_text = payload.get("text")
        if not new_text:
            raise HTTPException(status_code=400, detail="Text is required")

        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        logger.info(
            f"Updating chunk {chunk_id} in collection {collection_id} with text {new_text}"
        )
        success = await file_service.update_file_chunk(
            collection_id, chunk_id, new_text
        )
        logger.info(f"Success: {success}")
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Chunk not found")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(
            f"Error updating chunk {chunk_id} in collection {collection_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/chunks/{collection_id}/{chunk_id}")
async def delete_chunk(request: Request, collection_id: str, chunk_id: str):
    """Delete a specific chunk of a file"""
    try:
        logger.info(f"Deleting chunk {chunk_id} in collection {collection_id}")
        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        success = await file_service.delete_chunk(collection_id, chunk_id)
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Chunk not found")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(
            f"Error deleting chunk {chunk_id} in collection {collection_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/scrape-url")
async def scrape_url(request: Request, payload: dict):
    """Scrape content from a URL and add it to a collection"""
    try:
        if not payload or not payload.get("urls") or not payload.get("collection_id"):
            raise HTTPException(
                status_code=400, detail="URL and collection ID are required"
            )

        urls = payload["urls"]
        collection_id = payload["collection_id"]

        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        # Temporarily return a simple success response until scraper service is implemented
        result = await scraper_service.scrape_urls(urls, collection_id)
        success = result.get("success", False)
        errors = result.get("errors", [])
        if success:
            message = "URLs scraped successfully"
        else:
            message = "Failed to scrape URLs"

        return {"success": success, "message": message, "errors": errors}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error scraping URL {payload.get('url')}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/crawl-url")
async def crawl_url(request: Request, payload: dict):
    """Crawl and scrape all pages for a base url and add them to a collection.

    Body JSON:
        url: str (required)
        collection_id: str (required)
    """
    try:
        if not payload or not payload.get("url") or not payload.get("collection_id"):
            raise HTTPException(
                status_code=400, detail="URL and collection ID are required"
            )

        url = payload["url"]
        collection_id = payload["collection_id"]
        css_selector = ""
        excluded_selector = ""

        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        result = await scraper_service.crawl_url(
            base_url=url,
            collection_id=collection_id,
            css_selector=css_selector,
            excluded_selector=excluded_selector,
        )

        success = result.get("success", False)
        errors = result.get("errors", [])
        job_id = result.get("job_id")
        message = (
            "Faculty scrape started" if success else "Failed to start faculty scrape"
        )

        return {
            "success": success,
            "message": message,
            "errors": errors,
            "job_id": job_id,
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error scraping faculty {payload.get('faculty')}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/jobs/by-id/{job_id}")
async def get_job_status_by_id(request: Request, job_id: str):
    """Proxy endpoint to fetch job status from ingest service with auth checks."""
    try:
        # Require a logged in user (admin or owner). We don't know the collection here,
        # so we just ensure the user is authenticated.
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        status = await scraper_service.get_job_status(job_id)
        if not status.get("found"):
            logger.error(f"Job {job_id} not found")
            raise HTTPException(status_code=404, detail="Job not found")

        return status["status"]
    except HTTPException as he:
        logger.error(f"Error getting job status by id {job_id}: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Error getting job status by id {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/jobs/active")
async def get_active_job(request: Request, collection_id: str):
    """Get active job for a collection (if any)."""
    try:
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Enforce access to the collection for non-admins
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        status = await scraper_service.get_active_job_for_collection(collection_id)
        if not status.get("found"):
            # Return 200 with explicit empty payload
            return {"found": False}
        return status["status"]
    except HTTPException as he:
        logger.error(
            f"Error getting active job for collection {collection_id}: {str(he)}"
        )
        raise he
    except Exception as e:
        logger.error(
            f"Error getting active job for collection {collection_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/jobs/{job_id}/cancel")
async def cancel_job(request: Request, job_id: str):
    try:
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Proxy to ingest cancel endpoint
        import aiohttp
        from src.settings import Settings

        settings = Settings()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.ingest.url}:{settings.ingest.port}/jobs/{job_id}/cancel"
            ) as resp:
                if resp.status == 404:
                    raise HTTPException(status_code=404, detail="Job not found")
                if resp.status == 409:
                    return {"ok": False, "message": "Job not cancellable"}
                resp.raise_for_status()
                return await resp.json()
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/file/{collection_id}/{filename}", response_class=HTMLResponse)
async def view_file_chunks(request: Request, collection_id: str, filename: str):
    """View file chunks page for a specific file"""
    try:
        # Decode the URL-encoded filename
        decoded_filename = urllib.parse.unquote(filename)

        # Special handling for URLs - if the filename contains %2F, it was a URL
        if "%2F" in decoded_filename:
            # Replace %2F with actual slashes to restore the original URL
            decoded_filename = decoded_filename.replace("%2F", "/")
            logger.info(
                f"Detected URL in filename, restored slashes: {decoded_filename}"
            )

        logger.info(
            f"Viewing file chunks for {decoded_filename} in collection {collection_id}"
        )

        # Verify user is logged in
        current_user = await AuthService.verify_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has access to this collection
        if current_user.role != "admin":
            collection = await collection_service.get_collection(collection_id)
            if not collection or str(collection.owner_id) != current_user.id:
                raise HTTPException(status_code=403, detail="Unauthorized")

        # Use the templating engine to render file_chunks.html
        from fastapi.templating import Jinja2Templates
        from pathlib import Path
        import json

        templates_dir = Path(__file__).parent.parent / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))

        # Create a unique identifier for the file that's safe for JavaScript
        # This avoids having to escape the filename in JavaScript
        file_id = str(hash(decoded_filename))

        # Create a mapping in the context that maps file_id to the actual filename
        file_mapping = {"id": file_id, "name": decoded_filename}

        # Use json.dumps to properly escape special characters for JavaScript
        escaped_filename = json.dumps(decoded_filename)

        return templates.TemplateResponse(
            "file_chunks.html",
            {
                "request": request,
                "filename": decoded_filename,
                "file_id": file_id,
                "file_mapping_json": json.dumps(file_mapping),
                "escaped_filename": escaped_filename,
                "collection_id": collection_id,
                "is_chunks_page": True,
            },
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(
            f"Error viewing file chunks for {filename} in collection {collection_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
