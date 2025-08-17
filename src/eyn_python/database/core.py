from __future__ import annotations

import sqlite3
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import shutil

from eyn_python.logging import get_logger

log = get_logger(__name__)


class DatabaseManager:
    """SQLite database manager with utility functions."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def connect(self) -> None:
        """Connect to the database."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        
    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query."""
        if not self.connection:
            self.connect()
        if self.connection is None:
            raise RuntimeError("Database connection failed")
        return self.connection.execute(query, params)
        
    def commit(self) -> None:
        """Commit changes."""
        if self.connection:
            self.connection.commit()
            
    def rollback(self) -> None:
        """Rollback changes."""
        if self.connection:
            self.connection.rollback()
            
    def get_tables(self) -> List[str]:
        """Get list of tables."""
        cursor = self.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
        
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information."""
        cursor = self.execute(f"PRAGMA table_info({table_name})")
        return [dict(row) for row in cursor.fetchall()]
        
    def backup(self, backup_path: Union[str, Path]) -> None:
        """Create a backup of the database."""
        backup_path = Path(backup_path)
        shutil.copy2(self.db_path, backup_path)
        
    def optimize(self) -> None:
        """Optimize the database."""
        self.execute("VACUUM")
        self.execute("ANALYZE")
        self.commit()
        
    def export_table_to_csv(self, table_name: str, csv_path: Union[str, Path]) -> None:
        """Export a table to CSV."""
        csv_path = Path(csv_path)
        cursor = self.execute(f"SELECT * FROM {table_name}")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([description[0] for description in cursor.description])
            writer.writerows(cursor.fetchall())
            
    def import_csv_to_table(self, csv_path: Union[str, Path], table_name: str, 
                           create_table: bool = True) -> None:
        """Import CSV data into a table."""
        csv_path = Path(csv_path)
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            if create_table:
                columns = ', '.join([f'"{col}" TEXT' for col in headers])
                self.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
                
            placeholders = ', '.join(['?' for _ in headers])
            insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
            
            for row in reader:
                self.execute(insert_query, tuple(row))
                
        self.commit()


def create_database(db_path: Union[str, Path]) -> DatabaseManager:
    """Create a new SQLite database."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    manager = DatabaseManager(db_path)
    manager.connect()
    return manager


def execute_query(db_path: Union[str, Path], query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a query and return results."""
    with DatabaseManager(db_path) as db:
        cursor = db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def execute_script(db_path: Union[str, Path], script_path: Union[str, Path]) -> None:
    """Execute a SQL script file."""
    script_path = Path(script_path)
    with DatabaseManager(db_path) as db:
        with open(script_path, 'r', encoding='utf-8') as f:
            if db.connection is None:
                raise RuntimeError("Database connection failed")
            db.connection.executescript(f.read())
        db.commit()


def backup_database(db_path: Union[str, Path], backup_path: Union[str, Path]) -> None:
    """Create a backup of a database."""
    with DatabaseManager(db_path) as db:
        db.backup(backup_path)


def optimize_database(db_path: Union[str, Path]) -> None:
    """Optimize a database."""
    with DatabaseManager(db_path) as db:
        db.optimize()


def get_table_info(db_path: Union[str, Path], table_name: str) -> List[Dict[str, Any]]:
    """Get table schema information."""
    with DatabaseManager(db_path) as db:
        return db.get_table_info(table_name)


def list_tables(db_path: Union[str, Path]) -> List[str]:
    """List all tables in a database."""
    with DatabaseManager(db_path) as db:
        return db.get_tables()


def export_to_csv(db_path: Union[str, Path], table_name: str, csv_path: Union[str, Path]) -> None:
    """Export a table to CSV."""
    with DatabaseManager(db_path) as db:
        db.export_table_to_csv(table_name, csv_path)


def import_from_csv(db_path: Union[str, Path], csv_path: Union[str, Path], 
                   table_name: str, create_table: bool = True) -> None:
    """Import CSV data into a table."""
    with DatabaseManager(db_path) as db:
        db.import_csv_to_table(csv_path, table_name, create_table)
