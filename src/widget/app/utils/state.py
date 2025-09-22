from langgraph.graph.message import add_messages
from typing import Annotated, Union
from typing_extensions import TypedDict


def add_prompt_parts(
    current_list: list[str], new_value: Union[list[str], None]
) -> list[str]:
    if new_value is None:
        return []
    return current_list + new_value


class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_input_type: str = "empty"
    user_input_data: str = ""
    vector_db_data: str = ""
    collection_name: str = ""
    prompt_parts: Annotated[list[str], add_prompt_parts]
