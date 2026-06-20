# Reports

Running `python src/nyc_taxi_long_trip_model.py` writes the project outputs here:

- `assignment_report.md`: Deliverable 2 report covering tuning, final evaluation, ethics, real-world application, and conclusion.
- `NYC_Taxi_Deliverable_2_Model_Optimization_Report.docx`: Word document version of the Deliverable 2 report.
- `metrics.json`: dataset summary, baseline metrics, model metrics, and classification report.
- `preprocessing_audit.csv`: row counts before/after each cleaning and sampling step.
- `feature_engineering_summary.csv`: explanation of new or transformed columns.
- `target_distribution.csv`: class balance after preprocessing and sampling.
- `model_metrics.csv`: compact baseline, initial logistic, and optimized model comparison table.
- `tuning_results.csv`: validation-set hyperparameter and threshold tuning results.
- `model_feature_importance.csv`: permutation importance for the optimized final model.
- `model_coefficients.csv`: reference coefficients from the initial logistic regression model.
- `figures/`: exploratory and model evaluation charts used in the report.

The latest submitted model is the optimized histogram gradient boosting classifier with a 0.35 decision threshold. It achieved 0.9417 accuracy, 0.6201 precision, 0.8685 recall, 0.7236 F1, and 0.9751 ROC-AUC on the held-out test set. The full one-file PDF submission packet is saved at `output/pdf/NYC_Taxi_Deliverable_2_Full_Submission_Report.pdf`.
