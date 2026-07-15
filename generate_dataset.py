import pandas as pd
import numpy as np
import os

# Define categories and their average perishability levels (1: Low, 2: Medium, 3: High)
categories = {
    'Dairy': {'perishability': 3, 'temp': 4},
    'Fruits': {'perishability': 2, 'temp': 25},
    'Vegetables': {'perishability': 2, 'temp': 25},
    'Meat/Fish': {'perishability': 3, 'temp': 4},
    'Bakery': {'perishability': 3, 'temp': 25},
    'Pantry/Grains': {'perishability': 1, 'temp': 25},
    'Frozen Foods': {'perishability': 1, 'temp': -18}
}

category_names = list(categories.keys())

# Generate synthetic records
np.random.seed(42)
num_records = 2000

data = []
for i in range(num_records):
    category = np.random.choice(category_names)
    info = categories[category]
    
    quantity = np.random.uniform(0.5, 30.0) # Quantity in kg/liters/units
    days_to_expiry = np.random.randint(1, 1000) # Days to expiry from purchase
    
    # Storage temperature might deviate slightly from recommended
    recommended_temp = info['temp']
    storage_temp = recommended_temp + np.random.choice([-2, 0, 2, 5, 10]) if recommended_temp != -18 else recommended_temp
    
    perishability = info['perishability']
    
    # Calculate synthetic waste risk percentage
    # High temp, high perishability, low days_to_expiry, and high quantity increase waste likelihood
    base_waste = (perishability * 15) + (30 - days_to_expiry) * 1.5 + (storage_temp * 0.8) + (quantity * 1.2)
    noise = np.random.normal(0, 5)
    estimated_waste_pct = np.clip(base_waste + noise, 0, 100)
    
    data.append({
        'item_name': np.random.choice(['Milk', 'Apple', 'Tomato', 'Salmon', 'Bread', 'Rice', 'Frozen Pizza', 'Yogurt', 'Banana', 'Spinach', 'Chicken', 'Cheese']),
        'category': category,
        'quantity': round(quantity, 2),
        'days_to_expiry': days_to_expiry,
        'storage_temperature': storage_temp,
        'perishability_index': perishability,
        'estimated_waste_pct': round(estimated_waste_pct, 2)
    })

df = pd.DataFrame(data)
output_path = "grocery_dataset.csv"
df.to_csv(output_path, index=False)
print(f"Generated synthetic dataset with {num_records} records at: {os.path.abspath(output_path)}")
print(df.head())
