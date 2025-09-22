## Services (admin/services)

Core business logic for the admin panel (`admin/`). Services encapsulate
operations against the database and external services (vector/ingest), keeping
routers thin and focused on HTTP concerns.

- **Purpose**: implement domain workflows, validation, and cross-service calls.
- **Used by**: `admin/routers/*` for all non-trivial operations.

### auth_service.py
- Handles authentication/authorization for the admin frontend.
- Verifies users from session cookies, authenticates credentials, creates JWT,
  and sets/clears auth cookies.

### collection_service.py
- Manages collection lifecycle: list (admin vs owner), get, create, update,
  delete.
- On create: stores in MongoDB and creates a Qdrant collection via
  `AsyncVectorClient`.
- On delete: removes Qdrant collection and DB records (and related users).

### file_service.py
- File and chunk operations for collections.
- Uploads and ingests `.pdf`, `.txt`, `.csv` files via `insert_document`.
- Lists files by aggregating points, fetches chunks for a file, updates chunk
  text, and deletes all chunks for a file via `AsyncVectorClient`.

### scraper_service.py
- URL/faculty scraping integration through the ingest service.
- Creates background scrape jobs, reports job status, and resolves the active
  job for a collection.

### user_service.py
- User management: list non-admin users, get, create (bcrypt), update, delete
  (including owned collections), change password, and get/update `bot_name`.


