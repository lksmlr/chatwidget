from src.admin.database import Database
from src.clients.async_vector_client import AsyncVectorClient
from src.clients.async_ingest_client import (
    insert_urls,
    create_url_crawl_job,
    get_job_status,
    get_active_job,
)
import logging

logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(self):
        self.db = Database()
        self.vector_client = AsyncVectorClient()

    async def scrape_urls(self, urls, collection_id):
        # Format the URLs
        for url in urls:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

        # Get the corresponding collection
        collection = await self.db.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        collection_name = collection["collection_name"]
        logger.info(f"Scraping URL {url} for collection {collection_name}")

        # Insert the URLs
        errors = []
        try:
            success = await insert_urls(collection_name, urls)
        except Exception as e:
            logger.error(f"Failed to insert URLs: {str(e)}")
            errors.append(f"Failed to insert URLs: {str(e)}")

        return {
            "success": success,
            "errors": errors,
        }

    async def crawl_url(
        self,
        base_url: str,
        collection_id: str,
        css_selector: str = "",
        excluded_selector: str = "",
    ):
        # Check if the base url is valid
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url

        # Get the corresponding collection
        collection = await self.db.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")

        collection_name = collection["collection_name"]
        logger.info(f"Crawling URL {base_url} for collection {collection_name}")

        # Fire-and-forget: create background job in ingest service
        job_id = await create_url_crawl_job(
            collection_name=collection_name,
            base_url=base_url,
            css_selector=css_selector,
            excluded_selector=excluded_selector,
        )

        if not job_id:
            return {"success": False, "errors": ["Failed to create job"]}

        return {"success": True, "job_id": job_id, "errors": []}

    async def get_job_status(self, job_id: str):
        status = await get_job_status(job_id)
        if status is None:
            return {"found": False}
        return {"found": True, "status": status}

    async def get_active_job_for_collection(self, collection_id: str):
        collection = await self.db.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")
        collection_name = collection["collection_name"]
        job = await get_active_job(collection_name)
        if job is None:
            return {"found": False}
        return {"found": True, "status": job}
