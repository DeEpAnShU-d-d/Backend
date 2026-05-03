from flask import Flask, request, jsonify
from flask_cors import CORS
from db import init_db, add_waste_record, get_all_waste, get_recent_alerts, get_students, get_snacks, add_points_to_student, redeem_snack, get_student_by_id
from ai_engine import classify_image, generate_recommendations
from alert_engine import check_threshold

app = Flask(__name__)
CORS(app) # Enable CORS for frontend

init_db()

@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """
    Endpoint for ESP32 to send data.
    Expected JSON: {"weight_grams": float, "image_ref": string}
    """
    data = request.json
    weight = data.get('weight_grams')
    image_ref = data.get('image_ref')
    
    if weight is None:
        return jsonify({"error": "Missing weight_grams"}), 400
        
    # 1. AI Image Classification
    classified_food = classify_image(image_ref)
    
    record = {
        "weight_grams": weight,
        "image_ref": image_ref,
        "classified_food": classified_food
    }
    
    # 2. Store to "Firebase" (Mocked)
    add_waste_record(record)
    
    # 2.5 Reward System Check
    # If the plate is virtually empty (weight < 10g), reward 10 points
    student_id = data.get('student_id')
    reward_awarded = False
    if student_id:
        if weight < 10:
            success, _ = add_points_to_student(student_id, 10, is_clean_plate=True)
            if success:
                reward_awarded = True
        else:
            # Reset streak if weight is significant
            add_points_to_student(student_id, 0, is_clean_plate=False)
    
    # 3. Check Alerts
    all_records = get_all_waste()
    # Mocking shift window by taking last 20 records
    recent_records = all_records[-20:]
    check_threshold(recent_records)
    
    return jsonify({
        "status": "success", 
        "record": record,
        "reward_awarded": reward_awarded
    }), 201

@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """
    Endpoint for React Frontend to consume.
    """
    all_records = get_all_waste()
    recent_alerts = get_recent_alerts()
    
    # 4. Gen-AI Recommendations based on data
    ai_insight = generate_recommendations(all_records)
    
    return jsonify({
        "records": all_records,
        "alerts": recent_alerts,
        "ai_recommendation": ai_insight
    }), 200

@app.route('/api/rewards/students', methods=['GET'])
def list_students():
    return jsonify(get_students()), 200

@app.route('/api/rewards/snacks', methods=['GET'])
def list_snacks():
    return jsonify(get_snacks()), 200

@app.route('/api/rewards/redeem', methods=['POST'])
def redeem_snack_endpoint():
    data = request.json
    student_id = data.get('student_id')
    snack_id = data.get('snack_id')
    
    if not student_id or not snack_id:
        return jsonify({"error": "Missing student_id or snack_id"}), 400
        
    success, result = redeem_snack(student_id, snack_id)
    if success:
        return jsonify({"status": "success", "data": result}), 200
    else:
        return jsonify({"error": result}), 400

# ── Authentication ──
ADMIN_CREDENTIALS = {"username": "admin", "password": "admin123"}
STUDENT_PASSWORD = "student"  # shared demo password for all students

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', '')
    
    if role == 'admin':
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            return jsonify({"role": "admin", "username": username}), 200
        return jsonify({"error": "Invalid admin credentials"}), 401
    
    elif role == 'student':
        if password != STUDENT_PASSWORD:
            return jsonify({"error": "Invalid password"}), 401
        student = get_student_by_id(username)
        if not student:
            return jsonify({"error": f"Student ID '{username}' not found"}), 401
        return jsonify({"role": "student", "student_id": student['id'], "name": student['name']}), 200
    
    return jsonify({"error": "Invalid role"}), 400

@app.route('/api/student/<student_id>/dashboard', methods=['GET'])
def student_dashboard(student_id):
    student = get_student_by_id(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
