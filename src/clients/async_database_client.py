from pymongo import AsyncMongoClient
import msgpack

from src.settings import Settings


class AsyncDatabaseClient:
    _client = None
    _settings = Settings()

    @classmethod
    async def get_client(cls):
        """Initialize and return a singleton AsyncMongoClient."""
        if cls._client is None:
            uri = f"mongodb://{cls._settings.mongo_username.get_secret_value()}:{cls._settings.mongo_password.get_secret_value()}@{cls._settings.mongo.url}:{cls._settings.mongo.port}/admin"
            cls._client = AsyncMongoClient(uri)
        return cls._client

    @classmethod
    async def close_client(cls):
        """Close the AsyncMongoClient when the application shuts down."""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None

    async def get_collection(self, database_name: str, collection_name: str):
        """Get a collection from the database."""
        client = await self.get_client()
        database = client[database_name]
        return database[collection_name]

    async def find_one(
        self, database_name: str, collection_name: str, filter: dict, sort: list
    ):
        """Find one document in the collection."""
        collection = await self.get_collection(database_name, collection_name)
        return await collection.find_one(filter, sort=sort)

    def _unpack_ext(self, code, data):
        """Custom unpacking for msgpack ExtType."""
        if code == 5:
            try:
                nested_data = msgpack.unpackb(data, raw=True)
                return nested_data
            except Exception as e:
                print(f"Error unpacking ExtType: {e}")
                return data
        return msgpack.ExtType(code, data)

    async def get_latest_checkpoint(self, thread_id: str) -> list:
        """Get the latest checkpoint from the collection."""
        # Find the latest checkpoint
        latest_checkpoint = await self.find_one(
            database_name="checkpointing_db",
            collection_name="checkpoints_aio",
            filter={"thread_id": thread_id},
            sort=[("_id", -1)],
        )

        if not latest_checkpoint or "checkpoint" not in latest_checkpoint:
            return []

        # Unpack the msgpack data from the latest checkpoint
        checkpoint_unpacked = msgpack.unpackb(
            latest_checkpoint["checkpoint"], raw=True, ext_hook=self._unpack_ext
        )[b"channel_values"][b"messages"]

        messages = []
        for message in checkpoint_unpacked:
            if (
                isinstance(message, list)
                and len(message) > 2
                and isinstance(message[2], dict)
            ):
                content = message[2].get(b"content", b"").decode()
                messages.append(content)

        return messages

    async def delete(self, thread_id: str):
        """Delete all checkpoints for a given thread_id."""
        checkpointing_writes_collection = await self.get_collection(
            database_name="checkpointing_db", collection_name="checkpoint_writes_aio"
        )
        checkpointing_collection = await self.get_collection(
            database_name="checkpointing_db", collection_name="checkpoints_aio"
        )

        await checkpointing_writes_collection.delete_many({"thread_id": thread_id})
        await checkpointing_collection.delete_many({"thread_id": thread_id})
