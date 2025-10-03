import sqlite3

def search_all(db_path, search_term):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    results = []

    # Get all table names
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        # Get all columns for this table
        cur.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cur.fetchall()]

        for col in columns:
            try:
                query = f"""
                    SELECT rowid as id, {col} as value 
                    FROM {table}
                    WHERE CAST({col} AS TEXT) LIKE ?
                """
                cur.execute(query, (f"%{search_term}%",))
                for row in cur.fetchall():
                    results.append({
                        "table": table,
                        "column": col,
                        "row_id": row["id"],
                        "matched_value": row["value"]
                    })
            except Exception:
                # Skip unsearchable columns (e.g. blobs)
                continue

    conn.close()
    return results




from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "mydb.sqlite"

#@app.route("/search")
def search():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Missing query parameter ?q="}), 400
    
    results = search_all(DB_PATH, query)
    return jsonify(results)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()

def search_all(search_term):
    """
    Search across all tables and text-convertible columns in the SQLAlchemy db.
    Returns a list of dicts with table, column, row_id, and matched_value.
    """

    results = []
    inspector = inspect(db.engine)

    # Get all table names
    tables = inspector.get_table_names()

    with db.engine.connect() as conn:
        for table in tables:
            # Get all column names
            columns = [col["name"] for col in inspector.get_columns(table)]

            for col in columns:
                try:
                    # Build dynamic SQL (safe because table/col are from inspector)
                    query = text(f"""
                        SELECT rowid as id, {col} as value
                        FROM {table}
                        WHERE CAST({col} AS TEXT) LIKE :term
                    """)

                    rows = conn.execute(query, {"term": f"%{search_term}%"}).fetchall()

                    for row in rows:
                        results.append({
                            "table": table,
                            "column": col,
                            "row_id": row.id,
                            "matched_value": row.value
                        })
                except SQLAlchemyError:
                    # Skip columns that can't be cast/searched
                    continue

    return results
