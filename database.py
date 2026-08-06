import sqlite3
import json
from datetime import datetime
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_name TEXT,
            contact_number TEXT,
            email TEXT,
            gender TEXT,
            age TEXT,
            total_experience_years TEXT,
            last_employer TEXT,
            key_skills TEXT,
            current_job_title TEXT,
            original_filename TEXT,
            cv_text TEXT,
            raw_json TEXT,
            status TEXT DEFAULT 'extracted',
            batch_id INTEGER,
            batch_label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        conn.execute("ALTER TABLE candidates ADD COLUMN batch_id INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE candidates ADD COLUMN batch_label TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def create_batch(label: str) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO batches (label, created_at) VALUES (?, ?)",
        (label, datetime.now().isoformat())
    )
    batch_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return batch_id


def get_batches():
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT b.id, b.label, b.created_at, COUNT(c.id) as candidate_count
            FROM batches b
            LEFT JOIN candidates c ON c.batch_id = b.id
            GROUP BY b.id
            ORDER BY b.created_at DESC
        """).fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [dict(row) for row in rows]


def get_latest_batch():
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT b.id, b.label, b.created_at, COUNT(c.id) as candidate_count
            FROM batches b
            LEFT JOIN candidates c ON c.batch_id = b.id
            GROUP BY b.id
            ORDER BY b.created_at DESC
            LIMIT 1
        """).fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    return dict(row) if row else None


def insert_candidate(data: dict, filename: str, cv_text: str, batch_id: int = None, batch_label: str = None) -> int:
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO candidates 
        (candidate_name, contact_number, email, gender, age, 
         total_experience_years, last_employer, key_skills, current_job_title,
         original_filename, cv_text, raw_json, status, batch_id, batch_label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("candidate_name"),
        data.get("contact_number"),
        data.get("email"),
        data.get("gender"),
        data.get("age"),
        data.get("total_experience_years"),
        data.get("last_employer"),
        data.get("key_skills"),
        data.get("current_job_title"),
        filename,
        cv_text,
        json.dumps(data),
        "extracted",
        batch_id,
        batch_label
    ))
    candidate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return candidate_id


def get_candidates_by_batch(batch_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM candidates WHERE batch_id = ? ORDER BY created_at DESC",
        (batch_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_candidates(search: str = None, status: str = None):
    conn = get_connection()
    query = "SELECT * FROM candidates WHERE 1=1"
    params = []

    if search:
        query += """ AND (candidate_name LIKE ? OR email LIKE ? 
                    OR key_skills LIKE ? OR current_job_title LIKE ?
                    OR last_employer LIKE ? OR contact_number LIKE ?)"""
        search_param = f"%{search}%"
        params.extend([search_param] * 6)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_candidate_by_id(candidate_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_candidate(candidate_id: int, data: dict) -> bool:
    conn = get_connection()
    conn.execute("""
        UPDATE candidates SET
            candidate_name = ?,
            contact_number = ?,
            email = ?,
            gender = ?,
            age = ?,
            total_experience_years = ?,
            last_employer = ?,
            key_skills = ?,
            current_job_title = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        data.get("candidate_name"),
        data.get("contact_number"),
        data.get("email"),
        data.get("gender"),
        data.get("age"),
        data.get("total_experience_years"),
        data.get("last_employer"),
        data.get("key_skills"),
        data.get("current_job_title"),
        data.get("status", "extracted"),
        datetime.now().isoformat(),
        candidate_id
    ))
    conn.commit()
    changes = conn.total_changes
    conn.close()
    return changes > 0


def delete_candidate(candidate_id: int) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
    conn.commit()
    changes = conn.total_changes
    conn.close()
    return changes > 0


def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM candidates").fetchone()["cnt"]
    extracted = conn.execute("SELECT COUNT(*) as cnt FROM candidates WHERE status='extracted'").fetchone()["cnt"]
    reviewed = conn.execute("SELECT COUNT(*) as cnt FROM candidates WHERE status='reviewed'").fetchone()["cnt"]
    conn.close()
    return {"total": total, "extracted": extracted, "reviewed": reviewed}
