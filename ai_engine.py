import random

FOOD_TYPES = ['Daal', 'Rice', 'Chapati', 'Paneer', 'Aloo']

def classify_image(image_ref):
    """
    Mock Image Classifier:
    In a real scenario, this would send the image to a CNN or pre-trained vision model.
    """
    if not image_ref:
        return "Unknown"
    # Simulate identifying dominant food type
    return random.choice(FOOD_TYPES)

def generate_recommendations(waste_records):
    """
    Mock Gen-AI Analysis:
    In a real scenario, this would send aggregated data to an LLM to get insights.
    """
    if not waste_records:
        return "Not enough data to generate recommendations."
    
    # Calculate some basic stats to feed the "AI"
    total_waste = sum(r['weight_grams'] for r in waste_records)
    if total_waste < 1000:
        return "Waste levels are currently low. Keep up the good work!"
    
    # Simulate finding the most wasted item
    food_counts = {}
    for r in waste_records:
        food = r.get('classified_food', 'Unknown')
        food_counts[food] = food_counts.get(food, 0) + r['weight_grams']
    
    most_wasted = max(food_counts, key=food_counts.get) if food_counts else "Unknown"
    
    prompts = [
        f"Significant amounts of {most_wasted} are being discarded. Consider reducing {most_wasted} portion sizes by 15%.",
        f"Noticeable waste trend detected: {most_wasted} is frequently left over. Recommend adjusting the menu or surveying students about this dish.",
        f"High overall waste detected ({total_waste/1000:.1f}kg). Consider implementing a 'taste before you take' policy for the main dishes."
    ]
    
def plan_mess_menu(waste_records):
    """
    Generates a Mess Menu Planner recommendation based on waste data.
    """
    food_waste = {}
    for r in waste_records:
        food = r.get('classified_food', 'Unknown')
        food_waste[food] = food_waste.get(food, 0) + r['weight_grams']
    
    # Identify high waste and low waste items
    sorted_waste = sorted(food_waste.items(), key=lambda x: x[1], reverse=True)
    
    # Mocking a default menu
    default_menu = {
        "Monday": "Daal & Rice",
        "Tuesday": "Paneer & Chapati",
        "Wednesday": "Aloo Jeera & Rice",
        "Thursday": "Daal & Chapati",
        "Friday": "Paneer Matar & Rice",
        "Saturday": "Aloo Paratha & Daal",
        "Sunday": "Special Paneer & Rice"
    }
    
    if not sorted_waste:
        return default_menu
        
    high_waste_items = [item[0] for item in sorted_waste[:2]]
    
    planned_menu = {}
    for day, dish in default_menu.items():
        needs_swap = any(hw.lower() in dish.lower() for hw in high_waste_items)
        if needs_swap:
            planned_menu[day] = dish + " (ADAPTED: Reduced Portion)"
        else:
            planned_menu[day] = dish
            
    return planned_menu
