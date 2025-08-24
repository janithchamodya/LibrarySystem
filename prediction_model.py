# === prediction_model.py ===
import joblib
import numpy as np
import os

# ✅ Correct filenames
model_path = os.path.join("model", "xgb_regressor_model.pkl")
scaler_path = os.path.join("model", "scaler_for_xgb.pkl")

# ✅ Load model and scaler with joblib
model = joblib.load(model_path)
scaler = joblib.load(scaler_path)

def predict_holding_days(input_features):
    input_array = np.array(input_features).reshape(1, -1)
    scaled_input = scaler.transform(input_array)
    return model.predict(scaled_input)[0]
