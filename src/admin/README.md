# Admin Panel Startup Instructions

This guide will help you set up and run the admin panel on your local machine.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Network Requirements

**Important**: To connect to the database, vector store, and other services, you need to be connected to **VPN**.

## Setup Instructions

### 1. Create and Activate Virtual Environment

```bash
# Navigate to the project root directory
cd /path/to/kiwi-ki-chatbot-widget

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install all required packages
pip install -r requirements/requirements.txt
```

### 3. Environment Configuration

Create a `local.env` file in the `src/` directory with the following configuration:

```bash
# Create the environment file
touch src/local.env
```

Add the following content to `src/local.env`:

```env
# Database Configuration
QDRANT__URL="http://kit.informatik.fh-nuernberg.de"
QDRANT__PORT="6333"
QDRANT_KEY=your_qdrant_key
MONGO__URL="kit.informatik.fh-nuernberg.de"
MONGO__PORT="27017"
MONGO_PASSWORD=your_mongo_password
MONGO_USERNAME=your_mongo_username

# Ingest Service 
INGEST__URL="http://kit.informatik.fh-nuernberg.de"
INGEST__PORT="8900"

# LLM Configuration
LLM__URL="http://kit.informatik.fh-nuernberg.de:8001/v1"
LLM__NAME="/models/mistral-small-fp8"

# Embedding Services
SPARSE__URL="http://kit.informatik.fh-nuernberg.de"
SPARSE__PORT="8500"
DENSE__URL="http://kit.informatik.fh-nuernberg.de"
DENSE__PORT="8400"

# Embedding Configuration
EMBEDDING_DIMENSION=1024
EMBEDDING_WINDOW=8192

# Admin Panel Security 
ADMIN_PASSWORD=your_secure_admin_password
SECRET_KEY=your_secret_key_for_jwt_tokens
```

*Ensure to fill `your_mongo_password`, `your_mongo_username`, `your_secure_admin_password`, and `your_secret_key_for_jwt_tokens` with the correct variables.*

### 4. Database Setup

Initialize the database with the admin user:

```bash
# Run the database initialization script (uses admin password from local.env)
python src/admin/init_db.py

# Or override with a custom password
python src/admin/init_db.py --admin-password your_custom_password
```

### 5. Start the Admin Panel

#### Option 1: Using Python directly

```bash
# Navigate to the project root
cd /path/to/kiwi-ki-chatbot-widget

# Run the admin panel
python -m src.admin.app
```

#### Option 2: Using uvicorn directly

```bash
# Navigate to the project root
cd /path/to/kiwi-ki-chatbot-widget

# Start with uvicorn
uvicorn src.admin.app:app --host 0.0.0.0 --port 9000 --reload
```

#### Option 3: Using uvicorn with custom configuration

```bash
# For development with auto-reload
uvicorn src.admin.app:app --host 127.0.0.1 --port 9000 --reload --log-level debug

# For production-like environment
uvicorn src.admin.app:app --host 0.0.0.0 --port 9000 --workers 1
```

## Accessing the Admin Panel

Once the server is running, you can access the admin panel at:

- **URL**: http://localhost:9000
- **Login Page**: http://localhost:9000/auth/login

The application will automatically redirect you to the login page when you visit the root URL.

## Default Admin Credentials

The system will create a default admin user during initialization:
- **Username**: `admin`
- **Password**: Uses the `ADMIN_PASSWORD` value from your `local.env` file

If no admin password is set in the environment configuration, the initialization will fail with an error message.

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using port 9000
   lsof -i :9000
   
   # Kill the process if needed
   kill -9 <PID>
   
   # Or use a different port
   uvicorn src.admin.app:app --host 0.0.0.0 --port 9001 --reload
   ```

2. **Module Import Errors**
   - Ensure you're running from the project root directory
   - Verify virtual environment is activated
   - Check that all dependencies are installed

3. **Connection Issues**
   - Verify your VPN connection 
   - Try accessing the services directly in your browser.

### Logs and Debugging

The application uses Python's logging module. To see detailed logs:

```bash
# Run with debug logging
uvicorn src.admin.app:app --host 0.0.0.0 --port 9000 --reload --log-level debug
```

### Environment Variables

If you prefer using environment variables instead of the `local.env` file, you can export them:

```bash
export MONGO__URL=mongodb://localhost
export MONGO__PORT=27017
export ADMIN_PASSWORD=your_secure_password
# ... etc
```

## Development Mode

For development, use the reload option to automatically restart the server when code changes:

```bash
uvicorn src.admin.app:app --host 127.0.0.1 --port 9000 --reload
```

## File Structure

The admin panel expects the following directory structure:

```
src/admin/
├── app.py             # Main FastAPI application
├── database.py        # Database configuration
├── init_db.py         # Database initialization
├── user_manual.p.md   # A user manual for interacting with the ap-frontend.
├── static/            # Static files (CSS, JS, images)
├── templates/         # Jinja2 templates
├── routers/           # API route handlers
├── services/          # Business logic services
├── models/            # Data models
└── utils/             # Utility functions
```

## Support

If you encounter issues:

1. Check the logs for error messages
2. Verify all dependencies are installed
3. Ensure the environment configuration is correct
4. Check that all required services (MongoDB, etc.) are running

For additional help, refer to the project documentation. 