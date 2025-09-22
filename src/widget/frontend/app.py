import sys
import os
from contextlib import asynccontextmanager

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from src.widget.app.async_graph import AsyncGraph
from bson import ObjectId


from src.clients.async_database_client import AsyncDatabaseClient

# Global variables
GRAPH = None
DB_CLIENT = None


# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    global GRAPH, DB_CLIENT
    GRAPH = await AsyncGraph().build_graph()
    DB_CLIENT = AsyncDatabaseClient()
    await DB_CLIENT.get_client()

    yield

    if DB_CLIENT is not None:
        await AsyncDatabaseClient.close_client()


# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="src/widget/frontend/static"), name="static")
templates = Jinja2Templates(directory="src/widget/frontend/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.hostname)
    port = request.headers.get("x-forwarded-port", None)

    if port and (
        (proto == "http" and port != "80") or (proto == "https" and port != "443")
    ):
        base_url = f"{proto}://{host}:{port}"
    else:
        base_url = f"{proto}://{host}"

    return templates.TemplateResponse(
        "index.html", {"request": request, "base_url": base_url}
    )


@app.post("/generate_answer")
async def generate_answer(request: Request):
    try:
        global GRAPH
        type_prefixes = {
            "data:image": "image",
            "data:text/csv": "csv",
            "data:text/plain": "txt",
            "data:application/pdf": "pdf",
        }

        data = await request.json()
        user_message = data.get("message", "")
        user_input_data = data.get("data", "")
        collection = data.get("collection", "")
        thread_id = data.get("thread_id")

        config = {"configurable": {"thread_id": thread_id}}

        if user_input_data == "":
            user_input_type = "database"
        else:
            for prefix, user_input_type in type_prefixes.items():
                if user_input_data.startswith(prefix):
                    break

        answer = await GRAPH.ainvoke(
            {
                "messages": user_message,
                "user_input_type": user_input_type,
                "user_input_data": user_input_data,
                "collection_name": collection,
            },
            config,
        )

        return JSONResponse(
            content={"answer": answer["messages"][-1].content}, status_code=200
        )

    except Exception as e:
        print(e)
        return JSONResponse(
            content={
                "answer": "An error occurred while processing your request.",
                "error": str(e),
            },
            status_code=500,
        )


@app.get("/get_collections")
async def get_collections():
    try:
        global DB_CLIENT
        institutions_collection = await DB_CLIENT.get_collection(
            database_name="admin_panel", collection_name="collections"
        )
        institutions = institutions_collection.find()

        # Get bot name from users collection
        users_collection = await DB_CLIENT.get_collection(
            database_name="admin_panel", collection_name="users"
        )
        users = users_collection.find()

        bot_names = {}
        async for user in users:
            if "bot_name" in user:
                bot_names[str(user["_id"])] = user["bot_name"]

        modified_institutions = []

        async for inst in institutions:
            inst["_id"] = str(inst["_id"])
            if "owner_id" in inst and isinstance(inst["owner_id"], ObjectId):
                inst["owner_id"] = str(inst["owner_id"])
                try:
                    inst["bot_name"] = bot_names[str(inst["owner_id"])]
                except KeyError:
                    continue
                inst.pop("owner_id", None)
            inst.pop("created_at", None)
            inst.pop("password", None)
            modified_institutions.append(inst)

        return JSONResponse(content=modified_institutions)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/get_users")
async def get_users():
    try:
        global DB_CLIENT
        institutions_users = await DB_CLIENT.get_collection(
            database_name="admin_panel", collection_name="users"
        )
        users = list(institutions_users.find())

        for user in users:
            user["_id"] = str(user["_id"])
            user.pop("password", None)
            user.pop("role", None)
            user.pop("created_at", None)

        return JSONResponse(content=users)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/process_key")
async def process_key(request: Request):
    try:
        global DB_CLIENT
        data = await request.json()
        received_key = data.get("key", "")
        print(f"Received Key: {received_key}")

        institutions_collection = await DB_CLIENT.get_collection(
            database_name="admin_panel", collection_name="collections"
        )
        institutions = institutions_collection.find()

        async for inst in institutions:
            if inst["password"] is not None:
                check_key = inst["password"]
                if received_key.encode("utf-8") == check_key.encode("utf-8"):
                    return JSONResponse(
                        content={
                            "answer": "collection found",
                            "collection_name": inst["collection_name"],
                            "welcome_message": inst["welcome_message"],
                            "data_source_name": inst["data_source_name"],
                        },
                        status_code=200,
                    )

        return JSONResponse(
            content={"answer": "no collection with this key"}, status_code=200
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/delete_chat")
async def delete_chat(request: Request):
    try:
        global DB_CLIENT
        data = await request.json()
        thread_id = data.get("thread_id")

        await DB_CLIENT.delete(thread_id=thread_id)

        return JSONResponse(content={"success": True}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/get_chat_history")
async def get_chat_history(thread_id: str):
    global DB_CLIENT
    try:
        messages = await DB_CLIENT.get_latest_checkpoint(thread_id=thread_id)
        return JSONResponse(content={"messages": messages}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9090)
