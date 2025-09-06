# convert_model.py
import joblib
import numpy as np

# Re-declare the class so we can load the old bundle once
class Ensemble:
    def __init__(self, rf, gbr, xgb):
        self.rf = rf
        self.gbr = gbr
        self.xgb = xgb
    def predict(self, X):
        X = np.asarray(X, dtype=float)
        preds = []
        if self.rf is not None: preds.append(self.rf.predict(X))
        if self.gbr is not None: preds.append(self.gbr.predict(X))
        if self.xgb is not None: preds.append(self.xgb.predict(X))
        return np.column_stack(preds).mean(axis=1)

bundle = joblib.load("model/return_days_model_fixed_features.pkl")
model = bundle["model"]
feature_order = bundle.get("feature_order")

# Save a SAFE bundle with only standard sklearn estimators
safe_bundle = {
    "rf":  getattr(model, "rf", None),
    "gbr": getattr(model, "gbr", None),
    "xgb": getattr(model, "xgb", None),
    "feature_order": feature_order
}
joblib.dump(safe_bundle, "model/return_days_model_fixed_features_v2.pkl")
print("Saved: model/return_days_model_fixed_features_v2.pkl")
