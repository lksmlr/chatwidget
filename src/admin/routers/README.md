## Routers (admin/routers)

This folder contains FastAPI route handlers for the admin panel (`admin/`).
Routers expose authenticated HTTP endpoints, render Jinja templates where
needed, and delegate business logic to services.

- **Purpose**: serve admin UI pages and JSON APIs with consistent auth,
  validation, and error handling.
- **Used by**: registered in `admin/app.py` to assemble the web application.

### auth.py
- Authentication endpoints under `/auth`.
- Renders login page, processes login/logout, exposes `/auth/me`.
- Sets/clears cookies via `AuthService` for session management.

### dashboard.py
- Dashboard page at `/dashboard/`.
- Requires an authenticated user; renders `templates/index.html` with context.

### users.py
- Admin-only CRUD for users under `/admin/users`.
- Endpoints: list, create, get, update, delete; change password; get/update bot name.
- Uses `UserService`; responses are API-safe dicts.

### collections.py
- Manage collections under `/admin/collections`.
- Endpoints: list (admin sees all, users see own), create, delete,
  get/update settings, list users of a collection.
- Enforces ownership checks for non-admins; uses `CollectionService`.

### files.py
- File and content operations for collections.
- Endpoints: upload files, list/delete files, view and update chunks, scrape URLs/faculties, job status helpers, and file-chunks HTML view.
- Requires auth and enforces collection access; delegates to `FileService` and `ScraperService`.


