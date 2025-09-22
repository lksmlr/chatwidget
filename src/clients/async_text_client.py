from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from openai import APIConnectionError

from src.settings import Settings
from src.clients.utils.exceptions import NoResponseException


class AsyncTextModelClient:
    def __init__(self):
        self._settings = Settings()
        self.model = ChatOpenAI(
            base_url=self._settings.llm.url,
            api_key="empty",
            model=self._settings.llm.name,
        )

    async def chat(self, messages: list[BaseMessage]):
        try:
            return await self.model.ainvoke(messages)

        except APIConnectionError as e:
            print(f"LLM is not responding right now - Error: {e}")
            raise NoResponseException
