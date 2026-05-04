import cv2
import os
import numpy as np
import json
import time
from db import update_student_face_encoding, get_students

# Load Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize LBPH Face Recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

def generate_frames():
    """
    Yields camera frames as MJPEG for the browser stream.
    """
    cam = cv2.VideoCapture(0)
    
    # Load recognizer if exists
    is_trained = os.path.exists('trainer.yml')
    if is_trained:
        recognizer.read('trainer.yml')
        with open('label_map.json', 'r') as f:
            label_map = json.load(f)

    while True:
        success, frame = cam.read()
        if not success:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            color = (0, 165, 255) # Warm Orange
            name = "Scanning..."
            
            if is_trained:
                face_img = gray[y:y+h, x:x+w]
                face_img = cv2.resize(face_img, (200, 200))
                label_idx, confidence = recognizer.predict(face_img)
                
                if confidence < 70:
                    name = label_map.get(str(label_idx), "Unknown")
                    color = (0, 255, 0) # Green for match
                else:
                    name = "Unknown"
                    color = (0, 0, 255) # Red for mismatch

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
    cam.release()

def capture_face_samples(student_id):
    """
    Captures 30 samples of a face from the webcam for enrollment.
    Optimized: Removed imshow to reduce lag.
    """
    cam = cv2.VideoCapture(0)
    count = 0
    samples = []
    
    # Warm up camera
    for _ in range(5): cam.read()

    while count < 30:
        ret, frame = cam.read()
        if not ret: break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            count += 1
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (200, 200))
            samples.append(face_img)
            time.sleep(0.05) # Small delay to avoid burst capture
            if count >= 30: break
            
        if count >= 30: break
            
    cam.release()
    return samples if len(samples) > 0 else None

def train_recognizer():
    """
    Trains the recognizer with all enrolled students.
    """
    faces = []
    labels = []
    label_map = {} # map integer labels to student IDs
    
    dataset_path = 'dataset'
    if not os.path.exists(dataset_path):
        return False
        
    for i, student_id in enumerate(os.listdir(dataset_path)):
        label_map[i] = student_id
        student_dir = os.path.join(dataset_path, student_id)
        if not os.path.isdir(student_dir):
            continue
        for image_name in os.listdir(student_dir):
            img_path = os.path.join(student_dir, image_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(img)
                labels.append(i)
            
    if faces:
        recognizer.train(faces, np.array(labels))
        recognizer.save('trainer.yml')
        with open('label_map.json', 'w') as f:
            json.dump(label_map, f)
        return True
    return False

def recognize_face():
    """
    Optimized for Web: Captures for 2 seconds and returns recognized ID.
    Removed imshow to reduce lag.
    """
    if not os.path.exists('trainer.yml'):
        return None, "Model not trained"
        
    recognizer.read('trainer.yml')
    if not os.path.exists('label_map.json'): return None, "Label map missing"
    with open('label_map.json', 'r') as f:
        label_map = json.load(f)
        
    cam = cv2.VideoCapture(0)
    student_id = None
    
    # Try capturing for up to 2 seconds to find a face
    start_time = time.time()
    while time.time() - start_time < 2:
        ret, frame = cam.read()
        if not ret: break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (200, 200))
            label_idx, confidence = recognizer.predict(face_img)
            
            if confidence < 75: # Recognized
                student_id = label_map.get(str(label_idx))
                break
        
        if student_id: break
            
    cam.release()
    return student_id, None
