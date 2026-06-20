# Deliverable 2: Model Optimization, Real-World Impact, and Ethical Evaluation

## Project Title

Predicting Long NYC Yellow Taxi Trips for Dispatch and Congestion-Aware Planning

## Objective

This second deliverable refines the Day 1 NYC taxi long-trip model, tunes hyperparameters, evaluates the final optimized model, and reflects on real-world value, ethical limits, and future improvements. The project still predicts the binary target `long_trip`, where `1` means a cleaned yellow taxi trip lasted at least 30 minutes and `0` means it lasted under 30 minutes.

The dataset remains the official NYC Taxi and Limousine Commission Yellow Taxi Trip Record file for January 2024. The pipeline cleaned **2,964,624** raw rows down to **2,684,599** realistic trips, then used a deterministic **120,000-row** modeling sample with `random_state=42`. Long trips represented **8.78%** of the modeling sample, so model quality must be judged with precision, recall, F1, F0.5, and ROC-AUC in addition to accuracy.

## 1. Hyperparameter Tuning

The Day 1 model used a class-balanced logistic regression classifier. That model was useful because it was interpretable and had strong long-trip recall, but its precision was modest. In this use case, low precision means the system would warn dispatch teams about too many trips that do not actually become long trips. For Deliverable 2, the optimization goal was to improve accuracy and precision while still retaining enough recall for planning.

The final tuning workflow used a **60/20/20 stratified train-validation-test split**. The training set was used to fit candidate models, the validation set was used to choose hyperparameters and the classification threshold, and the test set was held out for final evaluation. This is more rigorous than tuning directly on the test set because it keeps the final test metrics independent from the model-selection step.

The optimized model family was scikit-learn's **histogram gradient boosting classifier**. This model was selected because it can capture nonlinear relationships between trip distance, pickup time, taxi zones, airport trips, and long-trip likelihood. Categorical fields were ordinal-encoded inside a scikit-learn `Pipeline`, and the classifier was told which transformed columns were categorical. This avoids treating taxi zone IDs as simple continuous numeric values.

Five candidate configurations were evaluated by changing `max_iter`, `learning_rate`, `max_leaf_nodes`, `l2_regularization`, and `class_weight`. For each candidate, the validation probabilities were searched across thresholds from 0.05 to 0.95. The threshold selection metric was **F0.5 with validation recall at or above 0.72**. F0.5 weights precision more heavily than recall, which matches the Day 2 request to improve accuracy and precision, while the recall floor prevents the model from becoming too conservative.

The selected candidate was:

- Model: optimized histogram gradient boosting
- Candidate: `hgb_depth63_weight6`
- `max_iter`: 200
- `learning_rate`: 0.08
- `max_leaf_nodes`: 63
- `l2_regularization`: 0.1
- `class_weight`: `{0: 1, 1: 6}`
- Decision threshold: `0.80`

The validation tuning table is saved in `reports/tuning_results.csv`. The selected model had the strongest validation F0.5 among candidates that met the recall floor.

## 2. Final Model Evaluation

The held-out test set contained **24,000** trips with the same **8.78%** long-trip rate as the full modeling sample. A most-frequent baseline still appears accurate because most trips are short, but it fails the real business objective: it never predicts a long trip. The baseline reached **91.22% accuracy** with **0.00 precision**, **0.00 recall**, and **0.00 F1** for the long-trip class.

The Day 1 logistic regression reference model had strong recall but too many false positives:

| Model | Accuracy | Precision | Recall | F1 | F0.5 | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Most frequent baseline | 0.9122 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 |
| Balanced logistic regression | 0.9176 | 0.5183 | 0.8647 | 0.6482 | 0.5635 | 0.9622 |
| Optimized histogram gradient boosting | 0.9580 | 0.7954 | 0.7029 | 0.7463 | 0.7750 | 0.9745 |

The optimized model is a stronger final model for the Day 2 objective. Accuracy improved from **0.9176** to **0.9580**, precision improved from **0.5183** to **0.7954**, F1 improved from **0.6482** to **0.7463**, and ROC-AUC improved from **0.9622** to **0.9745** compared with the logistic regression reference. This means the model now makes far fewer false long-trip warnings while maintaining useful coverage of real long trips.

The final confusion matrix on the test set was:

| Outcome | Count |
|---|---:|
| True negatives | 21,512 |
| False positives | 381 |
| False negatives | 626 |
| True positives | 1,481 |

Compared with the logistic model, the optimized model reduced false positives from **1,693** to **381**. That is the main precision gain. The tradeoff is that false negatives increased from **285** to **626**, so the optimized model misses more long trips than the recall-focused logistic model. This tradeoff is acceptable for the stated Day 2 goal because the final model is intended as a practical planning signal where accuracy and precision matter. If the stakeholder later decides that missed long trips are more costly than extra alerts, the threshold can be lowered using the saved probability outputs and validation table.

Feature importance was estimated with held-out permutation importance using ROC-AUC as the scoring metric. The most important feature was `trip_distance`, which is expected because longer distances are more likely to last 30 minutes or more. Time and location features also mattered: `pickup_hour`, `DOLocationID`, `PULocationID`, and `pickup_dayofweek` were the next strongest contributors. This confirms that the final model is learning plausible transportation patterns rather than relying on a single artifact.

Generated evaluation artifacts are saved in:

- `reports/model_metrics.csv`
- `reports/metrics.json`
- `reports/tuning_results.csv`
- `reports/model_feature_importance.csv`
- `reports/figures/confusion_matrix.png`
- `reports/figures/feature_importance.png`

## 3. Ethical Considerations

This model does not use names, phone numbers, exact addresses, race, gender, or other direct personal identifiers. However, it still uses pickup and dropoff taxi zone IDs. Location data can reflect neighborhood-level patterns related to income, commuting access, airport travel, tourism, disability access, and historical service availability. Because of that, the model must be treated as a decision-support tool rather than an automated authority.

The main ethical risk is misuse. A long-trip prediction could be helpful for dispatch planning, but it could become harmful if used to discourage drivers from accepting certain trips, avoid certain neighborhoods, penalize drivers for route outcomes, or justify unequal service. The model also learns from historical taxi behavior, so it may reproduce existing patterns instead of describing what fair transportation service should look like.

The final model's higher precision reduces unnecessary long-trip warnings, but ethical evaluation cannot stop at aggregate accuracy. Future audits should measure false-positive and false-negative rates by pickup zone, dropoff zone, time of day, weekday/weekend, and airport-trip status. If errors concentrate in specific neighborhoods or time periods, the model should be revised before being used in operations. Clear documentation should also state that the probability is an estimate, not a guarantee.

## 4. Real-World Application

A practical use of this model is an operational dashboard for taxi dispatch teams, fleet managers, airport queue monitors, or city transportation analysts. Before or near the beginning of a trip, the system can estimate whether the trip is likely to last at least 30 minutes using distance, pickup hour, day of week, airport flag, vendor, rate code, and pickup/dropoff zones. The output can be shown as a probability and a long-trip flag based on the tuned threshold.

For dispatch teams, the model can help estimate when vehicles may be unavailable for longer periods. This can improve driver shift planning, airport staging, and service coverage in high-demand areas. For city analysts, aggregated long-trip predictions can help identify times and zones where congestion or long-distance travel patterns may be increasing. For customer-facing systems, the probability could support better wait-time messaging, as long as it is framed carefully and not treated as a precise duration estimate.

The model should be deployed with human oversight. A dashboard should show aggregate counts, probability bands, and uncertainty rather than only a hard yes/no label. For example, trips could be grouped as low, medium, or high long-trip risk. Dispatchers could use those signals to plan coverage, but the system should not automatically deny service, change driver pay, or rank neighborhoods. The tuned threshold of **0.80** is appropriate for the current precision-focused objective, but it should be revisited if business priorities change.

The current pipeline is reproducible and collaboration-ready. It uses pandas and NumPy for data manipulation, Matplotlib and Seaborn for visualization, scikit-learn for modeling and evaluation, Google Colab-compatible notebooks for collaboration, and GitHub for version control. Dask remains optional for future scaling if the team expands from a 120,000-row modeling sample to multiple months or full-year training.

Operational deployment would require several additional steps. First, the model should be validated on months beyond January 2024 to check seasonality and drift. Second, probability calibration should be tested so probability values can be trusted for dashboard bands. Third, subgroup error monitoring should be added by zone and time period. Fourth, model retraining should be scheduled when travel patterns change due to weather, holidays, construction, major events, or policy changes.

## 5. Final Thoughts and Conclusion

Deliverable 2 improved the model from an interpretable recall-focused baseline into a stronger optimized classifier. The final histogram gradient boosting model achieved **95.80% accuracy**, **79.54% precision**, **70.29% recall**, **74.63% F1**, and **97.45% ROC-AUC** on the held-out test set. The biggest practical improvement was precision: the model now produces far fewer false long-trip alerts than the Day 1 logistic regression model.

The project also shows why optimization is not only about raising one metric. The selected threshold improved precision and accuracy, but it reduced recall compared with logistic regression. That tradeoff is acceptable for this deliverable because the objective emphasized accuracy and precision. In a different operational setting, the threshold could be adjusted to catch more long trips at the cost of more false alerts.

The final recommendation is to use this model for aggregate planning, not automated service decisions. It can help teams anticipate long-trip pressure, understand transportation patterns, and plan resources more effectively. Future work should validate the model across multiple months, add contextual data such as weather and events, calibrate probabilities, and run fairness/error audits by zone and time. With those safeguards, the model can become a useful real-world analytics tool while respecting the ethical limits of transportation prediction.
