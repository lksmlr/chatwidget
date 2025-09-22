import aiohttp
from typing import Union

from src.settings import Settings


class AsyncDenseClient:
    def __init__(self):
        self._settings = Settings()
        self.embed_endpoint: str = (
            f"{self._settings.dense.url}:{self._settings.dense.port}/embed"
        )
        self.tokenize_endpoint: str = (
            f"{self._settings.dense.url}:{self._settings.dense.port}/tokenize"
        )

    async def calc_dense_embeddings(self, texts: Union[list[str], str]) -> list[str]:
        if isinstance(texts, str):
            texts = [texts]

        data: dict = {"inputs": texts}

        headers: dict = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                self.embed_endpoint, json=data, headers=headers
            )

            return (await response.json())["vectors"]

    async def get_token_count(
        self, texts: Union[list[str], str]
    ) -> Union[list[int], int]:
        data: dict = {"inputs": texts}

        headers: dict = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                self.tokenize_endpoint, json=data, headers=headers
            )

            return (await response.json())["counts"]
