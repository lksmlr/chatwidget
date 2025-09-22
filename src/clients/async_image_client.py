from openai import AsyncOpenAI, APIConnectionError

from src.clients.utils.exceptions import NoResponseException
from src.settings import Settings


class AsyncImageModelClient:
    def __init__(self):
        self._settings = Settings()
        self.model = AsyncOpenAI(base_url=self._settings.llm.url, api_key="empty")

    async def image_to_text(self, base64_str: str) -> str:
        try:
            response = await self.model.chat.completions.create(
                model=self._settings.llm.name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe the picture in German. Answer in detail but with few words as possible.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"{base64_str}"},
                            },
                        ],
                    }
                ],
                max_tokens=1024,
            )

            return response.choices[0].message.content

        except APIConnectionError as e:
            print(f"LLM is not responding right now - Error: {e}")

            raise NoResponseException()


async def main():
    client = AsyncImageModelClient()
    # Example usage
    base64_str = "https://image.stern.de/34972122/t/xE/v2/w1440/r1.7778/-/wasserhaltige-snacks.jpg"
    # base64_str = "data:image/png;base64,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"
    result = await client.image_to_text(base64_str)
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
