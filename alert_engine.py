from db import add_alert

THRESHOLD_GRAMS_PER_SHIFT = 5000 # e.g. 5kg

def check_threshold(recent_records):
    total_waste = sum(r['weight_grams'] for r in recent_records)
    if total_waste > THRESHOLD_GRAMS_PER_SHIFT:
        msg = f"CRITICAL ALERT: High food waste detected! Total waste in recent shift: {total_waste/1000:.2f}kg."
        print(f"[SMS/EMAIL MOCK SENDING]: {msg}")
        add_alert(msg)
