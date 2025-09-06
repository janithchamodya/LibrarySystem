# prediction_model.py — loader for v2 (no custom class)
import os, joblib, numpy as np
MODEL_V2 = os.path.join("model", "return_days_model_fixed_features_v2.pkl")
B = joblib.load(MODEL_V2)

def predict_holding_days(features):
    X = np.asarray([features], dtype=float)
    preds = []
    if B["rf"]  is not None: preds.append(B["rf"].predict(X))
    if B["gbr"] is not None: preds.append(B["gbr"].predict(X))
    if B["xgb"] is not None: preds.append(B["xgb"].predict(X))
    y = np.column_stack(preds).mean(axis=1)
    return float(y[0])