import os
from os import getenv
from typing import Optional

from pydantic_settings import BaseSettings


class DbSettings(BaseSettings):
    """Database settings that can be set using environment variables.

    Reference: https://docs.pydantic.dev/latest/usage/pydantic_settings/
    """

    # Database configuration
    # postgresql_path: str = os.getenv("POSTGRESQL_PATH", "C:/Users/UTKARSH/PostgreSQL_16/16")
    # db_host: str = "localhost"  # Changed from Optional[str]
    # db_port: int = 5433        # Changed from Optional[int]
    # db_user: str = "postgres"   # Changed from Optional[str]
    # db_pass: str = "123456"  # Changed from Optional[str]
    # db_database: str = "mydb"   # Changed from Optional[str]
    # db_driver: str = "postgresql+psycopg"
    # migrate_db: bool = False
    
    # for aws rds
    db_host: str = "mydb.c89466wkiwuk.us-east-1.rds.amazonaws.com"
    db_port: int = 5432
    db_user: str = "postgres"      
    db_pass: str = "q0PgMNmwYsOfzx9moXFl"      # the password you set
    db_database: str = "mydb"               
    db_driver: str = "postgresql+psycopg"
    migrate_db: bool = False

    def get_db_url(self) -> str:
        db_url = "{}://{}{}@{}:{}/{}".format(
            self.db_driver,
            self.db_user,
            f":{self.db_pass}" if self.db_pass else "",
            self.db_host,
            self.db_port,
            self.db_database,
        )
        # Use local database if RUNTIME_ENV is not set
        if "None" in db_url and getenv("RUNTIME_ENV") is None:
            from workspace.dev_resources import dev_db

            # logger.debug("Using local connection")
            local_db_url = dev_db.get_db_connection_local()
            if local_db_url:
                db_url = local_db_url

        # Validate database connection
        if "None" in db_url or db_url is None:
            raise ValueError("Could not build database connection")
        return db_url


# Create DbSettings object
db_settings = DbSettings()
