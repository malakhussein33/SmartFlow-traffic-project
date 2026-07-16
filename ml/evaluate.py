"""
Model Evaluation Module
=======================
Calculates error metrics for regression models.
"""
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

class ModelEvaluator:
    def evaluate_regression(self, model, X_test, y_test) -> dict:
        """Evaluates RMSE, MAE, R2 scores for predictions."""
        predictions = model.predict(X_test)
        
        mse = mean_squared_error(y_test, predictions)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        
        # Calculate Mean Absolute Percentage Error (MAPE)
        # Avoid division by zero
        non_zero_mask = y_test != 0
        if np.any(non_zero_mask):
            mape = np.mean(np.abs((y_test[non_zero_mask] - predictions[non_zero_mask]) / y_test[non_zero_mask])) * 100
        else:
            mape = 0.0
            
        return {
            "RMSE": float(rmse),
            "MAE": float(mae),
            "R2": float(r2),
            "MAPE": float(mape)
        }
