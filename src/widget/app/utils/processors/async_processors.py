import sys
import os

from src.settings import Settings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from abc import ABC, abstractmethod
import base64
import tempfile
import os
from langchain_core.prompts import ChatPromptTemplate
import io
import aiofiles

from src.widget.app.utils.state import State
from src.clients.async_text_client import AsyncTextModelClient
from src.clients.async_image_client import AsyncImageModelClient
from src.clients.async_vector_client import AsyncVectorClient
from src.widget.app.utils.exceptions import GraphException
from langchain_docling import DoclingLoader


class AsyncProcessor(ABC):
    """Abstract base class for asynchronous processors."""

    @abstractmethod
    async def process(self, state: State) -> dict:
        """
        Process the data from the user input.

        Args:
            state (State): The current state containing user input and messages.

        Returns:
            dict: The processed state or result.
        """
        pass


class AsyncLLMProcessor(AsyncProcessor):
    def __init__(self):
        """
        Initialize the AsyncLLMProcessor with a text model client.

        Attributes:
            text_client (AsyncTextModelClient): Client for handling text-based model interactions.
        """
        self.text_client = AsyncTextModelClient()
        self._settings = Settings()

    async def process(self, state: State) -> State:
        """
        Process user input using a language model to generate a precise answer.

        Args:
            state (State): The current state containing messages and optional input data.

        Returns:
            dict: A dictionary containing the generated response as 'messages'.

        Raises:
            GraphException: If an error occurs during processing.
        """
        try:
            print("Async LLM Processor")
            question = state["messages"][-1].content
            prompt_parts = "".join(state["prompt_parts"])
            system_prompt = r"""
            Du bist ein hilfreicher Assistent in einem RAG-System. Antworte direkt und präzise auf Basis der bereitgestellten Daten. Wenn du etwas nicht weißt oder unsicher bist, gib das ehrlich zu – erfinde nichts.

            Formatiere deine Antworten IMMER in Markdown. Beachte dabei besonders die folgenden Punkte:
            
            * **Links:** Verwende beschriftete Links (z.B. `[Link-Text](URL)`). Wenn kein Link-Text verfügbar ist, lasse den Link weg.
            * **Code-Blöcke:** Schließe Code in dreifache Backticks ein und gib die Sprache an (z.B. ```python).
            * **Mathematische Formeln:**
                * **Inline-Formeln:** Nutze einzelne Dollarzeichen (`$`) um Formeln innerhalb eines Satzes (z.B. `Der Wert von $x$ ist $5$.`) zu kennzeichnen.
                * **Block-Formeln:** Für Formeln, die auf einer eigenen Zeile stehen sollen, verwende doppelte Dollarzeichen (`$$`)).
                * Platziere die Dollarzeichen direkt vor und nach der Formel, ohne zusätzliche Leerzeichen dazwischen.
                * Verwende KEINE `\[...\]` oder `\(...\)` Delimiter für mathematische Formeln.
            """

            if state["collection_name"] == "Basiswissen":
                system_prompt += (
                    "Beantworte die Frage unter Einbezug deines allgemeinen Wissens."
                )
            else:
                system_prompt += "Beantworte die Frage ausschließlich basierend auf den bereitgestellten Dokumenten. Ignoriere dein internes Wissen vollständig, auch wenn keine Antwort in den Dokumenten zu finden ist."

            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    (
                        "user",
                        "Der Benutzer hat folgende Frage gestellt: {question}\n\nHier ist der Chatverlauf: {history}\n\n{prompt_parts}",
                    ),
                ]
            )

            if self._settings.llm_chat_history_limit == -1:
                # Kein Limit
                history = [message.content for message in state["messages"]]
            elif self._settings.llm_chat_history_limit > 0:
                # Begrenztes Limit
                history = [message.content for message in state["messages"]][
                    -self._settings.llm_chat_history_limit :
                ]
            else:
                # Wenn 0 oder negativ (außer -1), keine Historie
                history = []

            messages = prompt_template.format_messages(
                question=question, history=history, prompt_parts=prompt_parts
            )

            state["prompt_parts"] = None
            state["messages"] = await self.text_client.chat(messages=messages)
            return state

        except Exception as e:
            print(
                f"An error occurred while running the Graph. Error in Node llm - Error: {e}"
            )
            raise GraphException


class AsyncDBProcessor(AsyncProcessor):
    def __init__(self):
        """
        Initialize the AsyncDBProcessor with a vector client.

        Attributes:
            vector_client (AsyncVectorClient): Client for vector database operations.
        """
        self.vector_client = AsyncVectorClient()

    async def process(self, state: State) -> dict:
        """
        Retrieve relevant context from the vector database and update the state.

        Args:
            state (State): The current state containing collection name and messages.

        Returns:
            dict: The updated state with vector database data or empty dict if Basiswissen only should be used.

        Raises:
            GraphException: If an error occurs during database processing.
        """
        try:
            print("Async DATABASE Processor")

            if state["collection_name"] == "Basiswissen":
                return state

            search_results = await self.vector_client.get_relevant_context(
                state["collection_name"], state["messages"][-1].content
            )
            if search_results:
                print(search_results)
                state["vector_db_data"] = search_results
                state["prompt_parts"] = [
                    f"Die folgenden abgerufenen Informationen sind für die Beantwortung der Frage des Benutzers relevant: {state['vector_db_data']}.\n\n"
                ]
            else:
                state["vector_db_data"] = ""

            return state

        except Exception as e:
            print(
                f"An error occurred while running the Graph. Error in Node database - Error: {e}"
            )
            raise GraphException


class AsyncPDFProcessor(AsyncProcessor):
    def __init__(self):
        """
        Initialize the AsyncPDFProcessor with a text model client.

        Attributes:
            text_client (AsyncTextModelClient): Client for handling text-based model interactions.
        """
        self.text_client = AsyncTextModelClient()

    async def process(self, state: State) -> dict:
        """
        Process a PDF file from base64 input, extract relevant information, and update the state.

        Args:
            state (State): The current state containing base64 PDF data and messages.

        Returns:
            dict: The updated state with extracted text from the PDF.

        Raises:
            GraphException: If an error occurs during PDF processing.
        """
        try:
            print("Async PDF Processor")
            base64_str = state["user_input_data"].split(",")[1]

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_pdf_path = os.path.join(temp_dir, "temp.pdf")
                async with aiofiles.open(temp_pdf_path, "wb") as pdf_file:
                    decoded = base64.b64decode(base64_str)
                    await pdf_file.write(decoded)
                loader = DoclingLoader(file_path=temp_pdf_path)
                markdown_chunks = loader.alazy_load()
                markdown = ""
                async for markdown_chunk in markdown_chunks:
                    markdown += str(markdown_chunk.page_content)

                if markdown:
                    state["user_input_data"] = markdown
                    state["prompt_parts"] = [
                        f"Das folgende hochgeladene PDF-Dokument könnte für die Beantwortung der Frage des Benutzers relevant sein: {state['user_input_data']}.\n\n"
                    ]
                else:
                    state["user_input_data"] = ""

                return state

        except Exception as e:
            print(
                f"An error occurred while running the Graph. Error in Node pdf - Error: {e}"
            )
            raise GraphException


class AsyncTXTProcessor(AsyncProcessor):
    def __init__(self):
        """
        Initialize the AsyncTXTProcessor with a text model client.

        Attributes:
            text_client (AsyncTextModelClient): Client for handling text-based model interactions.
        """
        self.text_client = AsyncTextModelClient()

    async def process(self, state: State) -> dict:
        """
        Process a TXT file from base64 input, extract relevant information, and update the state.

        Args:
            state (State): The current state containing base64 TXT data and messages.

        Returns:
            dict: The updated state with extracted text from the TXT file.

        Raises:
            GraphException: If an error occurs during TXT processing.
        """
        try:
            print("Async TXT Processor")
            base64_str = state["user_input_data"].split(",")[1]
            decoded_bytes = base64.b64decode(base64_str)
            text = decoded_bytes.decode("utf-8")

            if text:
                state["user_input_data"] = text
                state["prompt_parts"] = [
                    f"Die folgende hochgeladene txt-Datei könnte für die Beantwortung der Frage des Benutzers relevant sein: {state['user_input_data']}.\n\n"
                ]
            else:
                state["user_input_data"] = ""

            return state

        except Exception as e:
            print(
                f"An error occurred while running the Graph. Error in Node txt - Error: {e}"
            )
            raise GraphException


class AsyncCSVProcessor(AsyncProcessor):
    def __init__(self):
        """
        Initialize the AsyncCSVProcessor with a text model client.

        Attributes:
            text_client (AsyncTextModelClient): Client for handling text-based model interactions.
        """
        self.text_client = AsyncTextModelClient()

    async def process(self, state: State) -> dict:
        """
        Process a CSV file from base64 input, analyze it with a pandas agent, and update the state.

        Args:
            state (State): The current state containing base64 CSV data and messages.

        Returns:
            dict: The updated state with the agent's response from the CSV analysis.

        Raises:
            GraphException: If an error occurs during CSV processing.
        """
        try:
            print("async CSV Processor")
            base64_str = state["user_input_data"].split(",")[1]
            decoded_bytes = base64.b64decode(base64_str)
            csv = io.StringIO(decoded_bytes.decode("utf-8"))
            value = csv.getvalue()
            if value:
                print("#", value)
                state["user_input_data"] = value
                state["prompt_parts"] = [
                    f"Basierend auf der hochgeladenen csv-Datei sind die folgenden Informationen für die Beantwortung der Frage des Benutzers relevant: {state['user_input_data']}.\n\n"
                ]
            else:
                state["user_input_data"] = ""
            return state

        except Exception as e:
            print(
                f"An error occurred while running the Graph. Error in Node csv - Error: {e}"
            )
            raise GraphException


class AsyncIMAGEProcessor(AsyncProcessor):
    def __init__(self):
        """
        Initialize the AsyncIMAGEProcessor with an image model client.

        Attributes:
            image_client (AsyncImageModelClient): Client for handling image-to-text conversions.
        """
        self.image_client = AsyncImageModelClient()

    async def process(self, state: State) -> dict:
        """
        Process an image from the state and convert it to text, updating the state.

        Args:
            state (State): The current state containing image data.

        Returns:
            dict: The updated state with text extracted from the image.

        Raises:
            GraphException: If an error occurs during image processing.
        """
        try:
            print("async IMAGE Processor")

            base64_str = state["user_input_data"]

            response = await self.image_client.image_to_text(base64_str=base64_str)

            if response:
                state["user_input_data"] = response
                state["prompt_parts"] = [
                    f"Basierend auf dem hochgeladenen Bild sind die folgenden Informationen für die Beantwortung der Frage des Benutzers relevant: {state['user_input_data']}.\n\n"
                ]
            else:
                state["user_input_data"] = ""

            return state

        except Exception as e:
            print(
                f"An error occurred while running the Graph. Error in Node image - Error: {e}"
            )
            raise GraphException
