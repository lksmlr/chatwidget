from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()


async def add_bot_name_to_users():
    # Get MongoDB connection string from environment
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("Error: MONGO_URI environment variable not set")
        return

    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongo_uri)
        db = client["admin_panel"]
        users_collection = db["users"]

        # Find all users that don't have bot_name field
        cursor = users_collection.find({"bot_name": {"$exists": False}})
        documents = await cursor.to_list(length=None)

        if not documents:
            print("No users found without bot_name field")
            return

        print(f"Found {len(documents)} users to update")

        # Update each user
        for doc in documents:
            result = await users_collection.update_one(
                {"_id": doc["_id"]}, {"$set": {"bot_name": "Bot Name"}}
            )
            if result.modified_count > 0:
                print(f"Updated user {doc['_id']}: Added bot_name field")
            else:
                print(f"No changes needed for user {doc['_id']}")

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {str(e)}")
    finally:
        # Close the MongoDB connection
        client.close()


if __name__ == "__main__":
    asyncio.run(add_bot_name_to_users())
