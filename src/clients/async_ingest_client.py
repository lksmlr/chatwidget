import aiohttp
import aiofiles
import mimetypes
import os
import logging

from src.settings import Settings

_settings = Settings()

logger = logging.getLogger(__name__)


async def chunk_pdf(path_to_pdf: str) -> list[str]:
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            async with aiofiles.open(path_to_pdf, "rb") as pdf_file:
                content = await pdf_file.read()
                form = aiohttp.FormData()
                form.add_field(
                    "file",
                    content,
                    filename=path_to_pdf,
                    content_type="application/pdf",
                )

                async with session.post(
                    f"{_settings.ingest.url}:{_settings.ingest.port}/chunk_pdf",
                    data=form,
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    print(result)
                    return result.get("chunks", [])
    except aiohttp.ClientError as e:
        print(f"HTTP-Fehler: {str(e)}")
        return []
    except Exception as e:
        print(f"Allgemeiner Fehler: {str(e)}")
        return []


async def insert_document(path_to_document: str, collection_name: str) -> bool:
    try:
        mime_type, _ = mimetypes.guess_type(path_to_document)

        if mime_type is None:
            mime_type = "application/octet-stream"

        filename = os.path.basename(path_to_document)

        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(path_to_document, "rb") as document:
                content = await document.read()
                form = aiohttp.FormData()
                form.add_field(
                    "file",
                    content,
                    filename=filename,
                    content_type=mime_type,
                )
                form.add_field("collection_name", collection_name)

                async with session.post(
                    f"{_settings.ingest.url}:{_settings.ingest.port}/insert_document",
                    data=form,
                ) as response:
                    response.raise_for_status()
                    result = await response.json()

                    return result.get("success", False)

    except Exception as e:
        logger.error(f"Error while inserting document: {e}")
        return False


async def insert_urls(
    collection_name: str,
    urls: list[str],
    css_selector: str = "",
    excluded_selector: str = "",
) -> bool:
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=7200)
        ) as session:
            payload = {
                "collection_name": collection_name,
                "urls": urls,
                "css_selector": css_selector,
                "excluded_selector": excluded_selector,
            }
            async with session.post(
                f"{_settings.ingest.url}:{_settings.ingest.port}/insert_urls",
                json=payload,
            ) as response:
                response.raise_for_status()
                result = await response.json()

                return result.get("success", False)

    except aiohttp.ClientError as e:
        logger.error(f"HTTP-Fehler: {str(e)}")
        return False

    except Exception as e:
        logger.error(f"Allgemeiner Fehler: {str(e)}")
        return False


async def create_url_crawl_job(
    collection_name: str,
    base_url: str,
    css_selector: str = "",
    excluded_selector: str = "",
) -> str | None:
    """Create a background job for faculty scrape, returns job_id or None."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "collection_name": collection_name,
                "base_url": base_url,
                "css_selector": css_selector,
                "excluded_selector": excluded_selector,
            }
            async with session.post(
                f"{_settings.ingest.url}:{_settings.ingest.port}/jobs/crawl_url",
                json=payload,
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get("job_id")
    except Exception as e:
        logger.error(f"Error creating url crawl job: {e}")
        return None


async def get_job_status(job_id: str) -> dict | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_settings.ingest.url}:{_settings.ingest.port}/jobs/by-id/{job_id}"
            ) as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                return await response.json()
    except Exception as e:
        logger.error(f"Error fetching job status: {e}")
        return None


async def get_active_job(collection_name: str) -> dict | None:
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Getting active job for collection {collection_name}")
            async with session.get(
                f"{_settings.ingest.url}:{_settings.ingest.port}/jobs/active",
                params={"collection_name": collection_name},
            ) as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                return await response.json()
    except Exception as e:
        logger.error(f"Error fetching active job: {e}")
        return None
