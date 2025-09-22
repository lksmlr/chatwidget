from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()


async def rename_bot_name_to_data_source():
    # Get MongoDB connection string from environment
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("Error: MONGO_URI environment variable not set")
        return

    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongo_uri)
        db = client["admin_panel"]
        collections_collection = db["collections"]

        # Find all documents that have bot_name field
        cursor = collections_collection.find({"bot_name": {"$exists": True}})
        documents = await cursor.to_list(length=None)

        if not documents:
            print("No collections found with bot_name field")
            return

        print(f"Found {len(documents)} collections to update")

        # Update each document
        for doc in documents:
            bot_name = doc.get("bot_name")
            if bot_name:
                # Add new field and remove old one
                result = await collections_collection.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {"data_source_name": bot_name},
                        "$unset": {"bot_name": ""},
                    },
                )
                if result.modified_count > 0:
                    print(
                        f"Updated collection {doc['_id']}: {bot_name} -> data_source_name"
                    )
                else:
                    print(f"No changes needed for collection {doc['_id']}")

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {str(e)}")
    finally:
        # Close the MongoDB connection
        client.close()


if __name__ == "__main__":
    asyncio.run(rename_bot_name_to_data_source())
