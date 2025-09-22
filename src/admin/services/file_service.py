import os
import tempfile
import csv
from werkzeug.utils import secure_filename
import urllib.parse
from src.admin.database import Database
from src.clients.async_vector_client import AsyncVectorClient
from src.admin.services.collection_service import CollectionService
import aiofiles
from src.settings import Settings
from src.clients.async_ingest_client import insert_document
import logging

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self):
        self._settings = Settings()
        self.db = Database()
        self.vector_client = AsyncVectorClient()
        self.collection_service = CollectionService()
        self.ingest_service_url = (
            f"{self._settings.ingest.url}:{self._settings.ingest.port}"
        )

    async def process_csv(self, file_path):
        """Process CSV file and convert to text format for vectorization"""
        csv_content = []
        try:
            async with aiofiles.open(
                file_path, "r", encoding="utf-8", newline=""
            ) as csvfile:
                content = await csvfile.read()
                # First determine the dialect/delimiter
                dialect = csv.Sniffer().sniff(content[:4096])

                # Read as dictionary if the CSV has headers
                has_header = csv.Sniffer().has_header(content[:4096])

                # Process the content
                if has_header:
                    reader = csv.DictReader(content.splitlines(), dialect=dialect)
                    headers = reader.fieldnames
                    csv_content.append("# " + ", ".join(headers))
                    for row in reader:
                        row_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
                        csv_content.append(row_str)
                else:
                    reader = csv.reader(content.splitlines(), dialect=dialect)
                    for row in reader:
                        csv_content.append(", ".join(row))

            # Join the rows with line breaks
            return "\n".join(csv_content)
        except Exception as e:
            raise ValueError(f"Error processing CSV file: {str(e)}")

    async def upload_files(self, files, collection_id):
        """Process uploaded files and return processed file data"""
        # Check if collection exists
        collection = await self.collection_service.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        collection_name = collection.collection_name

        errors = []

        for file in files:
            if file.filename == "":
                continue

            filename = secure_filename(file.filename)

            # Save file to temp directory
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            content = await file.read()
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(content)

            success = True
            try:
                if (
                    filename.endswith(".pdf")
                    or filename.endswith(".txt")
                    or filename.endswith(".csv")
                ):
                    logger.info(
                        f"Processing file: {filename}, for collection: {collection_name}"
                    )
                    success_temp = await insert_document(temp_path, collection_name)
                    if not success_temp:
                        success = False
                else:
                    raise ValueError(f"Unsupported file type: {filename}")

            except Exception as e:
                logger.error(
                    f"Error processing file {filename}: {str(e)}", exc_info=True
                )
                errors.append({"filename": filename, "error": str(e)})
            finally:
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Error deleting temp file {temp_path}: {str(e)}")

        return success, errors

    async def get_collection_files(self, collection_id):
        """Get all files for a given collection"""
        try:
            collection = await self.collection_service.get_collection(collection_id)
            if not collection:
                raise ValueError(f"Collection {collection_id} not found")

            collection_name = collection.collection_name
            logger.info(f"Getting files for collection: {collection_name}")

            # Get points from the vector client
            points = await self.vector_client.get_points(collection_name)

            # Format the response
            formatted_points = {}
            for point in points:
                file_name = point.payload.get("source")
                if file_name and file_name not in formatted_points:
                    formatted_points[file_name] = {"file_name": file_name, "count": 1}
                elif file_name:
                    formatted_points[file_name]["count"] += 1

            result = list(formatted_points.values())
            logger.info(f"Found {len(result)} files in collection {collection_id}")
            return result
        except Exception as e:
            logger.error(f"Error in get_collection_files: {str(e)}", exc_info=True)
            raise

    async def get_points_for_file(self, collection_id, filename):
        """Get all points for file for a given collection"""
        try:
            collection = await self.collection_service.get_collection(collection_id)
            if not collection:
                raise ValueError(f"Collection {collection_id} not found")

            collection_name = collection.collection_name
            logger.info(
                f"Getting points for file {filename} in collection {collection_name}"
            )

            # Get points from the vector client
            points = await self.vector_client.get_points(collection_name)

            # Normalize function to handle encoded/decoded URL variants consistently
            def normalize(value: str) -> str:
                try:
                    # Unquote up to twice to collapse common double-encoding cases
                    once = urllib.parse.unquote(value)
                    twice = urllib.parse.unquote(once)
                    return twice
                except Exception:
                    return value

            filename_norm_candidates = {filename, normalize(filename)}

            # Filter points comparing both raw and normalized forms
            matching_points = []
            for point in points:
                source = point.payload.get("source")
                if not source:
                    continue
                source_norm_candidates = {source, normalize(source)}
                if filename_norm_candidates & source_norm_candidates:
                    matching_points.append(point)

            result = []
            for point in matching_points:
                result.append({"id": point.id, "text": point.payload.get("text")})

            logger.info(
                f"Found {len(result)} points for file {filename} in collection {collection_id}"
            )
            return result
        except Exception as e:
            logger.error(f"Error in get_points_for_file: {str(e)}", exc_info=True)
            raise

    async def update_file_chunk(self, collection_id, chunk_id, new_text):
        """Update a specific chunk of a file"""
        try:
            # No longer validate chunk_id - all IDs including 0 are valid now

            collection = await self.collection_service.get_collection(collection_id)
            if not collection:
                raise ValueError(f"Collection {collection_id} not found")

            collection_name = collection.collection_name

            # Get all points and find the matching one by ID - this works regardless of ID format
            all_points = await self.vector_client.get_points(collection_name)
            matching_point = None

            for point in all_points:
                # Convert IDs to strings for comparison to handle both numeric and UUID IDs
                if str(point.id) == str(chunk_id):
                    matching_point = point
                    break

            if not matching_point:
                raise ValueError(f"Chunk {chunk_id} not found")

            logger.info(
                f"Found matching point with ID {matching_point.id} for chunk_id {chunk_id}"
            )

            # Update the point with new text while preserving metadata
            success = await self.vector_client.update_point(
                collection_name=collection_name,
                point_id=matching_point.id,  # Use the exact ID format from the database
                text=new_text,
                source=matching_point.payload.get("source"),
            )

            return success
        except Exception as e:
            logger.error(f"Error in update_file_chunk: {str(e)}", exc_info=True)
            raise

    async def delete_chunk(self, collection_id, chunk_id):
        """Delete a specific chunk of a collection"""
        try:
            collection = await self.collection_service.get_collection(collection_id)
            if not collection:
                raise ValueError(f"Collection {collection_id} not found")

            collection_name = collection.collection_name
            logger.info(f"Deleting chunk {chunk_id} from collection {collection_name}")

            # Make sure the chunk is part of the collection
            points = await self.vector_client.get_points(collection_name)
            if chunk_id not in [point.id for point in points]:
                raise ValueError(
                    f"Chunk {chunk_id} not found in collection {collection_name}"
                )

            # Delete the point from the vector client
            await self.vector_client.remove_points(collection_name, [chunk_id])
            return True
        except Exception as e:
            logger.error(f"Error in delete_chunk: {str(e)}", exc_info=True)
            raise

    async def delete_file(self, collection_id, filename):
        """Delete all chunks associated with a file"""
        try:
            collection = await self.collection_service.get_collection(collection_id)
            if not collection:
                raise ValueError(f"Collection {collection_id} not found")

            collection_name = collection.collection_name
            logger.info(f"Deleting file {filename} from collection {collection_name}")

            # Get all points for the file
            points = await self.vector_client.get_points(collection_name)

            def normalize(value: str) -> str:
                try:
                    once = urllib.parse.unquote(value)
                    twice = urllib.parse.unquote(once)
                    return twice
                except Exception:
                    return value

            filename_norm_candidates = {filename, normalize(filename)}

            points_to_delete = []
            for point in points:
                source = point.payload.get("source")
                if not source:
                    continue
                source_norm_candidates = {source, normalize(source)}
                if filename_norm_candidates & source_norm_candidates:
                    points_to_delete.append(point.id)

            if not points_to_delete:
                logger.warning(
                    f"No points found for file {filename} in collection {collection_id}"
                )
                return False

            # Delete all points
            logger.info(f"Deleting {len(points_to_delete)} points for file {filename}")
            await self.vector_client.remove_points(collection_name, points_to_delete)
            return True
        except Exception as e:
            logger.error(f"Error in delete_file: {str(e)}", exc_info=True)
            raise
