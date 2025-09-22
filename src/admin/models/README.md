## Models (admin/models)

This folder defines lightweight data models for the admin panel (`admin/`).
They encapsulate the admin domain entities and provide safe, consistent
conversion to/from MongoDB records and API-friendly JSON.

- **Purpose**: centralize schemas, enforce basic invariants, and standardize
  serialization across routers and services.
- **Used by**: `admin/routers/*` and `admin/services/*` when reading/writing
  database documents and returning API responses.

### collection.py
- **`Collection` dataclass** representing a content collection (formerly
  “institution” data set) owned by a user.
- Auto-generates `collection_name` in `__post_init__` when not provided.
- `to_dict()`: prepares a Mongo-ready document; converts `owner_id` to
  `ObjectId` and preserves `_id` when present.
- `to_json()`: returns an API-safe payload (string ids, ISO timestamps).
- `from_dict()`: builds a `Collection` from a MongoDB record.

### user.py
- **`User` dataclass** representing an admin/institution user.
- Includes password utilities via Passlib (`hash_password`, `verify_password`).
- Role helpers: `is_admin()` and `is_institution()`.
- `to_dict()`/`to_json()`: API payload (string `_id`, ISO timestamps).
- `from_dict()`: builds a `User` from a MongoDB record.

Note: Passwords are stored hashed; never store or log plain-text passwords.

