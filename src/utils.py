"""Database utilities for the Music Store Assistant.

Provides a singleton database connection to the Chinook SQLite database.
"""

from pathlib import Path
from functools import lru_cache

from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine


@lru_cache(maxsize=1)
def get_db() -> SQLDatabase:
    """Get the SQLDatabase instance for Chinook.
    
    Uses a file-based SQLite database (Chinook.db) in the project root.
    The connection is cached for reuse across tool invocations.
    
    Returns:
        SQLDatabase: LangChain SQL database wrapper.
        
    Raises:
        FileNotFoundError: If Chinook.db is not found in the project root.
    """
    db_path = Path(__file__).parent.parent / "Chinook.db"
    
    if not db_path.exists():
        raise FileNotFoundError(
            f"Chinook.db not found at {db_path}. "
            "Download it from: https://github.com/lerocha/chinook-database"
        )
    
    engine = create_engine(f"sqlite:///{db_path}")
    return SQLDatabase(engine)


def get_table_names() -> list[str]:
    """Get list of available tables in the database."""
    db = get_db()
    return db.get_usable_table_names()
