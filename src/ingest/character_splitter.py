from src.clients.async_dense_client import AsyncDenseClient
from src.settings import Settings


_settings = Settings()


async def chunk_text(text: str) -> list[str]:
    _async_dense_client = AsyncDenseClient()

    token_amount = await _async_dense_client.get_token_count(text)
    if token_amount < int(_settings.dense_embedding_window):
        return [text]
    else:
        charakter_amount = int(len(text))
        div_round_up = -(-token_amount // int(_settings.dense_embedding_window))
        final_chunks = await split_string(text, div_round_up, charakter_amount)

        return final_chunks


async def split_string(
    text: str, split_amount: int, charakter_amount: int, overlap: int = 100
) -> list[str]:
    if split_amount <= 1:
        return [text]

    schritt = max(1, (charakter_amount - overlap * (split_amount - 1)) // split_amount)

    chunks = []
    for i in range(split_amount):
        start = i * schritt
        if i < split_amount - 1:
            end = start + schritt + overlap
            chunk = text[start:end]

            # Try to find the last sentence boundary (., !, or ?)
            sentence_endings = [".", "!", "?"]
            last_boundary = -1
            for ending in sentence_endings:
                pos = chunk.rfind(ending)
                if pos > last_boundary:
                    last_boundary = pos

            # If we found a sentence boundary, end the chunk there (include the punctuation)
            if (
                last_boundary > schritt * 0.8
            ):  # Only use if it's at least 80% through the chunk
                chunk = text[start : start + last_boundary + 1]

            chunks.append(chunk)
        else:
            # Last chunk gets everything remaining
            chunks.append(text[start:])

    return chunks


async def main():
    with open("D:\Downloads\der_kleine_stein_moo.txt", "r", encoding="utf-8") as f:
        text = f.read()

    text = " ".join(text.split())
    # Remove markdown code blocks
    text = text.replace("```", "")
    # Remove URLs (they can cause issues)
    text = " ".join(
        word for word in text.split() if not word.startswith(("http://", "https://"))
    )

    chunks = await chunk_text(text)

    final_chunks = []

    for chunk in chunks:
        # Skip empty or too small chunks
        if not chunk or len(chunk.strip()) < 50:  # Skip chunks smaller than 50 chars
            continue

        # Skip chunks that are just numbers or special characters
        if (
            chunk.strip()
            .replace(".", "")
            .replace(",", "")
            .replace("|", "")
            .replace("-", "")
            .isdigit()
        ):
            continue

        # Skip chunks that are just table separators
        if all(c in "|-: " for c in chunk.strip()):
            continue

        _async_dense_client = AsyncDenseClient()

        if await _async_dense_client.get_token_count(chunk) > int(
            _settings.dense_embedding_window
        ):
            sub_chunks = await chunk_text(chunk)
            # Filter out empty or too small sub-chunks
            sub_chunks = [c for c in sub_chunks if c and len(c.strip()) >= 50]
            final_chunks.extend(sub_chunks)
        else:
            final_chunks.append(chunk)

    for chunk in final_chunks:
        print("Chunk: ", chunk, "\n\n")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
