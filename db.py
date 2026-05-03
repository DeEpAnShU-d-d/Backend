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
            streak INTEGER DEFAULT 0
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
            timestamp TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Seed only necessary structural data (Snacks) if empty
    # We keep Students empty so you can add real ones or login with real IDs
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        # Adding some default student placeholders so the login doesn't fail for the demo
        students = [
            ("S001", "Student One", 0, 0),
            ("S002", "Student Two", 0, 0),
            ("S003", "Student Three", 0, 0)
        ]
        cursor.executemany("INSERT INTO students (id, name, points, streak) VALUES (?, ?, ?, ?)", students)
        
    cursor.execute("SELECT COUNT(*) FROM snacks")
    if cursor.fetchone()[0] == 0:
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
        "INSERT INTO waste_records (weight_grams, image_ref, classified_food, timestamp) VALUES (?, ?, ?, ?)",
        (record['weight_grams'], record.get('image_ref'), record.get('classified_food'), timestamp)
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
        cursor.execute("UPDATE students SET streak = streak + 1 WHERE id = ?", (student_id,))
        cursor.execute("SELECT streak FROM students WHERE id = ?", (student_id,))
        streak_row = cursor.fetchone()
        streak = streak_row[0] if streak_row else 0
        bonus = (streak // 3) * 5
        total_points = points + bonus
        cursor.execute("UPDATE students SET points = points + ? WHERE id = ?", (total_points, student_id))
    else:
        cursor.execute("UPDATE students SET streak = 0 WHERE id = ?", (student_id,))
    
    if cursor.rowcount > 0:
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        student = dict(cursor.fetchone())
        conn.commit()
        conn.close()
        return True, student
    
    conn.close()
    return False, None

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
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        updated_student = dict(cursor.fetchone())
        conn.close()
        return True, {"student": updated_student, "snack": snack}
    else:
        conn.close()
        return False, "Insufficient points"
