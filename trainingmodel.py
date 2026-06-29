import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os

# 1. Load dataset
dataset_path = "grocery_dataset.csv"
if not os.path.exists(dataset_path):
    # Fallback to generate it if missing
    import subprocess
    print("Dataset not found, generating...")
    subprocess.run(["python", "generate_dataset.py"])

df = pd.read_csv(dataset_path)

# 2. Features and label
# Features: Quantity, Days to Expiry, Storage Temperature, Perishability Index (Category-based)
X = df[["quantity", "days_to_expiry", "storage_temperature", "perishability_index"]]
y = df["estimated_waste_pct"]

# 3. Train/Test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Train Decision Tree model
model = DecisionTreeRegressor(random_state=42, max_depth=5)
model.fit(X_train, y_train)

# 5. Evaluate
preds = model.predict(X_test)
mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)

print("--- Model Training Results ---")
print(f"Mean Absolute Error (MAE): {mae:.2f}%")
print(f"R2 Score: {r2:.4f}")

# 6. Save model to backend directory
model_dir = "backend"
if not os.path.exists(model_dir):
    os.makedirs(model_dir)

model_path = os.path.join(model_dir, "grocery_model.joblib")
joblib.dump(model, model_path)
print(f"Trained model saved successfully to: {os.path.abspath(model_path)}")