#!/usr/bin/env python3
from database import Database
from models.user import User
from flask_bcrypt import Bcrypt
from src.settings import Settings
import argparse
import logging

logger = logging.getLogger(__name__)


def initialize_database(admin_password=None):
    """Initialize the database and create admin user if it doesn't exist."""
    # Using the singleton instance
    db = Database()
    bcrypt = Bcrypt()

    # Load settings to get default admin password
    settings = Settings()

    # Check if admin user exists
    admin_user = db.get_user("admin")

    if not admin_user:
        # Use provided password, or fall back to settings default, or prompt for one
        if not admin_password:
            if settings.admin_password:
                admin_password = settings.admin_password.get_secret_value()
            else:
                logger.error("No admin password provided and none found in settings.")
                return False

        # Create admin user
        hashed_password = bcrypt.generate_password_hash(admin_password).decode("utf-8")
        user = User(
            id="admin",
            username="admin",
            password=hashed_password,
            role="admin",
        )
        db.create_user(user.to_dict())
        logger.info("Admin user created successfully.")

    else:
        logger.info("Admin user already exists.")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize the database and create admin user if needed."
    )
    parser.add_argument(
        "--admin-password",
        help="Password for the admin user (overrides default from settings)",
    )
    args = parser.parse_args()

    success = initialize_database(args.admin_password)
    if success:
        logger.info("Database initialization completed successfully.")
    else:
        logger.error("Database initialization failed.")
        exit(1)
