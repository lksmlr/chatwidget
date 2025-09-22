from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from crawl4ai import AsyncWebCrawler, BrowserConfig
import asyncio
from uuid import uuid4
from time import time
import logging

from src.ingest.ingest_service import (
    aurls_to_vectorstore,
    adocument_to_vectorstore,
    acrawl_chunk_pdf,
    acrawl_url_and_add_to_vectorstore,
)

logger = logging.getLogger(__name__)


CRAWLER_INSTANCE = None
BROWSER_CONFIG = None
CRAWLER_RESTART_LOCK = asyncio.Lock()
JOBS: dict[str, dict] = {}
ACTIVE_BY_COLLECTION: dict[str, str] = {}


def _public_job(job: dict) -> dict:
    return {k: v for k, v in job.items() if not k.startswith("_")}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global CRAWLER_INSTANCE
    global BROWSER_CONFIG
    logger.info("\nStarting up and initializing crawler...")

    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        extra_args=[
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=site-per-process",
        ],
    )

    BROWSER_CONFIG = browser_config
    CRAWLER_INSTANCE = AsyncWebCrawler(config=BROWSER_CONFIG)
    await CRAWLER_INSTANCE.start()

    yield

    logger.info("\nShutting down and closing crawler...")
    if CRAWLER_INSTANCE:
        await CRAWLER_INSTANCE.close()


async def _restart_crawler():
    """Restart the global crawler instance safely with a lock."""
    global CRAWLER_INSTANCE
    global BROWSER_CONFIG
    async with CRAWLER_RESTART_LOCK:
        try:
            if CRAWLER_INSTANCE:
                try:
                    await CRAWLER_INSTANCE.close()
                except Exception:
                    pass
        finally:
            CRAWLER_INSTANCE = AsyncWebCrawler(config=BROWSER_CONFIG)
            await CRAWLER_INSTANCE.start()


def _is_playwright_closed_error(err: Exception) -> bool:
    msg = str(err) if err else ""
    signals = [
        "BrowserContext.new_page",
        "context or browser has been closed",
        "Target page, context or browser has been closed",
        "Connection closed",
    ]
    return any(s.lower() in msg.lower() for s in signals)


async def _with_crawler_retry(coro_factory, *, max_restarts: int = 1):
    """Run a coroutine factory with one safe crawler restart on fatal browser errors."""
    attempts = 0
    while True:
        try:
            return await coro_factory()
        except Exception as e:
            if not _is_playwright_closed_error(e) or attempts >= max_restarts:
                raise
            attempts += 1
            logger.warning(
                "Crawler/browser closed unexpectedly. Restarting crawler (attempt %s/%s)...",
                attempts,
                max_restarts,
            )
            await _restart_crawler()


# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _run_url_crawl_job(
    job_id: str,
    *,
    base_url: str,
    collection_name: str,
    css_selector: str,
    excluded_selector: str,
):
    job = JOBS.get(job_id)
    if not job:
        return
    job["status"] = "running"
    job["started_at"] = time()
    try:

        def report(progress: dict):
            # store lightweight progress info
            job["progress"] = progress.get("progress")
            job["processed"] = progress.get("processed")
            job["total"] = progress.get("total")
            job["message"] = progress.get("message")
            last_url = progress.get("last_url")
            if last_url:
                job["last_url"] = last_url

        async def _job_run():
            return await acrawl_url_and_add_to_vectorstore(
                base_url=base_url,
                crawler_instance=CRAWLER_INSTANCE,
                collection_name=collection_name,
                css_selector=css_selector,
                excluded_selector=excluded_selector,
                progress_callback=report,
            )

        success = await _with_crawler_retry(_job_run, max_restarts=1)
        job["status"] = "succeeded" if success else "failed"
        job["result"] = {"success": success}
    except asyncio.CancelledError:
        job["status"] = "cancelled"
        job["result"] = {"success": False}
        job["message"] = "Cancelled."
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        job["finished_at"] = time()
        # Clear active lock if still mapped
        try:
            if ACTIVE_BY_COLLECTION.get(collection_name) == job_id:
                del ACTIVE_BY_COLLECTION[collection_name]
        except Exception:
            pass
        # Ensure the crawler is in a clean state for the next run
        try:
            await _restart_crawler()
        except Exception:
            logger.warning("Failed to restart crawler after job completion")


@app.post("/chunk_pdf")
async def chunk_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()

        if not file.filename.endswith(".pdf"):
            return JSONResponse(
                content={"error": "Nur PDF-Dateien erlaubt"}, status_code=400
            )

        chunks = await acrawl_chunk_pdf(binary_data=content)

        return JSONResponse(
            content={
                "chunks": chunks,
            }
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/insert_document")
async def insert_document(
    collection_name: str = Form(...), file: UploadFile = File(...)
):
    ALLOWED_FILETYPES = [".txt", ".csv", ".pdf"]

    try:
        content = await file.read()

        if not any(file.filename.endswith(ext) for ext in ALLOWED_FILETYPES):
            return JSONResponse(
                content={
                    "error": f"Only the following data types are allowed: {', '.join(ALLOWED_FILETYPES)}"
                },
                status_code=400,
            )

        data_type = str(file.filename.split(".")[-1])

        success = await adocument_to_vectorstore(
            data_type=data_type,
            collection_name=collection_name,
            binary_data=content,
            source=file.filename,
        )

        return JSONResponse(content={"success": success})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/insert_urls")
async def insert_urls(request: Request):
    try:
        global CRAWLER_INSTANCE
        data = await request.json()
        collection_name = data.get("collection_name", "")
        urls = data.get("urls", "")
        css_selector = data.get("css_selector", "")
        excluded_selector = data.get("excluded_selector", "")

        async def _insert_urls_run():
            return await aurls_to_vectorstore(
                crawler_instance=CRAWLER_INSTANCE,
                collection_name=collection_name,
                urls=urls,
                css_selector=css_selector,
                excluded_selector=excluded_selector,
            )

        success = await _with_crawler_retry(_insert_urls_run, max_restarts=1)
        # After one-off insert, refresh crawler to avoid stale state between requests
        try:
            await _restart_crawler()
        except Exception:
            logger.warning("Failed to restart crawler after insert_urls")

        return JSONResponse(
            content={
                "success": success,
            }
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/jobs/crawl_url")
async def create_url_crawl_job(request: Request):
    try:
        global CRAWLER_INSTANCE
        data = await request.json()
        base_url = data.get("base_url")
        collection_name = data.get("collection_name", "")
        css_selector = data.get("css_selector", "")
        excluded_selector = data.get("excluded_selector", "")

        if not base_url or not collection_name:
            return JSONResponse(
                content={"error": "base_url and collection_name are required"},
                status_code=400,
            )
        # If there is already an active job for this collection, return it
        existing_job_id = ACTIVE_BY_COLLECTION.get(collection_name)
        if existing_job_id:
            existing = JOBS.get(existing_job_id)
            if existing and existing.get("status") in {"queued", "running"}:
                return JSONResponse(
                    content={"job_id": existing_job_id, "already_running": True},
                    status_code=202,
                )

        job_id = str(uuid4())
        JOBS[job_id] = {
            "id": job_id,
            "type": "faculty-scrape",
            "status": "queued",
            "created_at": time(),
            "base_url": base_url,
            "collection_name": collection_name,
        }
        # Set active lock
        ACTIVE_BY_COLLECTION[collection_name] = job_id

        task = asyncio.create_task(
            _run_url_crawl_job(
                job_id,
                base_url=base_url,
                collection_name=collection_name,
                css_selector=css_selector,
                excluded_selector=excluded_selector,
            )
        )
        JOBS[job_id]["_task"] = task

        return JSONResponse(
            content={"job_id": job_id, "already_running": False}, status_code=202
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/jobs/by-id/{job_id}")
async def get_job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse(content={"error": "job not found"}, status_code=404)
    return JSONResponse(content=_public_job(job))


@app.get("/jobs/active")
async def get_active_job(collection_name: str):
    job_id = ACTIVE_BY_COLLECTION.get(collection_name)
    if not job_id:
        return JSONResponse(content={"error": "no active job"}, status_code=404)
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse(content={"error": "job not found"}, status_code=404)
    return JSONResponse(content=_public_job(job))


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    logger.info(f"Cancelling job {job_id}")
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse(content={"error": "job not found"}, status_code=404)
    if job.get("status") not in {"queued", "running", "cancelling"}:
        return JSONResponse(content={"error": "job not cancellable"}, status_code=409)
    job["status"] = "cancelling"
    task: asyncio.Task | None = job.get("_task")
    if task and not task.done():
        task.cancel()
    return JSONResponse(content={"ok": True}, status_code=202)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8900)
