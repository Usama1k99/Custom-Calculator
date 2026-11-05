"""
SQLite session-wise calculation history database manager.
Zero external dependencies; utilizes Python standard library sqlite3.
"""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import List, Dict, Any, Optional
import uuid


class HistoryDB:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path("data")
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "history.db")
        else:
            p = Path(db_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(p)

        self._active_session_id: Optional[str] = None
        self._mem_conn: Optional[sqlite3.Connection] = None
        self._init_database()
        self._ensure_active_session()

    @contextmanager
    def _get_connection(self):
        if self.db_path == ":memory:":
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:")
                self._mem_conn.row_factory = sqlite3.Row
            yield self._mem_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def close(self):
        if self._mem_conn is not None:
            self._mem_conn.close()
            self._mem_conn = None

    def _init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    session_name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    closed_at TIMESTAMP
                )
            """)
            # Calculations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calculations (
                    calc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    expression TEXT NOT NULL,
                    result TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
                )
            """)
            # Index for fast search
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_calc_session ON calculations(session_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_calc_timestamp ON calculations(timestamp DESC);
            """)
            conn.commit()

    def _ensure_active_session(self):
        """
        Loads the most recent active session or creates a fresh one.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE closed_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                self._active_session_id = row["session_id"]
            else:
                self.create_new_session("Active Session")

    def create_new_session(self, name: Optional[str] = None) -> str:
        """
        Closes any existing session and starts a new one.
        """
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        if not name:
            name = f"Session {now.strftime('%b %d, %H:%M')}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Close previous active session if any
            if self._active_session_id:
                cursor.execute("""
                    UPDATE sessions SET closed_at = ? WHERE session_id = ?
                """, (now.isoformat(), self._active_session_id))

            # Create new session
            cursor.execute("""
                INSERT INTO sessions (session_id, session_name, created_at)
                VALUES (?, ?, ?)
            """, (session_id, name, now.isoformat()))
            conn.commit()

        self._active_session_id = session_id
        return session_id

    @property
    def active_session_id(self) -> str:
        if not self._active_session_id:
            self._ensure_active_session()
        return self._active_session_id or ""

    def add_calculation(self, expression: str, result: str, mode: str = "Standard", notes: str = "") -> int:
        """
        Records a calculation under the current active session.
        """
        session_id = self.active_session_id
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calculations (session_id, mode, expression, result, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, mode, expression, result, now, notes))
            conn.commit()
            return cursor.lastrowid or 0

    def get_grouped_history(self) -> List[Dict[str, Any]]:
        """
        Returns all sessions with their respective calculations grouped chronologically.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions ORDER BY created_at DESC
            """)
            session_rows = cursor.fetchall()
            results = []

            for s_row in session_rows:
                s_id = s_row["session_id"]
                cursor.execute("""
                    SELECT * FROM calculations
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                """, (s_id,))
                calc_rows = cursor.fetchall()

                results.append({
                    "session_id": s_id,
                    "session_name": s_row["session_name"],
                    "created_at": s_row["created_at"],
                    "is_active": s_id == self._active_session_id,
                    "calculations": [
                        {
                            "calc_id": c["calc_id"],
                            "mode": c["mode"],
                            "expression": c["expression"],
                            "result": c["result"],
                            "timestamp": c["timestamp"],
                            "notes": c["notes"]
                        }
                        for c in calc_rows
                    ]
                })

            return results

    def search_calculations(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches calculations by expression, result, or mode.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute("""
                SELECT c.*, s.session_name
                FROM calculations c
                JOIN sessions s ON c.session_id = s.session_id
                WHERE c.expression LIKE ? OR c.result LIKE ? OR c.mode LIKE ?
                ORDER BY c.timestamp DESC
            """, (pattern, pattern, pattern))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_all(self):
        """
        Clears all history and restarts a clean session.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM calculations")
            cursor.execute("DELETE FROM sessions")
            conn.commit()
        self.create_new_session("Active Session")
