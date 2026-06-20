# Reports

Running `python src/nyc_taxi_long_trip_model.py` writes the project outputs here:

- `assignment_report.md`: Deliverable 2 report covering tuning, final evaluation, ethics, real-world application, and conclusion.
- `metrics.json`: dataset summary, baseline metrics, model metrics, and classification report.
- `preprocessing_audit.csv`: row counts before/after each cleaning and sampling step.
- `feature_engineering_summary.csv`: explanation of new or transformed columns.
- `target_distribution.csv`: class balance after preprocessing and sampling.
- `model_metrics.csv`: compact baseline, initial logistic, and optimized model comparison table.
- `tuning_results.csv`: validation-set hyperparameter and threshold tuning results.
- `model_feature_importance.csv`: permutation importance for the optimized final model.
- `model_coefficients.csv`: reference coefficients from the initial logistic regression model.
- `figures/`: exploratory and model evaluation charts used in the report.
