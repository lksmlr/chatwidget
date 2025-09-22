from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.dense.dense_service import get_tokenize_count, calc_dense_embeddings


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/embed")
async def get_dense_embeddings(request: Request):
    try:
        data = await request.json()
        texts = data.get("inputs", "")

        vectors = await calc_dense_embeddings(texts)

        return JSONResponse(
            content={
                "vectors": vectors,
            }
        )
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/tokenize")
async def tokenize(request: Request):
    try:
        data = await request.json()
        texts = data.get("inputs", "")

        counts = await get_tokenize_count(texts)

        return JSONResponse(
            content={
                "counts": counts,
            }
        )
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8400)
