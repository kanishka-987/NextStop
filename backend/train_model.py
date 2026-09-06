# backend/train_model.py
# Script to trigger initial training of the Random Forest model.

import sys
import os

# Adjust path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ml import preprocess_and_train

print("[*] Starting Random Forest Regressor training...")
metrics_data = preprocess_and_train()
if metrics_data:
    print(f"[+] Model trained successfully!")
    print(f"    R² Accuracy: {metrics_data['accuracy']}%")
    print(f"    Mean Absolute Error (MAE): {metrics_data['mae']}")
    print(f"    RMSE: {metrics_data['rmse']}")
else:
    print("[-] Failed to train model. Excel dataset not found.")
