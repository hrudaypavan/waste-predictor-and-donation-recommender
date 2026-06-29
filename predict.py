import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# Load dataset
df = pd.read_excel("Grocery_Waste_Dataset_500.xlsx")

# Encode categorical data
df["Consumed"] = df["Consumed"].map({"Yes":1, "No":0, "Partial":0.5})

# Features & label
X = df[["Quantity", "Days to Expiry", "Consumed"]]
y = df["Estimated Waste (%)"]

# Train model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = DecisionTreeRegressor()
model.fit(X_train, y_train)

# Evaluate
preds = model.predict(X_test)
print("MAE:", mean_absolute_error(y_test, preds))