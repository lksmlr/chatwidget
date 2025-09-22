from langgraph.graph import START, END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from pymongo import AsyncMongoClient

from src.settings import Settings
from src.widget.app.utils.state import State
from src.widget.app.utils.processors.async_processor_factory import (
    AsyncProcessorFactory,
)


class AsyncGraph:
    def __init__(self):
        self.processor_factory = AsyncProcessorFactory()
        self._settings = Settings()

    async def data_type_condition(self, state: State) -> str:
        data_type_mapping = {
            "pdf": "pdf",
            "txt": "txt",
            "image": "image",
            "csv": "csv",
            "database": "database",
        }

        return data_type_mapping.get(state["user_input_type"])

    async def db_node(self, state: State) -> dict:
        processor = await self.processor_factory.create_processor(user_input_type="db")
        return await processor.process(state)

    async def llm_node(self, state: State) -> dict:
        processor = await self.processor_factory.create_processor(user_input_type="llm")
        return await processor.process(state)

    async def image_node(self, state: State) -> dict:
        processor = await self.processor_factory.create_processor(
            user_input_type="image"
        )
        return await processor.process(state)

    async def pdf_node(self, state: State) -> dict:
        processor = await self.processor_factory.create_processor(user_input_type="pdf")
        return await processor.process(state)

    async def csv_node(self, state: State) -> dict:
        processor = await self.processor_factory.create_processor(user_input_type="csv")
        return await processor.process(state)

    async def txt_node(self, state: State) -> dict:
        processor = await self.processor_factory.create_processor(user_input_type="txt")
        return await processor.process(state)

    async def build_graph(self) -> CompiledStateGraph:
        mongodb_uri = f"mongodb://{self._settings.mongo_username.get_secret_value()}:{self._settings.mongo_password.get_secret_value()}@{self._settings.mongo.url}:{self._settings.mongo.port}/admin"
        mongodb_client = AsyncMongoClient(mongodb_uri)
        checkpointer = AsyncMongoDBSaver(mongodb_client)

        graph_builder = StateGraph(State)

        graph_builder.add_node("image", self.image_node)
        graph_builder.add_node("pdf", self.pdf_node)
        graph_builder.add_node("txt", self.txt_node)
        graph_builder.add_node("csv", self.csv_node)
        graph_builder.add_node("database", self.db_node)
        graph_builder.add_node("llm", self.llm_node)

        graph_builder.add_conditional_edges(
            START,
            self.data_type_condition,
            {
                "image": "image",
                "pdf": "pdf",
                "txt": "txt",
                "csv": "csv",
                "database": "database",
            },
        )

        graph_builder.add_edge("image", "database")
        graph_builder.add_edge("pdf", "database")
        graph_builder.add_edge("txt", "database")
        graph_builder.add_edge("csv", "database")
        graph_builder.add_edge("database", "llm")

        graph_builder.add_edge("llm", END)

        return graph_builder.compile(checkpointer)
