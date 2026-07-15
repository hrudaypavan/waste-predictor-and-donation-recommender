import pandas as pd
import numpy as np
import os

# -------------------------------------------------------
# Real-world category definitions:
# Each category has:
#   perishability: 1=low, 2=medium, 3=high (how fast it spoils)
#   temp:          ideal storage temperature in Celsius
#   days_range:    realistic min/max days until expiry
#   qty_range:     realistic min/max quantity a user might store (kg/liters/units)
# -------------------------------------------------------
categories = {
    'Dairy':         {'perishability': 3, 'temp': 4,   'days_range': (3,   21),   'qty_range': (0.5, 5.0)},
    'Fruits':        {'perishability': 2, 'temp': 25,  'days_range': (2,   14),   'qty_range': (0.5, 8.0)},
    'Vegetables':    {'perishability': 2, 'temp': 25,  'days_range': (2,   14),   'qty_range': (0.5, 6.0)},
    'Meat/Fish':     {'perishability': 3, 'temp': 4,   'days_range': (1,   7),    'qty_range': (0.2, 3.0)},
    'Bakery':        {'perishability': 3, 'temp': 25,  'days_range': (1,   10),   'qty_range': (0.2, 2.0)},
    'Pantry/Grains': {'perishability': 1, 'temp': 25,  'days_range': (180, 1500), 'qty_range': (0.5, 30.0)},
    'Frozen Foods':  {'perishability': 1, 'temp': -18, 'days_range': (60,  730),  'qty_range': (0.5, 10.0)},
}

category_names = list(categories.keys())

# -------------------------------------------------------
# Generate 3000 realistic synthetic records
# -------------------------------------------------------
np.random.seed(42)
num_records = 3000

data = []
for i in range(num_records):
    category = np.random.choice(category_names)
    info = categories[category]

    # Pick realistic quantity and days_to_expiry for this category
    quantity = round(np.random.uniform(info['qty_range'][0], info['qty_range'][1]), 2)
    days_to_expiry = np.random.randint(info['days_range'][0], info['days_range'][1])

    # Storage temperature with slight real-world deviation from ideal
    recommended_temp = info['temp']
    if recommended_temp != -18:
        storage_temp = recommended_temp + np.random.choice([-2, 0, 0, 2, 5, 8])
    else:
        storage_temp = recommended_temp  # frozen stays frozen

    perishability = info['perishability']
    max_days = info['days_range'][1]

    # -------------------------------------------------------
    # Waste % Formula (real-world logic):
    #
    # 1. Freshness Factor (dominant):
    #    How close the item is to its expiry RELATIVE to its natural max shelf life.
    #    freshness_ratio → 1.0 means just purchased, 0.0 means expired.
    #    Low freshness (close to expiry) means HIGH waste risk.
    #
    # 2. Perishability Penalty:
    #    Dairy/Meat (perishability=3) spoil fast, so they carry a base penalty.
    #    Pantry/Frozen (perishability=1) are very stable, so low base penalty.
    #
    # 3. Quantity Factor:
    #    Large bulk quantities are harder to consume before expiry.
    #
    # 4. Temperature Factor:
    #    Storing items warmer than recommended speeds up spoilage.
    # -------------------------------------------------------
    freshness_ratio = days_to_expiry / max_days  # 0 = nearly expired, 1 = very fresh

    freshness_penalty = (1 - freshness_ratio) * 50        # max 50% from freshness
    perishability_penalty = (perishability - 1) * 15      # 0, 15, or 30%
    quantity_penalty = (quantity / info['qty_range'][1]) * 10  # max 10%
    temp_penalty = max(0, storage_temp - recommended_temp) * 0.5  # warm storage

    base_waste = freshness_penalty + perishability_penalty + quantity_penalty + temp_penalty
    noise = np.random.normal(0, 3)
    estimated_waste_pct = round(float(np.clip(base_waste + noise, 0, 100)), 2)

    data.append({
        'item_name': np.random.choice(['Milk', 'Apple', 'Tomato', 'Salmon', 'Bread', 'Rice',
                                        'Frozen Pizza', 'Yogurt', 'Banana', 'Spinach', 'Chicken', 'Cheese']),
        'category': category,
        'quantity': quantity,
        'days_to_expiry': days_to_expiry,
        'storage_temperature': storage_temp,
        'perishability_index': perishability,
        'estimated_waste_pct': estimated_waste_pct
    })

df = pd.DataFrame(data)
output_path = "grocery_dataset.csv"
df.to_csv(output_path, index=False)
print(f"Generated {num_records} records → {os.path.abspath(output_path)}")
print("\nAverage stats per category:")
print(df.groupby('category')[['days_to_expiry', 'estimated_waste_pct']].mean().round(1).to_string())
