import aiohttp
from qdrant_client import models

from src.settings import Settings


class AsyncSparseClient:
    def __init__(self):
        self._settings = Settings()
        self.url: str = (
            f"{self._settings.sparse.url}:{self._settings.sparse.port}/embed"
        )

    async def calc_sparse_embeddings(self, texts: str):
        async with aiohttp.ClientSession() as session:
            data: dict = {"inputs": texts}
            headers: dict = {"Content-Type": "application/json"}

            async with session.post(self.url, headers=headers, json=data) as response:
                if response.status == 200:
                    data = (await response.json())["vectors"]
                    embeddings = [
                        models.SparseVector(
                            indices=vector["indices"], values=vector["values"]
                        )
                        for vector in data
                    ]

                    return embeddings
