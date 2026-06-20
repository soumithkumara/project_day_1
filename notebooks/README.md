# Notebook Use

The analysis is implemented as a Python script so it can run locally, in GitHub Codespaces, or in Google Colab.

For Google Colab:

1. Open a new Colab notebook.
2. Clone this repo:

   ```python
   !git clone --branch project_day_2 https://github.com/soumithkumara/project_day_1.git
   %cd project_day_1
   ```

3. Install dependencies and run the analysis:

   ```python
   !pip install -r requirements.txt
   !python src/nyc_taxi_long_trip_model.py
   ```

4. View the generated charts in `reports/figures/` and metrics in `reports/metrics.json`.

The notebook `nyc_taxi_long_trip_model.ipynb` also displays the preprocessing audit, feature engineering summary, target distribution, metrics table, tuning results, optimized feature importance, and saved PNG charts inline after the pipeline finishes.

Use `predict_new_taxi_trip.ipynb` when you only want to pass a new taxi trip into the trained model and see whether it is predicted to be a 30+ minute trip.
