# Churn Model Evaluation Report

- Evaluation dataset: F:\project\churn-prediction\churn-ai-platform\data\processed\telco_churn_cleaned.csv
- Test size: 0.2
- Random state: 42

## Model Comparison (sorted by ROC-AUC)

| Model | Accuracy | ROC-AUC | Precision | Recall | F1 | Confusion Matrix |
|---|---:|---:|---:|---:|---:|---|
| xgboost | 0.9588 | 0.9926 | 0.9136 | 0.9332 | 0.9233 | [[1002, 33], [25, 349]] |
| lightgbm | 0.9574 | 0.9925 | 0.9046 | 0.9385 | 0.9213 | [[998, 37], [23, 351]] |
| logistic_regression | 0.9546 | 0.9923 | 0.8974 | 0.9358 | 0.9162 | [[995, 40], [24, 350]] |
| random_forest | 0.9077 | 0.9580 | 0.8020 | 0.8663 | 0.8329 | [[955, 80], [50, 324]] |

## Best Model
- Selected model: xgboost
- ROC-AUC: 0.9926
- Accuracy: 0.9588
- Precision: 0.9136
- Recall: 0.9332
- F1-score: 0.9233
- Confusion matrix: [[1002, 33], [25, 349]]