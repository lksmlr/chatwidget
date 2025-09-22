from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.sparse.sparse_service import calc_sparse_embedding


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/embed")
async def get_sparse_embeddings(request: Request):
    """
    returns {"vectors": [{"indices": [], "values": []}]}
    """
    try:
        data = await request.json()
        texts = data.get("inputs", [])
        vectors = await calc_sparse_embedding(texts)
        response_vectors = [
            {
                "indices": vector.indices,
                "values": vector.values,
            }
            for vector in vectors
        ]

        return JSONResponse(
            content={
                "vectors": response_vectors,
            }
        )
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8500)
