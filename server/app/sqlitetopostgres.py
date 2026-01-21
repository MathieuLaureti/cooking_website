import sqlite3
import psycopg
import json
from app.database import get_db
from app.db_models.models import MatchChecker
# Connect to both
db_gen = get_db()

# 2. Advance to the 'yield' (This opens the Postgres connection)
db = next(db_gen)

try:
    # --- YOUR MIGRATION LOGIC ---
    sqlite_conn = sqlite3.connect('db.sqlite3')
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT title, avoid, afinities, matchs FROM api_ingredient")
    
    for row in cursor.fetchall():
        # Using the 'db' session we got from the generator
        new_item = MatchChecker(
            title=row[0],
            avoid=json.loads(row[1]),
            affinities=json.loads(row[2]),
            matches=json.loads(row[3])
        )
        db.add(new_item)
    
    db.commit() # Save all 700 rows
    print("Migration successful!")

finally:
    # 3. Resume the generator to hit the 'db.close()' in the 'finally' block
    try:
        next(db_gen)
    except StopIteration:
        # This is the expected behavior when a generator finishes
        pass
    sqlite_conn.close()