import asyncio
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
from typing import Union


_tokenizer = AutoTokenizer.from_pretrained(pretrained_model_name_or_path=r"/model")
_model = SentenceTransformer(model_name_or_path=r"/model", trust_remote_code=True)


async def calc_dense_embeddings(
    texts: Union[list[str], str],
) -> Union[list[list[float]], list[float]]:
    embeddings = await asyncio.to_thread(_model.encode, sentences=texts, batch_size=10)

    return embeddings.tolist()


async def get_tokenize_count(texts: Union[list[str], str]) -> Union[list[int], int]:
    if isinstance(texts, str):
        token_ids: list[int] = (await asyncio.to_thread(_tokenizer, texts))["input_ids"]
        counts: int = len(token_ids)

    else:
        token_ids: list[list[int]] = (await asyncio.to_thread(_tokenizer, texts))[
            "input_ids"
        ]
        counts: list[int] = [len(ids) for ids in token_ids]

    return counts
