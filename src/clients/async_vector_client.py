from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import PointStruct
from qdrant_client.models import QueryResponse
import warnings
import uuid
import typing as tt

from src.clients.async_dense_client import AsyncDenseClient
from src.clients.async_sparse_client import AsyncSparseClient
from src.settings import Settings


warnings.filterwarnings(
    "ignore", message="Api key is used with an insecure connection."
)


class AsyncVectorContextManager:
    def __init__(self):
        self._settings = Settings()
        self.client = AsyncQdrantClient(
            url=self._settings.qdrant.url,
            port=self._settings.qdrant.port,
            api_key=self._settings.qdrant_key.get_secret_value(),
        )

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()


class AsyncVectorClient:
    def __init__(self):
        self._settings = Settings()
        self.dense_client = AsyncDenseClient()
        self.sparse_client = AsyncSparseClient()

    async def create_collection(self, collection_name: str) -> None:
        async with AsyncVectorContextManager() as client:
            if not await client.collection_exists(collection_name=collection_name):
                try:
                    await client.create_collection(
                        collection_name=collection_name,
                        vectors_config={
                            "dense": models.VectorParams(
                                size=int(self._settings.dense_embedding_dimension),
                                distance=models.Distance.COSINE,
                            )
                        },
                        sparse_vectors_config={
                            "sparse": models.SparseVectorParams(
                                index=models.SparseIndexParams(
                                    on_disk=False,
                                ),
                            )
                        },
                    )

                    print(f"created collection {collection_name}")

                except Exception as e:
                    print(f"Error creating collection {collection_name}: {str(e)}")
                    raise

            else:
                print(f"collection already exists {collection_name}")

    async def enter_point(self, collection_name: str, text: str, source: str) -> None:
        async with AsyncVectorContextManager() as client:
            embeddings_dense: list = await self.dense_client.calc_dense_embeddings(
                text=text, query=False
            )
            embeddings_sparse: dict = await self.sparse_client.calc_sparse_embeddings(
                text=text
            )

            # Generate a unique UUID string as the point ID
            unique_id = str(uuid.uuid4())

            await client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=unique_id,
                        vector={"dense": embeddings_dense, "sparse": embeddings_sparse},
                        payload={"source": source, "text": text},
                    )
                ],
            )

            print(f"point with id: {unique_id} got entered")

    async def enter_points(
        self,
        collection_name: str,
        sources_to_chunks: dict[str, list[str]],
        progress_callback: tt.Optional[tt.Callable[[dict], None]] = None,
        batch_size: int = 64,
    ) -> None:
        """Enter multiple points into the collection in batches and report progress.

        Progress callback signature:
            callback({ 'phase': 'upsert', 'processed': int, 'total': int, 'progress': float })
        """
        async with AsyncVectorContextManager() as client:
            # Determine total chunks to be inserted (used for progress)
            total_chunks = sum(len(chunks) for chunks in sources_to_chunks.values())
            processed = 0

            for url, chunks in sources_to_chunks.items():
                # Prepare texts
                texts = [f"Source: {url}\nContent: {chunk}" for chunk in chunks]

                # Embeddings (dense & sparse)
                embeddings_dense: list = await self.dense_client.calc_dense_embeddings(
                    texts=texts
                )
                print(f"Calculated {len(embeddings_dense)} dense embeddings")

                embeddings_sparse: list = (
                    await self.sparse_client.calc_sparse_embeddings(texts=texts)
                )
                print(f"Calculated {len(embeddings_sparse)} sparse embeddings")

                # Build point structs for this URL and upsert in batches
                points_for_url = [
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector={"dense": dense, "sparse": sparse},
                        payload={"source": url, "text": text},
                    )
                    for text, sparse, dense in zip(
                        texts, embeddings_sparse, embeddings_dense
                    )
                ]

                # Upsert in batches and report progress
                for i in range(0, len(points_for_url), batch_size):
                    batch = points_for_url[i : i + batch_size]
                    await client.upsert(collection_name=collection_name, points=batch)
                    processed += len(batch)
                    if progress_callback is not None and total_chunks > 0:
                        try:
                            progress_callback(
                                {
                                    "processed": processed,
                                    "total": total_chunks,
                                    "progress": processed / total_chunks,
                                    "message": "Calculating embeddings.",
                                }
                            )
                        except Exception:
                            pass

            print(f"{processed} points got entered")

    async def remove_point(self, id: str):
        """Remove a single point by ID"""
        async with AsyncVectorContextManager() as client:
            await client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[id]),
            )

            print(f"point with id: {id} got removed")

    async def get_relevant_context(self, collection_name: str, question: str) -> str:
        async with AsyncVectorContextManager() as client:
            embeddings_dense: list = (
                await self.dense_client.calc_dense_embeddings(texts=question)
            )[0]

            embeddings_sparse: dict = (
                await self.sparse_client.calc_sparse_embeddings(texts=question)
            )[0]

            query_response: QueryResponse = await client.query_points(
                collection_name=collection_name,
                prefetch=[
                    models.Prefetch(query=embeddings_sparse, using="sparse", limit=20),
                    models.Prefetch(query=embeddings_dense, using="dense", limit=20),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=10,
            )

            result = [point.payload["text"] for point in query_response.points]

            return ". ".join(result)

    async def get_points(self, collection_name: str) -> list:
        async with AsyncVectorContextManager() as client:
            count_result = await client.count(collection_name=collection_name)
            count = count_result.count

            if count == 0:
                return []

            points_result = await client.scroll(
                collection_name=collection_name,
                with_vectors=True,
                with_payload=True,
                limit=count,
            )

            return points_result[0]

    async def remove_file(self, filename: str):
        """Remove all points associated with a filename"""

        async with AsyncVectorContextManager() as client:
            # Get all points for this file
            points = await client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source", match=models.MatchValue(value=filename)
                        )
                    ]
                ),
                with_payload=False,
                with_vectors=False,
            )[0]

            # Extract point IDs
            point_ids = [point.id for point in points]

            if point_ids:
                # Delete all points
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(points=point_ids),
                )

    async def get_point(self, collection_name: str, point_id: str) -> any:
        """Get a single point by ID"""
        async with AsyncVectorContextManager() as client:
            try:
                # Handle both numeric and UUID string IDs
                id_to_use = point_id

                # Log the attempt for debugging
                print(
                    f"Attempting to retrieve point with ID: {id_to_use} from collection {collection_name}"
                )

                result = await client.retrieve(
                    collection_name=collection_name,
                    ids=[id_to_use],
                    with_payload=True,
                    with_vectors=False,
                )
                if result and len(result) > 0:
                    return result[0]

                # If ID is numeric string, try as int
                if isinstance(point_id, str) and point_id.isdigit():
                    try:
                        id_as_int = int(point_id)
                        print(f"Retrying with numeric ID: {id_as_int}")
                        result = await client.retrieve(
                            collection_name=collection_name,
                            ids=[id_as_int],
                            with_payload=True,
                            with_vectors=False,
                        )
                        if result and len(result) > 0:
                            return result[0]
                    except Exception as e:
                        print(f"Error retrieving with numeric ID {id_as_int}: {str(e)}")

                print(f"Point not found with ID: {point_id}")
                return None
            except Exception as e:
                print(f"Error getting point {point_id}: {str(e)}")
                return None

    async def update_point(
        self, collection_name: str, point_id, text: str, source: str
    ) -> bool:
        """Update an existing point with new text while preserving metadata.

        Args:
            collection_name: Name of the collection
            point_id: ID of the point to update (use the exact ID from the database)
            text: New text content
            source: Source metadata

        Returns:
            bool: True if successful, False otherwise
        """
        async with AsyncVectorContextManager() as client:
            try:
                # Log the attempt for debugging
                print(
                    f"Updating point with exact ID: {point_id} in collection {collection_name}"
                )

                # Generate new embeddings for the updated text
                embeddings_dense = await self.dense_client.calc_dense_embeddings(
                    texts=text
                )
                embeddings_sparse = await self.sparse_client.calc_sparse_embeddings(
                    texts=text
                )

                # Update the point with new text and embeddings
                await client.overwrite_payload(
                    collection_name=collection_name,
                    payload={
                        "source": source,
                        "text": text,
                    },
                    points=[point_id],
                )

                await client.update_vectors(
                    collection_name=collection_name,
                    points=[
                        models.PointVectors(
                            id=point_id,
                            vector={
                                "dense": embeddings_dense[0],
                                "sparse": embeddings_sparse[0],
                            },
                        )
                    ],
                )

                print(f"Point with id: {point_id} updated successfully")
                return True
            except Exception as e:
                print(f"Error updating point {point_id}: {str(e)}")
                return False

    async def remove_points(self, collection_name: str, point_ids: list) -> None:
        """Remove multiple points by IDs"""
        if not point_ids:
            return

        async with AsyncVectorContextManager() as client:
            try:
                await client.delete(
                    collection_name=collection_name,
                    points_selector=models.PointIdsList(points=point_ids),
                )
                print(
                    f"Removed {len(point_ids)} points from collection {collection_name}"
                )
            except Exception as e:
                print(f"Error removing points: {str(e)}")
                raise

    async def delete_collection(self, collection_name: str) -> None:
        """Delete an entire collection"""
        async with AsyncVectorContextManager() as client:
            try:
                await client.delete_collection(collection_name=collection_name)
                print(f"Collection {collection_name} deleted successfully")
                return True
            except Exception as e:
                print(f"Error deleting collection {collection_name}: {str(e)}")
                raise

    async def fix_invalid_ids(self, collection_name: str) -> dict:
        """Fix any points with ID 0 by reassigning them valid UUIDs.
        Returns a dictionary with counts of fixed points and any errors encountered."""
        result = {"fixed_count": 0, "errors": []}

        try:
            async with AsyncVectorContextManager() as client:
                # Get all points
                all_points = await self.get_points(collection_name)

                # Find points with ID 0
                invalid_points = [
                    point for point in all_points if point.id == 0 or point.id == "0"
                ]

                if not invalid_points:
                    return {"fixed_count": 0, "message": "No invalid IDs found"}

                print(
                    f"Found {len(invalid_points)} points with invalid ID 0 in collection {collection_name}"
                )

                # Fix each invalid point
                for point in invalid_points:
                    try:
                        # Create new embeddings from the text
                        text = point.payload.get("text", "")
                        source = point.payload.get("source", "")

                        embeddings_dense = (
                            await self.dense_client.calc_dense_embeddings(
                                text=text, query=False
                            )
                        )
                        embeddings_sparse = (
                            await self.sparse_client.calc_sparse_embeddings(text=text)
                        )

                        # Generate a new UUID for the point
                        new_id = str(uuid.uuid4())

                        # Insert a new point with valid UUID
                        await client.upsert(
                            collection_name=collection_name,
                            points=[
                                PointStruct(
                                    id=new_id,
                                    vector={
                                        "dense": embeddings_dense,
                                        "sparse": embeddings_sparse,
                                    },
                                    payload={"source": source, "text": text},
                                )
                            ],
                        )

                        print(f"Fixed point by assigning new UUID {new_id}")
                        result["fixed_count"] += 1

                    except Exception as e:
                        error_msg = f"Error fixing point: {str(e)}"
                        print(error_msg)
                        result["errors"].append(error_msg)

                # Now delete the invalid points
                try:
                    if result["fixed_count"] > 0:
                        await client.delete(
                            collection_name=collection_name,
                            points_selector=models.PointIdsList(points=[0]),
                        )
                        print(f"Deleted {result['fixed_count']} points with ID 0")
                except Exception as e:
                    error_msg = f"Error deleting invalid points: {str(e)}"
                    print(error_msg)
                    result["errors"].append(error_msg)

                return result

        except Exception as e:
            error_msg = f"Error in fix_invalid_ids: {str(e)}"
            print(error_msg)
            result["errors"].append(error_msg)
            return result
