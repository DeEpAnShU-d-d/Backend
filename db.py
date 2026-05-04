import sqlite3
import os
from datetime import datetime

DB_FILE = 'ecoplate.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            face_encoding TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snacks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cost_in_points INTEGER NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waste_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight_grams REAL NOT NULL,
            image_ref TEXT,
            classified_food TEXT,
            timestamp TEXT NOT NULL,
            student_id TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Seed data if empty
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        students = [
            ("S001", "Alice Smith", 0, 0, None),
            ("S002", "Bob Johnson", 20, 0, None),
            ("S003", "Charlie Brown", 50, 0, None)
        ]
        cursor.executemany("INSERT INTO students (id, name, points, streak, face_encoding) VALUES (?, ?, ?, ?, ?)", students)
        
        snacks = [
            ("SN1", "Apple", 10),
            ("SN2", "Chips", 20),
            ("SN3", "Juice Box", 30),
            ("SN4", "Granola Bar", 15)
        ]
        cursor.executemany("INSERT INTO snacks (id, name, cost_in_points) VALUES (?, ?, ?)", snacks)
        
    conn.commit()
    conn.close()

def add_waste_record(record):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    cursor.execute(
        "INSERT INTO waste_records (weight_grams, image_ref, classified_food, timestamp, student_id) VALUES (?, ?, ?, ?, ?)",
        (
            record['weight_grams'],
            record.get('image_ref'),
            record.get('classified_food'),
            timestamp,
            record.get('student_id')
        )
    )
    
    conn.commit()
    conn.close()

def add_alert(alert_msg):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute("INSERT INTO alerts (message, timestamp) VALUES (?, ?)", (alert_msg, timestamp))
    conn.commit()
    conn.close()
    print(f"[SQLITE] Alert Saved: {alert_msg}")

def get_all_waste():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM waste_records")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_recent_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_student(student_id, name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO students (id, name, points, streak) VALUES (?, ?, 0, 0)", (student_id, name))
        conn.commit()
        return True, "Student created successfully"
    except sqlite3.IntegrityError:
        return False, "Student ID already exists"
    finally:
        conn.close()

def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count > 0, "Student deleted successfully" if count > 0 else "Student not found"

def get_student_by_id(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_snacks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM snacks")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_points_to_student(student_id, points, is_clean_plate=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if is_clean_plate:
        # Increment streak and apply bonus
        cursor.execute("UPDATE students SET streak = streak + 1 WHERE id = ?", (student_id,))
        cursor.execute("SELECT streak FROM students WHERE id = ?", (student_id,))
        streak_row = cursor.fetchone()
        streak = streak_row[0] if streak_row else 0
        
        # Bonus: 5 extra points for every 3 streak levels
        bonus = (streak // 3) * 5
        total_points = points + bonus
        
        cursor.execute("UPDATE students SET points = points + ? WHERE id = ?", (total_points, student_id))
    else:
        # Reset streak if they waste food
        cursor.execute("UPDATE students SET streak = 0 WHERE id = ?", (student_id,))
    
    if cursor.rowcount > 0:
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        student = dict(cursor.fetchone())
        conn.commit()
        conn.close()
        return True, student
    
    conn.close()
    return False, None

def update_student_face_encoding(student_id, encoding_json):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET face_encoding = ? WHERE id = ?", (encoding_json, student_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def award_bonus_points(student_id, weight_grams):
    """
    Awards points based on food waste:
    0-200g: 5 pts
    200-500g: 3 pts
    >500g: 0 pts
    """
    points = 0
    if weight_grams <= 200:
        points = 5
    elif weight_grams <= 500:
        points = 3
    
    if points > 0:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET points = points + ? WHERE id = ?", (points, student_id))
        conn.commit()
        conn.close()
        return True, points
    return False, 0

def redeem_snack(student_id, snack_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student_row = cursor.fetchone()
    cursor.execute("SELECT * FROM snacks WHERE id = ?", (snack_id,))
    snack_row = cursor.fetchone()
    
    if not student_row or not snack_row:
        conn.close()
        return False, "Student or Snack not found"
    
    student = dict(student_row)
    snack = dict(snack_row)
    
    if student['points'] >= snack['cost_in_points']:
        cursor.execute("UPDATE students SET points = points - ? WHERE id = ?", (snack['cost_in_points'], student_id))
        conn.commit()
        # Fetch updated student
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        updated_student = dict(cursor.fetchone())
        conn.close()
        return True, {"student": updated_student, "snack": snack}
    else:
        conn.close()
        return False, "Insufficient points"
