# Real-World AI-Driven Analytics Solution Using Python

## Project Topic

This repository contains the complete Deliverable 2 analytics and model optimization project using the NYC Taxi and Limousine Commission Yellow Taxi Trip Record dataset. The project frames a transportation analytics problem: predicting whether a taxi trip is likely to last at least 30 minutes.

The solution uses Python, pandas, NumPy, Matplotlib, Seaborn, and scikit-learn to download data, preprocess it, perform exploratory analysis, tune an optimized AI model, and evaluate ethical/practical considerations. The final submission packet is available as one PDF so the full report, metrics, figures, code, and reproducibility notes can be reviewed in one place.

## Business Problem

Taxi operators, dispatch teams, and city transportation planners need early signals about trip duration. A long-trip risk model can support driver shift planning, passenger wait-time estimates, airport operations, and congestion-aware service monitoring. This project treats the model as a decision-support tool, not a system for denying rides or penalizing neighborhoods.

## Dataset

- Source: NYC TLC Trip Record Data
- File: Yellow Taxi Trip Records, January 2024
- Direct data URL: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
- Data dictionary: https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf

The raw parquet file is downloaded automatically into `data/raw/` and is not committed to GitHub because it is large.

## Repository Structure

```text
.
|-- data/
|   `-- README.md
|-- notebooks/
|   |-- README.md
|   |-- predict_new_taxi_trip.ipynb
|   `-- nyc_taxi_long_trip_model.ipynb
|-- reports/
|   |-- README.md
|   |-- assignment_report.md
|   |-- metrics.json
|   |-- preprocessing_audit.csv
|   |-- feature_engineering_summary.csv
|   |-- target_distribution.csv
|   |-- model_metrics.csv
|   |-- model_coefficients.csv
|   |-- model_feature_importance.csv
|   |-- tuning_results.csv
|   `-- figures/
|-- src/
|   `-- nyc_taxi_long_trip_model.py
|-- output/
|   `-- pdf/
|-- requirements.txt
`-- README.md
```

## How to Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\nyc_taxi_long_trip_model.py
```

The script downloads the official dataset, cleans it, tunes a histogram gradient boosting classifier, selects a recall-protected precision threshold, and writes charts plus metrics to `reports/`.

To use a smaller sample while testing:

```powershell
.\.venv\Scripts\python.exe src\nyc_taxi_long_trip_model.py --sample-size 30000
```

## Deliverables

- Primary full PDF submission packet: `output/pdf/NYC_Taxi_Deliverable_2_Full_Submission_Report.pdf`
- Written Deliverable 2 report: `reports/assignment_report.md`
- Word version of Deliverable 2 report: `reports/NYC_Taxi_Deliverable_2_Model_Optimization_Report.docx`
- Reproducible Python pipeline: `src/nyc_taxi_long_trip_model.py`
- New-trip prediction notebook: `notebooks/predict_new_taxi_trip.ipynb`
- Generated model metrics: `reports/metrics.json` and `reports/model_metrics.csv`
- Hyperparameter tuning results: `reports/tuning_results.csv`
- Final model feature importance: `reports/model_feature_importance.csv`
- Detailed preprocessing audit: `reports/preprocessing_audit.csv`
- EDA and evaluation charts: `reports/figures/`
- GitHub-ready version control structure with ignored raw data and model binaries

## Final Model Summary

The final optimized model is a histogram gradient boosting classifier selected with validation F0.5 while requiring recall to stay at or above 0.865. The selected threshold is 0.35, which improves precision while keeping long-trip recall slightly above the Day 1 logistic regression reference.

| Metric | Day 1 logistic | Day 2 optimized |
|---|---:|---:|
| Accuracy | 0.9176 | 0.9417 |
| Precision | 0.5183 | 0.6201 |
| Recall | 0.8647 | 0.8685 |
| F1 | 0.6482 | 0.7236 |
| ROC-AUC | 0.9622 | 0.9751 |
| False positives | 1,693 | 1,121 |
| False negatives | 285 | 277 |
