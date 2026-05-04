import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from db import init_db, add_waste_record, get_all_waste, get_recent_alerts, get_students, get_snacks, add_points_to_student, redeem_snack, get_student_by_id, update_student_face_encoding, create_student, delete_student, award_bonus_points
from ai_engine import classify_image, generate_recommendations, plan_mess_menu
from alert_engine import check_threshold
from face_engine import capture_face_samples, train_recognizer, recognize_face, generate_frames

app = Flask(__name__)
CORS(app) # Enable CORS for frontend

init_db()

# Ensure dataset directory exists
DATASET_DIR = 'dataset'
if not os.path.exists(DATASET_DIR):
    os.makedirs(DATASET_DIR)
init_db()

# Global state to track the latest weight reading
latest_sensor_data = {"weight_grams": 0, "timestamp": 0}

@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """
    Endpoint for ESP32 to send data.
    Expected JSON: {"weight_grams": float, "image_ref": string}
    """
    import time
    data = request.json
    weight = data.get('weight_grams')
    image_ref = data.get('image_ref')

    # Store latest weight for recognition matching
    global latest_sensor_data
    latest_sensor_data = {"weight_grams": weight if weight is not None else 0, "timestamp": time.time()}

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
    planned_menu = plan_mess_menu(all_records)
    
    return jsonify({
        "records": all_records,
        "alerts": recent_alerts,
        "ai_recommendation": ai_insight,
        "mess_menu": planned_menu
    }), 200

@app.route('/api/rewards/students', methods=['GET'])
def list_students():
    return jsonify(get_students()), 200

@app.route('/api/rewards/students/add', methods=['POST'])
def add_student_endpoint():
    data = request.json
    student_id = data.get('id')
    name = data.get('name')
    
    if not student_id or not name:
        return jsonify({"error": "Missing id or name"}), 400
        
    success, message = create_student(student_id, name)
    if success:
        return jsonify({"status": "success", "message": message}), 201
    else:
        return jsonify({"error": message}), 400

@app.route('/api/rewards/students/<student_id>', methods=['DELETE'])
def delete_student_endpoint(student_id):
    success, message = delete_student(student_id)
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"error": message}), 404

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

@app.route('/api/face/enroll', methods=['POST'])
def enroll_face():
    data = request.json
    student_id = data.get('student_id')
    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400
    
    student = get_student_by_id(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    # Capture samples
    samples = capture_face_samples(student_id)
    if samples:
        # Save samples to disk
        student_dir = os.path.join(DATASET_DIR, student_id)
        if not os.path.exists(student_dir):
            os.makedirs(student_dir)
            
        import cv2
        for i, sample in enumerate(samples):
            cv2.imwrite(os.path.join(student_dir, f"{i}.jpg"), sample)
        
        # Update DB to mark as enrolled
        update_student_face_encoding(student_id, "ENROLLED")
        
        # Train model after enrollment
        train_recognizer()
        
        return jsonify({"status": "success", "message": f"Enrolled {student_id}"}), 200
    else:
        return jsonify({"error": "No face samples captured"}), 400

@app.route('/api/face/recognize', methods=['GET'])
def recognize_face_endpoint():
    student_id, error = recognize_face()
    if error:
        return jsonify({"error": error}), 400
    
    if student_id:
        student = get_student_by_id(student_id)
        
        # Automatic Bonus Point Logic based on latest weight
        import time
        global latest_sensor_data
        
        points_awarded = 0
        # Check if weight was received in the last 10 seconds
        if time.time() - latest_sensor_data["timestamp"] < 10:
            weight = latest_sensor_data["weight_grams"]
            success, points = award_bonus_points(student_id, weight)
            points_awarded = points if success else 0
            
        return jsonify({
            "status": "success", 
            "student_id": student_id, 
            "student": student,
            "points_awarded": points_awarded,
            "waste_measured": latest_sensor_data["weight_grams"]
        }), 200
    else:
        return jsonify({"error": "No face recognized or process cancelled"}), 404

@app.route('/api/face/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/face/train', methods=['POST'])
def train_face_model():
    success = train_recognizer()
    if success:
        return jsonify({"status": "success", "message": "Model trained successfully"}), 200
    else:
        return jsonify({"error": "Training failed (likely no dataset)"}), 400

@app.route('/api/student/<student_id>/dashboard', methods=['GET'])
def student_dashboard(student_id):
    student = get_student_by_id(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
