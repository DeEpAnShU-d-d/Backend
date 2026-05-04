import requests
import time
import random

API_URL = "https://backend-wk20.onrender.com/api/sensor-data"

def simulate_esp32():
    print("Starting Mock ESP32 Sensor Data Stream...")
    # Send some data quickly to populate the dashboard immediately
    for _ in range(5):
        # 20% chance of a clean plate (0-5 grams)
        if random.random() < 0.2:
            weight = round(random.uniform(0.0, 5.0), 2)
        else:
            weight = round(random.uniform(500.0, 1500.0), 2)
            
        student_id = random.choice(["S001", "S002", "S003"])
        image_ref = f"cam_img_{int(time.time())}.jpg"
        payload = {"weight_grams": weight, "image_ref": image_ref, "student_id": student_id}
        try:
            res = requests.post(API_URL, json=payload)
            print(f"Sent: {payload} | Response: {res.status_code}")
        except Exception as e:
            print(f"Failed to connect to backend: {e}")
        time.sleep(1)

    while True:
        # Simulate a reading every 5 seconds
        # 20% chance of a clean plate
        if random.random() < 0.2:
            weight = round(random.uniform(0.0, 5.0), 2)
        else:
            weight = round(random.uniform(50.0, 500.0), 2)
            
        student_id = random.choice(["S001", "S002", "S003"])
        image_ref = f"cam_img_{int(time.time())}.jpg"
        
        payload = {
            "weight_grams": weight,
            "image_ref": image_ref,
            "student_id": student_id
        }
        
        try:
            res = requests.post(API_URL, json=payload)
            print(f"Sent: {payload} | Response: {res.status_code}")
        except Exception as e:
            print(f"Failed to connect to backend: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    simulate_esp32()
