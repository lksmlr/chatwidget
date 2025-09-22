from src.widget.app.utils.processors.async_processors import (
    AsyncProcessor,
    AsyncTXTProcessor,
    AsyncIMAGEProcessor,
    AsyncCSVProcessor,
    AsyncPDFProcessor,
    AsyncDBProcessor,
    AsyncLLMProcessor,
)


class AsyncProcessorFactory:
    @staticmethod
    async def create_processor(user_input_type: str) -> AsyncProcessor:
        """
        Create an appropriate AsyncProcessor instance based on the user input type.

        Args:
            user_input_type (str): The type of user input (e.g., 'pdf', 'txt', 'image', 'csv', 'db', 'llm').

        Returns:
            AsyncProcessor: An instance of the corresponding processor class.

        Raises:
            KeyError: If the user_input_type is not recognized, processors.get() will return None, which may lead to an error if not handled by the caller.
        """
        processors = {
            "pdf": AsyncPDFProcessor,
            "txt": AsyncTXTProcessor,
            "image": AsyncIMAGEProcessor,
            "csv": AsyncCSVProcessor,
            "db": AsyncDBProcessor,
            "llm": AsyncLLMProcessor,
        }

        return processors.get(user_input_type)()
