# Real-World AI-Driven Analytics Solution Using Python

## Project Topic

This repository contains a complete initial analytics deliverable using the NYC Taxi and Limousine Commission Yellow Taxi Trip Record dataset. The project frames a transportation analytics problem: predicting whether a taxi trip is likely to last at least 30 minutes.

The solution uses Python, pandas, NumPy, Matplotlib, Seaborn, and scikit-learn to download data, preprocess it, perform exploratory analysis, train an initial AI model, and evaluate ethical considerations.

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

The script downloads the official dataset, cleans it, trains a class-balanced logistic regression model, and writes charts plus metrics to `reports/`.

To use a smaller sample while testing:

```powershell
.\.venv\Scripts\python.exe src\nyc_taxi_long_trip_model.py --sample-size 30000
```

## Deliverables

- Written assignment report: `reports/assignment_report.md`
- Reproducible Python pipeline: `src/nyc_taxi_long_trip_model.py`
- New-trip prediction notebook: `notebooks/predict_new_taxi_trip.ipynb`
- One-file submission PDF: `output/pdf/NYC_Taxi_AI_Analytics_Submission_Guide.pdf`
- Generated model metrics: `reports/metrics.json` and `reports/model_metrics.csv`
- Detailed preprocessing audit: `reports/preprocessing_audit.csv`
- EDA and evaluation charts: `reports/figures/`
- GitHub-ready version control structure with ignored raw data and model binaries
