"""Build an initial NYC taxi long-trip risk model.

The pipeline downloads the official NYC TLC yellow taxi parquet file, cleans
trip records, creates features, trains an interpretable classifier, and writes
figures/metrics for the assignment report.
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    fbeta_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_URL = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data/"
    "yellow_tripdata_2024-01.parquet"
)
DEFAULT_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "yellow_tripdata_2024-01.parquet"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models"
RANDOM_STATE = 42

RAW_COLUMNS = [
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "Airport_fee",
]

NUMERIC_FEATURES = [
    "trip_distance",
    "passenger_count",
    "pickup_hour",
    "pickup_dayofweek",
    "is_weekend",
    "airport_trip",
]

CATEGORICAL_FEATURES = [
    "VendorID",
    "RatecodeID",
    "PULocationID",
    "DOLocationID",
]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "long_trip"
INITIAL_MODEL_NAME = "Balanced logistic regression"
FINAL_MODEL_NAME = "Optimized histogram gradient boosting"
DECISION_RECALL_FLOOR = 0.865
DECISION_BETA = 0.5

HGB_TUNING_CANDIDATES: list[dict[str, Any]] = [
    {
        "candidate": "hgb_depth31_weight4",
        "max_iter": 250,
        "learning_rate": 0.06,
        "max_leaf_nodes": 31,
        "l2_regularization": 0.0,
        "class_weight": {0: 1, 1: 4},
    },
    {
        "candidate": "hgb_depth63_weight4",
        "max_iter": 300,
        "learning_rate": 0.05,
        "max_leaf_nodes": 63,
        "l2_regularization": 0.01,
        "class_weight": {0: 1, 1: 4},
    },
    {
        "candidate": "hgb_depth31_balanced",
        "max_iter": 300,
        "learning_rate": 0.05,
        "max_leaf_nodes": 31,
        "l2_regularization": 0.1,
        "class_weight": "balanced",
    },
    {
        "candidate": "hgb_depth63_weight6",
        "max_iter": 200,
        "learning_rate": 0.08,
        "max_leaf_nodes": 63,
        "l2_regularization": 0.1,
        "class_weight": {0: 1, 1: 6},
    },
    {
        "candidate": "hgb_depth31_weight3",
        "max_iter": 400,
        "learning_rate": 0.03,
        "max_leaf_nodes": 31,
        "l2_regularization": 0.01,
        "class_weight": {0: 1, 1: 3},
    },
]

# TLC location IDs for Newark, JFK, and LaGuardia airport zones.
AIRPORT_ZONE_IDS = {1, 132, 138}


@dataclass(frozen=True)
class PipelineConfig:
    data_url: str
    raw_path: Path
    report_dir: Path
    model_dir: Path
    sample_size: int
    force_download: bool


def download_file(url: str, output_path: Path, force: bool = False) -> Path:
    """Download a file unless it already exists locally."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not force:
        return output_path

    def report_hook(block_num: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size)
        if block_num % 100 == 0 or math.isclose(percent, 100):
            print(f"Downloading data: {percent:5.1f}%")

    urllib.request.urlretrieve(url, output_path, reporthook=report_hook)
    return output_path


def load_raw_data(path: Path) -> pd.DataFrame:
    """Read only the columns needed for this assignment."""
    return pd.read_parquet(path, columns=RAW_COLUMNS)


def _audit_filter(
    df: pd.DataFrame,
    mask: pd.Series,
    step: str,
    description: str,
    audit_rows: list[dict[str, Any]],
    raw_rows: int,
) -> pd.DataFrame:
    """Apply one preprocessing filter and record its row impact."""
    rows_before = len(df)
    filtered = df.loc[mask].copy()
    rows_after = len(filtered)
    audit_rows.append(
        {
            "step": step,
            "description": description,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "rows_removed": rows_before - rows_after,
            "step_removed_pct": round(
                ((rows_before - rows_after) / rows_before) * 100, 4
            )
            if rows_before
            else 0.0,
            "retained_pct_of_raw": round((rows_after / raw_rows) * 100, 4)
            if raw_rows
            else 0.0,
        }
    )
    return filtered


def preprocess_with_audit(
    raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Clean TLC records, create modeling features, and document each change."""
    df = raw.copy()
    raw_rows = len(df)
    audit_rows: list[dict[str, Any]] = [
        {
            "step": "01_raw_load",
            "description": "Loaded selected NYC TLC yellow taxi columns from parquet.",
            "rows_before": raw_rows,
            "rows_after": raw_rows,
            "rows_removed": 0,
            "step_removed_pct": 0.0,
            "retained_pct_of_raw": 100.0,
        }
    ]

    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    df["trip_duration_min"] = (
        df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]
    ).dt.total_seconds() / 60
    audit_rows.append(
        {
            "step": "02_derive_duration",
            "description": "Converted pickup/dropoff timestamps and created trip_duration_min.",
            "rows_before": len(df),
            "rows_after": len(df),
            "rows_removed": 0,
            "step_removed_pct": 0.0,
            "retained_pct_of_raw": round((len(df) / raw_rows) * 100, 4),
        }
    )

    df = _audit_filter(
        df,
        (df["tpep_pickup_datetime"] >= "2024-01-01")
        & (df["tpep_pickup_datetime"] < "2024-02-01"),
        "03_filter_pickup_month",
        "Kept trips with pickup timestamps in January 2024.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["trip_duration_min"].between(1, 180),
        "04_filter_duration",
        "Removed trips shorter than 1 minute or longer than 180 minutes.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["trip_distance"].between(0.1, 60),
        "05_filter_distance",
        "Removed trips with zero, near-zero, negative, or extreme distances.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["passenger_count"].between(1, 6),
        "06_filter_passengers",
        "Kept trips with passenger_count from 1 to 6.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["fare_amount"] > 0,
        "07_filter_positive_fare",
        "Removed trips with non-positive fare_amount.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["total_amount"] > 0,
        "08_filter_positive_total",
        "Removed trips with non-positive total_amount.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["RatecodeID"].between(1, 6),
        "09_filter_standard_ratecode",
        "Kept standard TLC rate codes 1 through 6.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["PULocationID"].between(1, 265),
        "10_filter_pickup_zone",
        "Kept valid TLC pickup location IDs from 1 to 265.",
        audit_rows,
        raw_rows,
    )
    df = _audit_filter(
        df,
        df["DOLocationID"].between(1, 265),
        "11_filter_dropoff_zone",
        "Kept valid TLC dropoff location IDs from 1 to 265.",
        audit_rows,
        raw_rows,
    )

    df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour
    df["pickup_dayofweek"] = df["tpep_pickup_datetime"].dt.dayofweek
    df["is_weekend"] = df["pickup_dayofweek"].isin([5, 6]).astype(int)
    df["airport_trip"] = (
        df["PULocationID"].isin(AIRPORT_ZONE_IDS)
        | df["DOLocationID"].isin(AIRPORT_ZONE_IDS)
    ).astype(int)
    df[TARGET] = (df["trip_duration_min"] >= 30).astype(int)

    for column in CATEGORICAL_FEATURES:
        df[column] = df[column].astype("Int64").astype(str)

    audit_rows.append(
        {
            "step": "12_feature_engineering",
            "description": "Created time, weekend, airport, target, and categorical model fields.",
            "rows_before": len(df),
            "rows_after": len(df),
            "rows_removed": 0,
            "step_removed_pct": 0.0,
            "retained_pct_of_raw": round((len(df) / raw_rows) * 100, 4),
        }
    )

    feature_rows = [
        {
            "column": "trip_duration_min",
            "type": "derived numeric",
            "source": "tpep_dropoff_datetime - tpep_pickup_datetime",
            "purpose": "Used for cleaning and to create the long_trip target; not used as a model input.",
        },
        {
            "column": "pickup_hour",
            "type": "derived numeric",
            "source": "hour from tpep_pickup_datetime",
            "purpose": "Captures daily travel and congestion cycles.",
        },
        {
            "column": "pickup_dayofweek",
            "type": "derived numeric",
            "source": "day of week from tpep_pickup_datetime, Monday=0",
            "purpose": "Captures weekday/weekend and commute-pattern differences.",
        },
        {
            "column": "is_weekend",
            "type": "derived binary",
            "source": "pickup_dayofweek in Saturday or Sunday",
            "purpose": "Flags weekend operating patterns.",
        },
        {
            "column": "airport_trip",
            "type": "derived binary",
            "source": "pickup or dropoff zone in Newark, JFK, or LaGuardia TLC IDs",
            "purpose": "Flags trips involving major airport zones.",
        },
        {
            "column": TARGET,
            "type": "target binary",
            "source": "trip_duration_min >= 30",
            "purpose": "Prediction target: 1 for long trips, 0 otherwise.",
        },
        {
            "column": ", ".join(CATEGORICAL_FEATURES),
            "type": "converted categorical",
            "source": "integer IDs converted to strings",
            "purpose": "Prevents ID values from being treated as ordered numeric quantities.",
        },
    ]

    return df, pd.DataFrame(audit_rows), pd.DataFrame(feature_rows)


def clean_and_engineer_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean TLC records and create modeling features."""
    df, _, _ = preprocess_with_audit(raw)
    return df


def make_logistic_model() -> Pipeline:
    """Create the initial interpretable logistic classification pipeline."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", min_frequency=50),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )
    classifier = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=RANDOM_STATE,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", classifier)])


def make_hist_gradient_boosting_model(params: dict[str, Any]) -> Pipeline:
    """Create the optimized model family used during hyperparameter tuning."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "ordinal",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        verbose_feature_names_out=False,
    )
    categorical_indices = list(range(len(NUMERIC_FEATURES), len(FEATURES)))
    model_params = {key: value for key, value in params.items() if key != "candidate"}
    classifier = HistGradientBoostingClassifier(
        categorical_features=categorical_indices,
        random_state=RANDOM_STATE,
        **model_params,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", classifier)])


def make_model() -> Pipeline:
    """Create the default optimized classification pipeline."""
    return make_hist_gradient_boosting_model(HGB_TUNING_CANDIDATES[1])


def evaluate_predictions(
    y_true: pd.Series,
    y_pred: np.ndarray,
    y_score: np.ndarray,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Calculate core classification metrics."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "f0_5": round(
            float(fbeta_score(y_true, y_pred, beta=0.5, zero_division=0)),
            4,
        ),
        "roc_auc": round(float(roc_auc_score(y_true, y_score)), 4),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }
    if threshold is not None:
        metrics["decision_threshold"] = round(float(threshold), 4)
    return metrics


def threshold_search(
    y_true: pd.Series,
    y_score: np.ndarray,
    recall_floor: float = DECISION_RECALL_FLOOR,
    beta: float = DECISION_BETA,
) -> tuple[float, pd.DataFrame]:
    """Choose a probability threshold on validation data."""
    rows: list[dict[str, Any]] = []
    for threshold in np.round(np.arange(0.05, 0.951, 0.01), 2):
        y_pred = (y_score >= threshold).astype(int)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        rows.append(
            {
                "threshold": float(threshold),
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1_score(y_true, y_pred, zero_division=0)),
                "f0_5": float(
                    fbeta_score(y_true, y_pred, beta=beta, zero_division=0)
                ),
                "predicted_positive_rate": float(np.mean(y_pred)),
            }
        )

    threshold_frame = pd.DataFrame(rows)
    feasible = threshold_frame[threshold_frame["recall"] >= recall_floor]
    selection_frame = feasible if not feasible.empty else threshold_frame
    selected = selection_frame.sort_values(
        ["f0_5", "accuracy", "precision"],
        ascending=[False, False, False],
    ).iloc[0]
    return float(selected["threshold"]), threshold_frame


def tune_hist_gradient_boosting(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_validation: pd.DataFrame,
    y_validation: pd.Series,
) -> tuple[Pipeline, float, dict[str, Any], pd.DataFrame]:
    """Tune gradient boosting hyperparameters and decision threshold."""
    tuning_rows: list[dict[str, Any]] = []
    best_model: Pipeline | None = None
    best_threshold = 0.5
    best_candidate: dict[str, Any] | None = None
    best_score_key = (-np.inf, -np.inf, -np.inf)

    for candidate in HGB_TUNING_CANDIDATES:
        model = make_hist_gradient_boosting_model(candidate)
        model.fit(x_train, y_train)
        validation_score = model.predict_proba(x_validation)[:, 1]
        threshold, _ = threshold_search(y_validation, validation_score)
        validation_pred = (validation_score >= threshold).astype(int)
        metrics = evaluate_predictions(
            y_validation,
            validation_pred,
            validation_score,
            threshold=threshold,
        )
        row = {
            "candidate": candidate["candidate"],
            "model": FINAL_MODEL_NAME,
            "selected_threshold": round(float(threshold), 4),
            "max_iter": candidate["max_iter"],
            "learning_rate": candidate["learning_rate"],
            "max_leaf_nodes": candidate["max_leaf_nodes"],
            "l2_regularization": candidate["l2_regularization"],
            "class_weight": json.dumps(candidate["class_weight"]),
            "selection_metric": "validation_f0_5_with_recall_floor",
            "validation_recall_floor": DECISION_RECALL_FLOOR,
            **{f"validation_{key}": value for key, value in metrics.items()},
        }
        tuning_rows.append(row)
        score_key = (
            metrics["f0_5"],
            metrics["accuracy"],
            metrics["precision"],
        )
        if score_key > best_score_key:
            best_score_key = score_key
            best_model = model
            best_threshold = threshold
            best_candidate = candidate

    if best_model is None or best_candidate is None:
        raise RuntimeError("No tuned model candidate was selected.")

    tuning_frame = pd.DataFrame(tuning_rows)
    tuning_frame["selected"] = tuning_frame["candidate"] == best_candidate["candidate"]
    return best_model, best_threshold, best_candidate, tuning_frame


def coefficient_summary(model: Pipeline) -> pd.DataFrame:
    """Return sorted feature coefficients from the fitted logistic model."""
    preprocessor = model.named_steps["preprocess"]
    classifier = model.named_steps["model"]
    feature_names = preprocessor.get_feature_names_out()
    coefficients = classifier.coef_.ravel()
    frame = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
            "absolute_coefficient": np.abs(coefficients),
        }
    )
    frame["feature"] = (
        frame["feature"]
        .str.replace("num__", "", regex=False)
        .str.replace("cat__", "", regex=False)
        .str.replace("onehot__", "", regex=False)
    )
    frame["direction"] = np.where(
        frame["coefficient"] >= 0,
        "Higher long-trip risk",
        "Lower long-trip risk",
    )
    return frame.sort_values("absolute_coefficient", ascending=False)


def feature_importance_summary(
    model: Pipeline,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    max_rows: int = 15_000,
) -> pd.DataFrame:
    """Estimate final model feature importance with held-out permutation tests."""
    if len(x_test) > max_rows:
        x_importance = x_test.sample(n=max_rows, random_state=RANDOM_STATE)
        y_importance = y_test.loc[x_importance.index]
    else:
        x_importance = x_test
        y_importance = y_test

    result = permutation_importance(
        model,
        x_importance,
        y_importance,
        scoring="roc_auc",
        n_repeats=5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    frame = pd.DataFrame(
        {
            "feature": list(x_importance.columns),
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
            "scoring": "roc_auc",
        }
    )
    return frame.sort_values("importance_mean", ascending=False)


def create_figures(
    df: pd.DataFrame,
    model: Pipeline,
    y_test: pd.Series,
    y_pred: np.ndarray,
    feature_importance: pd.DataFrame,
    report_dir: Path,
    initial_model: Pipeline | None = None,
) -> None:
    """Create EDA and model evaluation figures."""
    figure_dir = report_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(8, 5))
    sns.histplot(df["trip_duration_min"], bins=60, color="#2f6f73")
    plt.axvline(30, color="#c03a2b", linestyle="--", label="30-minute threshold")
    plt.title("Distribution of Cleaned Trip Duration")
    plt.xlabel("Trip duration (minutes)")
    plt.ylabel("Trips")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figure_dir / "duration_distribution.png", dpi=180)
    plt.close()

    plot_sample = df.sample(n=min(len(df), 20000), random_state=RANDOM_STATE)
    plt.figure(figsize=(8, 5))
    sns.scatterplot(
        data=plot_sample,
        x="trip_distance",
        y="trip_duration_min",
        hue=TARGET,
        alpha=0.35,
        palette={0: "#5677a6", 1: "#d1683c"},
        linewidth=0,
    )
    plt.title("Trip Distance vs. Duration")
    plt.xlabel("Trip distance (miles)")
    plt.ylabel("Trip duration (minutes)")
    plt.tight_layout()
    plt.savefig(figure_dir / "distance_vs_duration.png", dpi=180)
    plt.close()

    hourly = (
        df.groupby("pickup_hour", as_index=False)[TARGET]
        .mean()
        .rename(columns={TARGET: "long_trip_rate"})
    )
    plt.figure(figsize=(8, 5))
    sns.lineplot(
        data=hourly,
        x="pickup_hour",
        y="long_trip_rate",
        marker="o",
        color="#234f68",
    )
    plt.title("Long-Trip Rate by Pickup Hour")
    plt.xlabel("Pickup hour")
    plt.ylabel("Share of trips lasting at least 30 minutes")
    plt.ylim(0, max(0.4, hourly["long_trip_rate"].max() + 0.03))
    plt.tight_layout()
    plt.savefig(figure_dir / "hourly_long_trip_rate.png", dpi=180)
    plt.close()

    cm = confusion_matrix(y_test, y_pred)
    display = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=["Under 30 min", "30+ min"],
    )
    display.plot(cmap="Blues", values_format="d")
    plt.title("Optimized Model Confusion Matrix")
    plt.tight_layout()
    plt.savefig(figure_dir / "confusion_matrix.png", dpi=180)
    plt.close()

    positive_importance = feature_importance[feature_importance["importance_mean"] > 0]
    importance_frame = positive_importance.head(10).sort_values(
        "importance_mean",
        ascending=True,
    )
    plt.figure(figsize=(9, 5.5))
    sns.barplot(
        data=importance_frame,
        y="feature",
        x="importance_mean",
        color="#2f6f73",
    )
    plt.title("Optimized Model Feature Importance")
    plt.xlabel("Mean ROC-AUC decrease after permutation")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(figure_dir / "feature_importance.png", dpi=180)
    plt.close()

    if initial_model is None:
        return

    coefficient_frame = coefficient_summary(initial_model).head(15)
    plt.figure(figsize=(9, 6))
    sns.barplot(
        data=coefficient_frame,
        y="feature",
        x="coefficient",
        hue="direction",
        dodge=False,
        palette={
            "Higher long-trip risk": "#d1683c",
            "Lower long-trip risk": "#5677a6",
        },
    )
    plt.axvline(0, color="black", linewidth=0.8)
    plt.title("Initial Logistic Regression Coefficients")
    plt.xlabel("Standardized coefficient")
    plt.ylabel("")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(figure_dir / "top_coefficients.png", dpi=180)
    plt.close()


def write_outputs(
    df: pd.DataFrame,
    raw_rows: int,
    clean_rows_before_sampling: int,
    preprocessing_audit: pd.DataFrame,
    feature_summary: pd.DataFrame,
    split_summary: dict[str, Any],
    baseline_metrics: dict[str, Any],
    initial_metrics: dict[str, Any],
    final_metrics: dict[str, Any],
    selected_candidate: dict[str, Any],
    final_threshold: float,
    tuning_results: pd.DataFrame,
    report: str,
    final_model: Pipeline,
    initial_model: Pipeline,
    feature_importance: pd.DataFrame,
    report_dir: Path,
    model_dir: Path,
) -> None:
    """Persist metrics, feature notes, and the trained model."""
    report_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "dataset": {
            "source": DEFAULT_DATA_URL,
            "raw_rows": int(raw_rows),
            "clean_rows_before_sampling": int(clean_rows_before_sampling),
            "model_sample_rows": int(len(df)),
            "long_trip_rate": round(float(df[TARGET].mean()), 4),
            "median_duration_min": round(float(df["trip_duration_min"].median()), 2),
            "median_distance_miles": round(float(df["trip_distance"].median()), 2),
        },
        "target_distribution": {
            "under_30_min": int((df[TARGET] == 0).sum()),
            "long_30_plus_min": int((df[TARGET] == 1).sum()),
            "long_trip_rate": round(float(df[TARGET].mean()), 4),
        },
        "model_inputs": {
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "target": TARGET,
            "positive_class": "long_trip = 1 means trip duration is at least 30 minutes",
        },
        "train_test_split": split_summary,
        "model_optimization": {
            "selected_model": FINAL_MODEL_NAME,
            "selected_candidate": selected_candidate,
            "decision_threshold": round(float(final_threshold), 4),
            "selection_metric": (
                f"validation F0.5 with recall >= {DECISION_RECALL_FLOOR:.3f}"
            ),
            "reason": (
                "F0.5 emphasizes precision while the higher recall floor keeps "
                "long-trip recall above the Day 1 logistic reference."
            ),
        },
        "baseline_most_frequent": baseline_metrics,
        "initial_logistic_regression": initial_metrics,
        "logistic_regression": initial_metrics,
        "optimized_hist_gradient_boosting": final_metrics,
        "optimized_model": final_metrics,
        "classification_report": report,
    }

    with (report_dir / "metrics.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    preprocessing_audit.to_csv(report_dir / "preprocessing_audit.csv", index=False)
    feature_summary.to_csv(report_dir / "feature_engineering_summary.csv", index=False)
    tuning_results.to_csv(report_dir / "tuning_results.csv", index=False)

    pd.DataFrame(
        [
            {"model": "Most frequent baseline", **baseline_metrics},
            {"model": INITIAL_MODEL_NAME, **initial_metrics},
            {"model": FINAL_MODEL_NAME, **final_metrics},
        ]
    ).to_csv(report_dir / "model_metrics.csv", index=False)

    pd.DataFrame(
        [
            {
                "target_value": 0,
                "label": "Under 30 minutes",
                "rows": int((df[TARGET] == 0).sum()),
                "share": round(float((df[TARGET] == 0).mean()), 4),
            },
            {
                "target_value": 1,
                "label": "30+ minutes",
                "rows": int((df[TARGET] == 1).sum()),
                "share": round(float((df[TARGET] == 1).mean()), 4),
            },
        ]
    ).to_csv(report_dir / "target_distribution.csv", index=False)

    coefficient_summary(initial_model).to_csv(
        report_dir / "model_coefficients.csv",
        index=False,
    )
    feature_importance.to_csv(report_dir / "model_feature_importance.csv", index=False)
    joblib.dump(final_model, model_dir / "long_trip_optimized_model.joblib")


def run_pipeline(config: PipelineConfig) -> dict[str, Any]:
    raw_path = download_file(config.data_url, config.raw_path, config.force_download)
    raw = load_raw_data(raw_path)
    raw_rows = len(raw)
    df, preprocessing_audit, feature_summary = preprocess_with_audit(raw)
    clean_rows = len(df)
    if config.sample_size and len(df) > config.sample_size:
        rows_before_sample = len(df)
        df = df.sample(n=config.sample_size, random_state=RANDOM_STATE)
        preprocessing_audit = pd.concat(
            [
                preprocessing_audit,
                pd.DataFrame(
                    [
                        {
                            "step": "13_model_sample",
                            "description": (
                                "Selected deterministic modeling sample with "
                                f"random_state={RANDOM_STATE}."
                            ),
                            "rows_before": rows_before_sample,
                            "rows_after": len(df),
                            "rows_removed": rows_before_sample - len(df),
                            "step_removed_pct": round(
                                ((rows_before_sample - len(df)) / rows_before_sample)
                                * 100,
                                4,
                            ),
                            "retained_pct_of_raw": round((len(df) / raw_rows) * 100, 4),
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    x = df[FEATURES]
    y = df[TARGET]
    x_development, x_test, y_development, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    x_train, x_validation, y_train, y_validation = train_test_split(
        x_development,
        y_development,
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=y_development,
    )
    split_summary = {
        "split_method": "60/20/20 stratified train-validation-test split",
        "random_state": RANDOM_STATE,
        "train_rows": int(len(x_train)),
        "validation_rows": int(len(x_validation)),
        "test_rows": int(len(x_test)),
        "train_long_trip_rate": round(float(y_train.mean()), 4),
        "validation_long_trip_rate": round(float(y_validation.mean()), 4),
        "test_long_trip_rate": round(float(y_test.mean()), 4),
    }

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(x_train, y_train)
    baseline_pred = baseline.predict(x_test)
    baseline_score = np.repeat(y_train.mean(), repeats=len(y_test))
    baseline_metrics = evaluate_predictions(y_test, baseline_pred, baseline_score)

    initial_model = make_logistic_model()
    initial_model.fit(x_train, y_train)
    initial_score = initial_model.predict_proba(x_test)[:, 1]
    initial_pred = (initial_score >= 0.5).astype(int)
    initial_metrics = evaluate_predictions(
        y_test,
        initial_pred,
        initial_score,
        threshold=0.5,
    )

    final_model, final_threshold, selected_candidate, tuning_results = (
        tune_hist_gradient_boosting(x_train, y_train, x_validation, y_validation)
    )
    y_score = final_model.predict_proba(x_test)[:, 1]
    y_pred = (y_score >= final_threshold).astype(int)
    final_metrics = evaluate_predictions(
        y_test,
        y_pred,
        y_score,
        threshold=final_threshold,
    )

    report = classification_report(
        y_test,
        y_pred,
        target_names=["Under 30 min", "30+ min"],
        digits=4,
    )
    feature_importance = feature_importance_summary(final_model, x_test, y_test)
    create_figures(
        df,
        final_model,
        y_test,
        y_pred,
        feature_importance,
        config.report_dir,
        initial_model=initial_model,
    )
    write_outputs(
        df,
        raw_rows,
        clean_rows,
        preprocessing_audit,
        feature_summary,
        split_summary,
        baseline_metrics,
        initial_metrics,
        final_metrics,
        selected_candidate,
        final_threshold,
        tuning_results,
        report,
        final_model,
        initial_model,
        feature_importance,
        config.report_dir,
        config.model_dir,
    )
    return {
        "raw_rows": raw_rows,
        "clean_rows_before_sampling": clean_rows,
        "sample_rows": len(df),
        "long_trip_rate": round(float(df[TARGET].mean()), 4),
        "initial_metrics": initial_metrics,
        "optimized_metrics": final_metrics,
        "baseline_metrics": baseline_metrics,
        "selected_candidate": selected_candidate["candidate"],
        "decision_threshold": round(float(final_threshold), 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-url", default=DEFAULT_DATA_URL)
    parser.add_argument("--raw-path", type=Path, default=DEFAULT_RAW_PATH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--sample-size", type=int, default=120_000)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PipelineConfig(
        data_url=args.data_url,
        raw_path=args.raw_path,
        report_dir=args.report_dir,
        model_dir=args.model_dir,
        sample_size=args.sample_size,
        force_download=args.force_download,
    )
    result = run_pipeline(config)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
