# Real-World AI-Driven Analytics Solution Using Python

## Project Title

Predicting Long NYC Yellow Taxi Trips for Dispatch and Congestion-Aware Planning

## 1. Introduction and Problem Framing

New York City taxi service is a high-volume transportation system where trip duration affects driver availability, passenger expectations, airport queues, congestion, and shift planning. The stakeholder problem for this project is: **Can a taxi operator or city transportation analyst estimate whether a yellow taxi trip is likely to last at least 30 minutes using structured trip information?**

This is a real-world business and societal problem because long trips change how quickly vehicles return to dense pickup areas and how accurately riders can be told what to expect. A long-trip risk estimate can help dispatch teams plan coverage, identify time periods with heavier congestion pressure, and improve operational dashboards. The output should be used as decision support, not as a reason to deny trips or deprioritize neighborhoods.

The analytics goal is a binary classification task. The target variable is `long_trip`, where `1` means the cleaned trip duration is at least 30 minutes and `0` means it is below 30 minutes. I chose this target because it is easy for nontechnical stakeholders to understand and because recall matters: missing too many long trips would reduce the usefulness of the tool for staffing and service planning.

## 2. Dataset Exploration and Preprocessing

The project uses the official NYC Taxi and Limousine Commission Yellow Taxi Trip Record data for January 2024. The data source is the NYC TLC public trip record page, and the pipeline downloads the parquet file directly from the official TLC cloudfront host:

- Dataset page: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- File used: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
- Data dictionary: https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf

The raw file contains **2,964,624** yellow taxi trip records. To keep the project reproducible while still realistic, the script reads the official parquet file, cleans the full month, and then uses a deterministic **120,000-row** modeling sample with `random_state=42`. Before sampling, preprocessing retained **2,684,599** realistic trips.

Important raw fields included pickup and dropoff timestamps, passenger count, trip distance, pickup and dropoff location IDs, rate code, fare fields, payment type, and total amount. The model intentionally avoids using the target itself or post-outcome leakage such as calculated trip duration as an input feature. The final model features are:

- Numeric: `trip_distance`, `passenger_count`, `pickup_hour`, `pickup_dayofweek`, `is_weekend`, `airport_trip`
- Categorical: `VendorID`, `RatecodeID`, `PULocationID`, `DOLocationID`

Several cleaning rules were applied to remove records that would mislead the model or reflect data-entry artifacts rather than normal service. Trips were kept only if the pickup time occurred in January 2024, duration was between 1 and 180 minutes, distance was between 0.1 and 60 miles, passenger count was between 1 and 6, fare and total amount were positive, pickup/dropoff location IDs were valid TLC zone IDs, and rate code was a standard value from 1 to 6. This last rule was added after exploratory review showed that a nonstandard rate code was dominating coefficients, which was a warning sign that the model could learn an artifact rather than a transport pattern.

Feature engineering converted timestamps into operationally useful time features. `pickup_hour` captures daily demand cycles, `pickup_dayofweek` and `is_weekend` capture commuting and weekend differences, and `airport_trip` identifies trips involving Newark, JFK, or LaGuardia TLC zones. The target label was then created from cleaned trip duration: trips at least 30 minutes long were labeled `1`.

Exploratory analysis showed the cleaned sample is strongly imbalanced. Only **8.78%** of sampled trips were long trips. The median trip duration was **11.6 minutes**, and the median trip distance was **1.7 miles**. Because most trips are short, accuracy alone is a weak metric: a naive model can predict "not long" for every trip and still look accurate. For that reason, the evaluation focuses on recall, F1 score, and ROC-AUC in addition to accuracy.

Generated visualizations are stored in `reports/figures/`:

- `duration_distribution.png`: distribution of cleaned trip duration with the 30-minute threshold
- `distance_vs_duration.png`: relationship between distance, duration, and target class
- `hourly_long_trip_rate.png`: long-trip share by pickup hour
- `confusion_matrix.png`: held-out test-set performance
- `top_coefficients.png`: most influential model coefficients

## 3. Initial Model Development

The initial AI model is a **class-balanced logistic regression classifier** implemented with scikit-learn. I chose logistic regression because it is fast, reproducible, and more explainable than a black-box model. Since this is an early-stage analytics solution for operational stakeholders, interpretability is valuable: the team can explain why the model produces higher or lower long-trip risk instead of only reporting predictions.

The model pipeline uses a `ColumnTransformer`. Numeric fields are median-imputed and standardized. Categorical fields are imputed with the most frequent value and one-hot encoded with `handle_unknown="ignore"` so the model can safely process future trips containing categories not seen during training. The data is split into an 80% training set and a 20% held-out test set using stratification so the long-trip rate is preserved in both sets.

The baseline model is a most-frequent classifier. Because long trips are uncommon, this baseline predicts every test trip as under 30 minutes. It reaches **91.22% accuracy**, but it has **0.00 recall** and **0.00 F1** for long trips. This confirms why accuracy is not enough for this problem.

The balanced logistic regression model produced the following test-set results:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Most frequent baseline | 0.9122 | 0.0000 | 0.0000 | 0.0000 | 0.5000 |
| Balanced logistic regression | 0.9170 | 0.5162 | 0.8624 | 0.6458 | 0.9627 |

The model improves the assignment-relevant outcome because it identifies most long trips instead of ignoring the minority class. Recall of **86.24%** means the model catches most 30-minute-plus trips in the held-out test set. Precision of **51.62%** means that about half of predicted long trips are actually long, which is acceptable for an early warning signal but not enough for high-stakes automated decisions.

The most influential coefficient is `trip_distance`, which has the strongest positive relationship with long-trip risk. Location features also matter, showing that pickup and dropoff zones carry information about likely duration. This is useful operationally, but it creates an ethical caution: location can act as a proxy for neighborhood, income, airport access, or commuting patterns. Therefore, this model should support aggregate planning and human review, not individual service exclusion.

Recommended next iterations are to validate the model on multiple months, add weather and event data, compare with tree-based models, calibrate predicted probabilities, and evaluate performance by borough or taxi zone to check whether errors concentrate unfairly in specific neighborhoods.

## 4. Team Collaboration Process

The project was organized as a small analytics team workflow. One role focused on stakeholder framing and ethical risk, one on data engineering and preprocessing, one on model development, and one on report quality assurance. GitHub was used as the version-control system, with a feature branch for the NYC taxi analytics implementation and clear tracked deliverables for code, report, metrics, and generated figures.

The collaboration process followed an iterative lifecycle. First, the team selected NYC Taxi data because it matched the transportation dataset option and had enough size and complexity for meaningful preprocessing. Second, the data pipeline was built to download the official file instead of relying on a manually copied dataset. Third, exploratory outputs were reviewed before finalizing cleaning rules. The nonstandard `RatecodeID` issue was caught during coefficient review, and preprocessing was updated to keep only standard rate codes. Finally, the report was written from the actual model metrics so the narrative matched the reproducible outputs.

For Google Colab collaboration, teammates can clone the repository, install `requirements.txt`, and run `src/nyc_taxi_long_trip_model.py`. The repository avoids committing large raw data files, which keeps GitHub clean while making the analysis reproducible from the public TLC source.

## Ethical Reflection

This model does not use rider names, exact addresses, race, gender, or other direct personal identifiers. However, transportation location data still has ethical risk because pickup and dropoff zones can reveal patterns about neighborhoods and access to mobility. A model trained on historical trips can also reproduce historical service patterns rather than an ideal public-service objective.

The safest use is aggregate planning: estimating when and where long trips may affect vehicle availability. The model should not be used to reject rides, discourage service to specific areas, punish drivers, or set prices without additional fairness review. Future versions should include subgroup error analysis by zone and time period, monitor model drift, and document limitations clearly for decision-makers.
