import os
import typing as tt
import tempfile
import aiofiles
import pandas as pd
import asyncio
import tiktoken
from typing import AsyncGenerator
from langchain_docling import DoclingLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pymupdf
import pytesseract
from PIL import Image
import logging
import io
from src.settings import Settings
from src.clients.async_dense_client import AsyncDenseClient
from src.clients.async_vector_client import AsyncVectorClient
from src.ingest.character_splitter import chunk_text
from charset_normalizer import from_bytes as detect_encoding_from_bytes

logger = logging.getLogger(__name__)

_settings = Settings()


def num_tokens_from_string(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


_headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
]

_markdown_splitter = MarkdownHeaderTextSplitter(
    _headers_to_split_on, strip_headers=False
)


async def acrawl_chunk_txt(binary_data: bytes) -> list[str]:
    """
    Chunks a text document into smaller segments suitable for vector storage.

    Args:
        binary_data (bytes): The binary data of the text document.

    Returns:
        list[str]: A list of text chunks, each within the embedding context window size.

    Notes:
        - The text is cleaned by removing multiple newlines, spaces, markdown code blocks, and URLs.
        - Chunks smaller than 50 characters, containing only numbers/special characters, or table separators are skipped.
        - If a chunk exceeds the context window, it is further split recursively.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_txt_path = os.path.join(temp_dir, "temp.txt")

        async with aiofiles.open(temp_txt_path, "wb") as txt_file:
            await txt_file.write(binary_data)

        async with aiofiles.open(temp_txt_path, "r", encoding="utf-8") as f:
            text = await f.read()
            _async_dense_client = AsyncDenseClient()

            if await _async_dense_client.get_token_count(text) < int(
                _settings.dense_embedding_window
            ):
                return [text]

            # Preprocess the text to handle special cases
            # Remove multiple newlines and spaces
            text = " ".join(text.split())
            # Remove markdown code blocks
            text = text.replace("```", "")
            # Remove URLs (they can cause issues)
            text = " ".join(
                word
                for word in text.split()
                if not word.startswith(("http://", "https://"))
            )

            chunks = await chunk_text(text)
            final_chunks = []

            for chunk in chunks:
                # Skip empty or too small chunks
                if (
                    not chunk or len(chunk.strip()) < 50
                ):  # Skip chunks smaller than 50 chars
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

                if await _async_dense_client.get_token_count(chunk) > int(
                    _settings.dense_embedding_window
                ):
                    sub_chunks = await chunk_text(chunk)
                    # Filter out empty or too small sub-chunks
                    sub_chunks = [c for c in sub_chunks if c and len(c.strip()) >= 50]
                    final_chunks.extend(sub_chunks)
                else:
                    final_chunks.append(chunk)

            return final_chunks


async def acrawl_chunk_csv(binary_data: bytes) -> list[str]:
    """
    Chunks a CSV file into text segments for vector storage, replacing all single and double quotes with escaped double quotes.

    Args:
        binary_data (bytes): The binary data of the CSV file.

    Returns:
        list[str]: A list of text chunks, each containing CSV rows within the embedding context window size.

    Notes:
        - The CSV is parsed using pandas, and rows are joined with ' | ' as a separator.
        - Each chunk includes the header and one or more rows, ensuring the total token count is within the context window.
        - The header is included in every chunk to maintain context.
        - Replaces all occurrences of ' or " with \" in cell values.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_csv_path = os.path.join(temp_dir, "temp.csv")

        async with aiofiles.open(temp_csv_path, "wb") as txt_file:
            await txt_file.write(binary_data)

        def _read_csv_robust_sync(path: str, raw_bytes: bytes) -> pd.DataFrame:
            common_params = {
                "sep": None,  # sniff delimiter
                "engine": "python",  # tolerant parser
                "on_bad_lines": "skip",
                "dtype": str,
            }

            encodings_to_try: list[str] = ["utf-8", "utf-8-sig"]

            detected_encoding: str | None = None
            try:
                result = detect_encoding_from_bytes(raw_bytes).best()
                if result and result.encoding:
                    detected_encoding = result.encoding

            except Exception:
                detected_encoding = None

            if detected_encoding and detected_encoding.lower() not in [
                e.lower() for e in encodings_to_try
            ]:
                encodings_to_try.append(detected_encoding)

            # Add common alternatives
            encodings_to_try.extend(
                ["cp1252", "latin1", "utf-16", "utf-16le", "utf-16be"]
            )

            last_exception: Exception | None = None

            for enc in encodings_to_try:
                try:
                    return pd.read_csv(path, encoding=enc, **common_params)
                except UnicodeDecodeError as e:
                    last_exception = e
                    continue
                except Exception as e:
                    # Could be a parse error triggered by wrong decoding; try next
                    last_exception = e
                    continue

            # Final fallback: decode to text with replacement and parse from memory
            fallback_encoding = detected_encoding or "utf-8"
            try:
                text = raw_bytes.decode(fallback_encoding, errors="replace")
                return pd.read_csv(io.StringIO(text), **common_params)
            except Exception as e:
                raise e if last_exception is None else last_exception

        try:
            df = await asyncio.to_thread(
                _read_csv_robust_sync, temp_csv_path, binary_data
            )
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise

        # Replace all single and double quotes with escaped double quotes in all cell values
        def replace_quotes(cell):
            if pd.notnull(cell):
                cell_str = str(cell)
                # Replace ' and " with \"
                cell_str = cell_str.replace("'", '\\"').replace('"', '\\"')
                return cell_str
            return cell

        # Apply replacement to all cells
        df = df.apply(lambda col: col.map(replace_quotes))

        header = " | ".join(df.columns)

        lines = [header] + [
            " | ".join(str(cell) for cell in row if pd.notnull(cell))
            for _, row in df.iterrows()
        ]

        _async_dense_client = AsyncDenseClient()

        token_counts = await _async_dense_client.get_token_count(texts=lines)

        chunks = []
        current_chunk = lines[0] + "\n"
        current_tokens = token_counts[0]
        header_tokens = token_counts[0]

        for line, line_tokens in zip(lines[1:], token_counts[1:]):
            if current_tokens + line_tokens > int(_settings.dense_embedding_window):
                chunks.append(current_chunk.strip())

                current_chunk = lines[0] + "\n" + line + "\n"
                current_tokens = header_tokens + line_tokens
            else:
                current_chunk += line + "\n"
                current_tokens += line_tokens

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


async def acrawl_urls(
    crawler_instance: AsyncWebCrawler,
    urls: list[str],
    css_selector: str,
    excluded_selector: str,
) -> AsyncGenerator[dict[str, str], None]:
    """
    Crawls multiple URLs and extracts markdown content based on specified selectors.

    Args:
        urls (list[str]): List of URLs to crawl.
        css_selector (str): CSS selector to extract specific content from the page.
        excluded_selector (str): CSS selector for content to exclude from extraction.

    Yields:
        AsyncGenerator[dict[str, str], None]: A dictionary mapping each URL to its extracted markdown content.

    Notes:
        - Uses AsyncWebCrawler with a headless browser configuration.
        - Results are streamed as they complete, bypassing cache.
    """

    config = CrawlerRunConfig(
        stream=True,
        cache_mode=CacheMode.BYPASS,
        css_selector=css_selector,
        excluded_selector=excluded_selector,
    )

    try:
        runner = await crawler_instance.arun_many(urls=urls, config=config)
        async for result in runner:
            if result.success:
                yield {result.url: result.markdown}
    except Exception:
        # Do not swallow crawler/browser failures; propagate so caller can restart the browser
        raise


async def aurls_to_vectorstore(
    crawler_instance: AsyncWebCrawler,
    collection_name: str,
    urls: list[str],
    css_selector: str,
    excluded_selector: str,
    progress_callback: "tt.Optional[tt.Callable[[dict], None]]" = None,
) -> bool:
    """
    Crawls URLs, chunks their markdown content, and stores the chunks in a vector store.

    Args:
        collection_name (str): Name of the vector store collection.
        urls (list[str]): List of URLs to crawl.
        css_selector (str): CSS selector to extract specific content.
        excluded_selector (str): CSS selector for content to exclude.

    Returns:
        bool: True if the operation succeeds, False otherwise.

    Raises:
        Exception: If an error occurs during crawling or vector store insertion.
    """

    # Normalize and de-duplicate URLs by stripping fragments (anchor-only variants)
    seen: set[str] = set()
    normalized_urls: list[str] = []
    for u in urls:
        base_u = u.split("#")[0]
        if base_u and base_u not in seen:
            seen.add(base_u)
            normalized_urls.append(base_u)

    markdown_generator: AsyncGenerator[dict[str, str], None] = acrawl_urls(
        crawler_instance=crawler_instance,
        urls=normalized_urls,
        css_selector=css_selector,
        excluded_selector=excluded_selector,
    )

    if progress_callback is not None:
        try:
            progress_callback(
                {
                    "processed": 2,
                    "total": 1_000,
                    "progress": 2 / 1_000,
                    "message": "Chunking pages.",
                }
            )  # Show 2/1000 progress initially
        except Exception:
            pass

    try:
        _async_vector_client = AsyncVectorClient()
        urls_to_chunks = {}
        async for url_to_chunks in achunk_markdown(url_to_markdown=markdown_generator):
            for url, chunks in url_to_chunks.items():
                urls_to_chunks[url] = chunks

        if progress_callback is not None:
            try:
                progress_callback(
                    {
                        "processed": 2,
                        "total": 1_000,
                        "progress": 2 / 1_000,
                        "message": "Chunking finished.",
                    }
                )  # Show 2/1000 progress initially
            except Exception:
                pass

        await _async_vector_client.enter_points(
            collection_name=collection_name,
            sources_to_chunks=urls_to_chunks,
            progress_callback=progress_callback,
        )
        return True

    except Exception as e:
        logger.error(f"Error chunking and storing URLs: {e}")
        return False


async def achunk_markdown(
    url_to_markdown: AsyncGenerator[dict[str, str], None],
) -> AsyncGenerator[dict[str, list[str]], None]:
    """
    Chunks markdown content from URLs into smaller segments for vector storage.

    Args:
        url_to_markdown (AsyncGenerator[dict[str, str], None]): Generator yielding dictionaries mapping URLs to markdown content.

    Yields:
        AsyncGenerator[dict[str, list[str]], None]: A dictionary mapping each URL to a list of text chunks.

    Notes:
        - Attempts to split markdown by headers first, falling back to recursive text splitting if no headers are found.
        - Chunks exceeding the context window are further split recursively.
    """
    async for document in url_to_markdown:
        for url, markdown in document.items():
            # Attempt to split by markdown headers
            md_header_chunks = _markdown_splitter.split_text(markdown)

            final_chunks = []

            if md_header_chunks:
                # If headers are found, process them

                _async_dense_client = AsyncDenseClient()

                counts = await _async_dense_client.get_token_count(
                    [chunk.page_content for chunk in md_header_chunks]
                )

                for count, chunk in zip(counts, md_header_chunks):
                    if count > int(_settings.dense_embedding_window):
                        # If a chunk is too large, split it further
                        sub_chunks = await chunk_text(chunk.page_content)
                        final_chunks.extend(sub_chunks)
                    else:
                        final_chunks.append(chunk.page_content)
            else:
                # If no headers are found, use RecursiveCharacterTextSplitter
                final_chunks = await chunk_text(markdown)

            yield {url: final_chunks}


async def acrawl_chunk_pdf(binary_data: bytes) -> list[str]:
    """
    Chunks a PDF document into text segments for vector storage.

    Args:
        binary_data (bytes): The binary data of the PDF document.

    Returns:
        list[str]: A list of text chunks extracted from the PDF.

    Notes:
        - Uses DoclingLoader to extract text from the PDF.
        - Chunks are generated asynchronously from the loader's output.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_path = os.path.join(temp_dir, "temp.pdf")

        async with aiofiles.open(temp_pdf_path, "wb") as pdf_file:
            await pdf_file.write(binary_data)

        loader = DoclingLoader(
            file_path=temp_pdf_path,
        )

        chunks = [chunk.page_content async for chunk in loader.alazy_load()]

        # Fallback if DoclingLoader OCR returns no chunks
        if len(chunks) == 0:
            logger.debug(
                "DoclingLoader returned no chunks, falling back to pymupdf and tesseract"
            )
            doc = pymupdf.open(temp_pdf_path)
            texts = []
            for page in doc:
                try:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    texts.append(pytesseract.image_to_string(img, lang="eng+deu"))
                except Exception as e:
                    logger.error(f"Error getting pixmap: {e}")
                    continue
            text = "\n".join(texts)
            if text.strip():
                chunks = await chunk_text(text)
                final_chunks = []

                for chunk in chunks:
                    # Skip empty or too small chunks
                    if (
                        not chunk or len(chunk.strip()) < 50
                    ):  # Skip chunks smaller than 50 chars
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
                        sub_chunks = [
                            c for c in sub_chunks if c and len(c.strip()) >= 50
                        ]
                        final_chunks.extend(sub_chunks)
                    else:
                        final_chunks.append(chunk)

                chunks = final_chunks

        if len(chunks) == 0:
            raise ValueError("No chunks found")

        return chunks


async def adocument_to_vectorstore(
    data_type: str, collection_name: str, binary_data: bytes, source: str
) -> bool:
    """
    Processes a document (PDF, TXT, or CSV) and stores its chunks in a vector store.

    Args:
        data_type (str): The type of document ('pdf', 'txt', or 'csv').
        collection_name (str): Name of the vector store collection.
        binary_data (bytes): The binary data of the document.
        source (str): The source identifier for the document (e.g., file path or URL).

    Returns:
        bool: True if the document is successfully processed and stored, False otherwise.

    Raises:
        Exception: If an error occurs during chunking or vector store insertion.
    """

    if data_type == "pdf":
        chunks: list[str] = await acrawl_chunk_pdf(binary_data=binary_data)
    elif data_type == "txt":
        chunks: list[str] = await acrawl_chunk_txt(binary_data=binary_data)
    elif data_type == "csv":
        chunks: list[str] = await acrawl_chunk_csv(binary_data=binary_data)
    else:
        raise ValueError(f"Unsupported data type: {data_type}")

    if len(chunks) == 0:
        return False

    source_to_chunks: dict[str, list[str]] = {source: chunks}

    try:
        _async_vector_client = AsyncVectorClient()
        await _async_vector_client.enter_points(
            collection_name=collection_name, sources_to_chunks=source_to_chunks
        )

        return True
    except Exception as e:
        logger.error(f"Error entering points: {e}")
        return False


async def acrawl_url_and_add_to_vectorstore(
    base_url: str,
    crawler_instance: AsyncWebCrawler,
    collection_name: str,
    css_selector: str,
    excluded_selector: str,
    progress_callback: "tt.Optional[tt.Callable[[dict], None]]" = None,
) -> bool:
    """
    Starts a crawl of a base url and adds all pages starting with the base url to the vector store.
    """
    try:
        # Normalize base URL
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url
        if not base_url.endswith("/"):
            base_url = base_url + "/"

        # Strip fragments to avoid crawling anchor-only variants
        base_url = base_url.split("#")[0]

        parsed_base = urlparse(base_url)
        base_netloc = parsed_base.netloc

        # BFS crawl asynchronously to avoid blocking the event loop
        visited: set[str] = set()
        queue: list[str] = [base_url]

        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10)

        if progress_callback is not None:
            try:
                progress_callback(
                    {
                        "processed": 0,
                        "total": 1_000,
                        "progress": 0.0,
                        "message": "Crawling pages.",
                    }
                )
            except Exception:
                pass

        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector
        ) as session:
            while queue:
                # Yield back to the loop to keep HTTP server responsive
                await asyncio.sleep(0)

                current_url = queue.pop(0)
                if current_url in visited:
                    continue
                visited.add(current_url)

                try:
                    async with session.get(current_url, allow_redirects=True) as resp:
                        if resp.status != 200:
                            continue
                        content_type = resp.headers.get("Content-Type", "")
                        # Skip non-HTML
                        if "text/html" not in content_type:
                            continue
                        text = await resp.text(errors="ignore")
                except aiohttp.ClientError:
                    continue

                soup = BeautifulSoup(text, "html.parser")
                for link in soup.find_all("a", href=True):
                    href = link.get("href")
                    if not href:
                        continue
                    if href.startswith("javascript:") or href.startswith("mailto:"):
                        continue
                    full_url = urljoin(current_url, href)
                    # Remove URL fragment (e.g., #section)
                    full_url = full_url.split("#")[0]
                    parsed = urlparse(full_url)
                    # Keep only same host and within base path
                    if parsed.netloc != base_netloc:
                        continue
                    if not full_url.startswith(base_url):
                        continue
                    if full_url not in visited and full_url not in queue:
                        queue.append(full_url)

                # Update crawl progress approximately
                if progress_callback is not None:
                    try:
                        processed = len(visited)
                        total_estimate = processed + len(queue)
                        progress_callback(
                            {
                                "processed": processed,
                                "total": max(total_estimate, 1),
                                "progress": processed / max(total_estimate, 1),
                                "message": f"Crawling pages ({processed} discovered)",
                                "last_url": current_url,
                            }
                        )
                    except Exception:
                        pass

        links = list(visited)

        # Initialize vectorization progress
        if progress_callback is not None:
            try:
                total = max(len(links), 1)
                progress_callback(
                    {
                        "processed": 0,
                        "total": total,
                        "progress": 0.0,
                        "message": f"Crawling finished. ({max(len(links), 1)} links)",
                    }
                )
            except Exception:
                pass

        success = await aurls_to_vectorstore(
            crawler_instance=crawler_instance,
            collection_name=collection_name,
            urls=links,
            css_selector=css_selector,
            excluded_selector=excluded_selector,
            progress_callback=progress_callback,
        )

        return success

    except Exception as e:
        logger.error(f"Error crawling and adding to vector store: {e}")
        return False
