## Scripts (admin/scrips)

Maintenance/migration utilities for the admin panel data. These are one-off
scripts and are not loaded by the FastAPI app.

### Prerequisites
- MongoDB access and credentials.
- Environment config:
  - `update_collection_passwords.py` reads from `src/local.env` via `Settings`.
  - Other scripts expect `MONGO_URI` in your environment (can use `.env`).

### Scripts
- **rename_bot_name_to_data_source.py**: Renames `bot_name` field to
  `data_source_name` in the `collections` collection and unsets the old field.
- **add_bot_name_to_users.py**: Adds a default `bot_name` to users missing the
  field in the `users` collection.

### Run
```bash
python src/admin/scrips/<script_name>.py
```


