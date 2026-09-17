# Customer Churn Prediction using XGBoost

## Overview

Customer churn is one of the most critical challenges for subscription-based businesses. Retaining existing customers is significantly more cost-effective than acquiring new ones.

This project uses Machine Learning and Explainable AI to predict customer churn and identify customers at high risk of leaving a service. The solution helps businesses take proactive retention actions and improve customer lifetime value.

---

## Business Problem

Organizations lose significant revenue when customers discontinue their services. Identifying churn-prone customers in advance allows businesses to implement targeted retention strategies.

This project aims to:

* Predict customer churn probability
* Identify high-risk customers
* Understand key churn drivers
* Support data-driven decision making
* Improve customer retention

---

## Dataset

The model is trained using a Telco Customer Churn Dataset containing customer demographics, service information, billing behavior, and account history.

### Features Used

* Age
* Gender
* Tenure
* Monthly Charges
* Contract Type
* Internet Service
* Payment Method
* Customer Lifetime Value
* Service Usage Information

### Target Variable

**Churn**

* 1 = Customer likely to leave
* 0 = Customer likely to stay

---

## Data Preprocessing

The dataset was prepared using a Scikit-Learn preprocessing pipeline.

### Steps Performed

* Missing Value Imputation
* Data Cleaning
* Feature Encoding
* Feature Scaling
* One-Hot Encoding
* Feature Transformation

This ensures consistent processing during both training and prediction stages.

---

## Feature Engineering

Feature engineering was applied to improve predictive performance and capture customer behavior patterns.

Key feature groups include:

* Customer Demographics
* Contract Information
* Billing Behavior
* Service Usage Metrics
* Customer Retention Signals

---

## Machine Learning Model

### Algorithm

**XGBoost Classifier**

XGBoost was selected because of its strong performance on structured customer data and its ability to handle complex feature interactions.

### Model Capabilities

* Binary Classification
* Churn Probability Prediction
* Risk Classification
* Feature Importance Analysis

---

## Model Performance

### Validation Results

| Metric              | Value                 |
| ------------------- | --------------------- |
| Algorithm           | XGBoost Classifier    |
| Classification Type | Binary Classification |
| Probability Output  | Supported             |
| Explainability      | SHAP                  |
| Model Pipeline      | Scikit-Learn Pipeline |

### Probability Distribution

* Minimum Churn Probability: 0.0035
* Maximum Churn Probability: 0.9965
* Mean Probability: 0.2881

The model produces distinct churn probabilities across different customer profiles, confirming real predictive behavior.

> Add your actual Accuracy, Precision, Recall, F1-Score, and ROC-AUC values here from model evaluation.

---

## Explainable AI (SHAP)

To improve model transparency, SHAP (SHapley Additive Explanations) was used.

SHAP helps identify:

* Most influential features
* Positive churn drivers
* Negative churn drivers
* Individual prediction explanations

This makes model predictions interpretable and business-friendly.

---

## Machine Learning Workflow

```text
Data Collection
       ↓
Data Cleaning
       ↓
Feature Engineering
       ↓
Data Preprocessing
       ↓
Model Training
       ↓
Model Evaluation
       ↓
SHAP Explainability
       ↓
Churn Prediction
       ↓
Business Insights
```

---

## Tools & Technologies

### Programming

* Python

### Data Analysis

* Pandas
* NumPy

### Machine Learning

* Scikit-Learn
* XGBoost

### Explainable AI

* SHAP

### Experiment Tracking

* MLflow

### Visualization

* Matplotlib
* Power BI

---

## Business Impact

The solution enables organizations to:

* Reduce customer churn
* Improve customer retention
* Increase customer lifetime value
* Identify high-risk customers
* Optimize retention campaigns
* Support data-driven business decisions

---

## Future Improvements

* Automated Model Retraining
* Model Drift Monitoring
* Advanced Customer Segmentation
* Real-Time Prediction Pipeline
* Deep Learning-Based Churn Prediction
* Cloud Deployment

---

## Author

### Yashraj Thube

Data Science | Machine Learning | Artificial Intelligence

GitHub: https://github.com/YashrajThube
