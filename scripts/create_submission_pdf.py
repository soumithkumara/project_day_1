from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
REPORTS = ROOT / "reports"
SRC = ROOT / "src"
NOTEBOOKS = ROOT / "notebooks"
OUTPUT_PDF = OUTPUT_DIR / "NYC_Taxi_AI_Analytics_Submission_Guide.pdf"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("&", "&amp;"), style)


def bullets(items: list[str], style: ParagraphStyle) -> KeepTogether:
    return KeepTogether([para("- " + item, style) for item in items])


def make_table(data: list[list[str]], widths: list[float], font_size: int = 8) -> Table:
    table = Table(data, colWidths=[w * inch for w in widths], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#203864")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#A6A6A6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
            ]
        )
    )
    return table


def code_block(text: str, style: ParagraphStyle, width: int = 88) -> Preformatted:
    wrapped_lines: list[str] = []
    for line in text.splitlines():
        if len(line) <= width:
            wrapped_lines.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        prefix = " " * min(indent, 12)
        wrapped_lines.extend(
            textwrap.wrap(
                line,
                width=width,
                subsequent_indent=prefix + "    ",
                replace_whitespace=False,
                drop_whitespace=False,
            )
        )
    return Preformatted("\n".join(wrapped_lines), style)


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(0.75 * inch, 0.45 * inch, "NYC Taxi AI Analytics Submission Guide")
    canvas.drawRightString(7.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def notebook_code_cells(path: Path) -> list[str]:
    notebook = load_json(path)
    cells = []
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if source.strip():
                cells.append(source)
    return cells


def add_figure(story: list, image_path: Path, caption: str, styles):
    story.append(KeepTogether([para(caption, styles["FigureCaption"]), Image(str(image_path), width=5.8 * inch, height=3.6 * inch)]))
    story.append(Spacer(1, 0.18 * inch))


def build_pdf():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = load_json(REPORTS / "metrics.json")
    audit = load_csv(REPORTS / "preprocessing_audit.csv")
    feature_summary = load_csv(REPORTS / "feature_engineering_summary.csv")
    requirements = read_text(ROOT / "requirements.txt").strip()
    main_code = read_text(SRC / "nyc_taxi_long_trip_model.py")
    prediction_cells = notebook_code_cells(NOTEBOOKS / "predict_new_taxi_trip.ipynb")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#203864"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#203864"),
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=colors.HexColor("#385623"),
            spaceBefore=10,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeSmall",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=6.5,
            leading=8,
            leftIndent=0,
            rightIndent=0,
            borderColor=colors.HexColor("#D9E2F3"),
            borderWidth=0.5,
            borderPadding=5,
            backColor=colors.HexColor("#F8FAFD"),
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FigureCaption",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#203864"),
            alignment=TA_CENTER,
            spaceAfter=4,
        )
    )

    story: list = []
    story.append(para("NYC Taxi AI Analytics Project", styles["TitleCenter"]))
    story.append(para("One-File Submission Guide: Code, Requirements, Directions, Model, and Outputs", styles["SubTitle"]))
    story.append(para("Team members: Soumith Kumar Ananthula, Varun Reddy Beesam, Vivek Doppalapudi", styles["SubTitle"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        para(
            "This PDF consolidates the repository instructions, model explanation, dependency requirements, preprocessing summary, evaluation metrics, prediction usage, and core source code for submission review.",
            styles["BodyCustom"],
        )
    )

    story.append(para("1. Project Overview", styles["H1Custom"]))
    story.append(
        para(
            "The project builds a working AI-driven analytics solution using Python and the NYC Taxi and Limousine Commission yellow taxi trip records. The model predicts whether a new taxi trip is likely to last 30 minutes or longer.",
            styles["BodyCustom"],
        )
    )
    story.append(
        bullets(
            [
                "Problem type: supervised binary classification.",
                "Prediction target: long_trip, where 1 means 30+ minutes and 0 means under 30 minutes.",
                "Model: optimized histogram gradient boosting with a tuned precision-focused threshold.",
                "Use case: operational planning for long-trip risk, not ride denial or punitive decision-making.",
                "Repository: https://github.com/soumithkumara/project_day_1",
            ],
            styles["BodyCustom"],
        )
    )

    story.append(para("2. Repository Structure", styles["H1Custom"]))
    repo_tree = """project_day_1/
|-- data/README.md
|-- notebooks/
|   |-- nyc_taxi_long_trip_model.ipynb
|   `-- predict_new_taxi_trip.ipynb
|-- reports/
|   |-- NYC_Taxi_AI_Analytics_APA7_Report.docx
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
|-- src/nyc_taxi_long_trip_model.py
|-- scripts/
|   |-- create_apa7_report_docx.py
|   `-- create_submission_pdf.py
|-- requirements.txt
`-- README.md"""
    story.append(code_block(repo_tree, styles["CodeSmall"], width=94))

    story.append(para("3. Software Requirements", styles["H1Custom"]))
    story.append(para("Install the Python dependencies below when running locally. In Colab, the notebooks verify packages and avoid unnecessary NumPy upgrades.", styles["BodyCustom"]))
    story.append(code_block(requirements, styles["CodeSmall"], width=94))

    story.append(para("4. How to Run the Main Analysis in Google Colab", styles["H1Custom"]))
    story.append(para("Use these commands in a Colab notebook if you are running from a blank session:", styles["BodyCustom"]))
    story.append(
        code_block(
            """!git clone https://github.com/soumithkumara/project_day_1.git
%cd project_day_1
!pip install -r requirements.txt
!python src/nyc_taxi_long_trip_model.py""",
            styles["CodeSmall"],
        )
    )
    story.append(para("Recommended Colab notebooks:", styles["H2Custom"]))
    story.append(
        bullets(
            [
                "notebooks/nyc_taxi_long_trip_model.ipynb - trains the model and displays preprocessing, metrics, and charts.",
                "notebooks/predict_new_taxi_trip.ipynb - loads/trains the model and predicts a new taxi trip.",
            ],
            styles["BodyCustom"],
        )
    )

    story.append(para("5. Dataset and Preprocessing Summary", styles["H1Custom"]))
    story.append(
        para(
            f"The official January 2024 yellow taxi parquet file contained {metrics['dataset']['raw_rows']:,} raw rows. After filtering invalid or unrealistic records, {metrics['dataset']['clean_rows_before_sampling']:,} rows remained. A deterministic {metrics['dataset']['model_sample_rows']:,}-row sample was used for modeling so the project runs quickly and reproducibly.",
            styles["BodyCustom"],
        )
    )
    audit_table = [["Step", "Rows removed", "Rows after"]]
    selected = {
        "03_filter_pickup_month",
        "04_filter_duration",
        "05_filter_distance",
        "06_filter_passengers",
        "07_filter_positive_fare",
        "09_filter_standard_ratecode",
        "13_model_sample",
    }
    for row in audit:
        if row["step"] in selected:
            audit_table.append(
                [
                    row["description"],
                    f"{int(row['rows_removed']):,}",
                    f"{int(row['rows_after']):,}",
                ]
            )
    story.append(make_table(audit_table, [4.5, 1.0, 1.0], font_size=7.2))
    story.append(Spacer(1, 0.12 * inch))

    story.append(para("6. Feature Engineering", styles["H1Custom"]))
    feature_table = [["Feature", "Type", "Purpose"]]
    for row in feature_summary:
        feature_table.append([row["column"], row["type"], row["purpose"]])
    story.append(make_table(feature_table, [1.6, 1.35, 3.55], font_size=7.1))

    story.append(para("7. Model Details and Metrics", styles["H1Custom"]))
    story.append(
        para(
            "The final AI model is an optimized histogram gradient boosting classifier. Numeric features are median-imputed, categorical features are ordinal-encoded, and a validation-selected probability threshold is used to predict class 0 for under 30 minutes or class 1 for 30 minutes or more.",
            styles["BodyCustom"],
        )
    )
    base = metrics["baseline_most_frequent"]
    initial = metrics["initial_logistic_regression"]
    model = metrics["optimized_hist_gradient_boosting"]
    metric_table = [
        ["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"],
        ["Most frequent baseline", f"{base['accuracy']:.4f}", f"{base['precision']:.4f}", f"{base['recall']:.4f}", f"{base['f1']:.4f}", f"{base['roc_auc']:.4f}"],
        ["Balanced logistic regression", f"{initial['accuracy']:.4f}", f"{initial['precision']:.4f}", f"{initial['recall']:.4f}", f"{initial['f1']:.4f}", f"{initial['roc_auc']:.4f}"],
        ["Optimized gradient boosting", f"{model['accuracy']:.4f}", f"{model['precision']:.4f}", f"{model['recall']:.4f}", f"{model['f1']:.4f}", f"{model['roc_auc']:.4f}"],
    ]
    story.append(make_table(metric_table, [2.0, 0.85, 0.85, 0.85, 0.75, 0.85], font_size=8))
    story.append(
        para(
            f"The optimized model uses a tuned decision threshold of {model['decision_threshold']:.2f}. It improves precision to {model['precision']:.4f} and accuracy to {model['accuracy']:.4f} while keeping recall at {model['recall']:.4f} on the held-out test set.",
            styles["BodyCustom"],
        )
    )

    story.append(para("8. How to Predict a New Taxi Trip", styles["H1Custom"]))
    story.append(para("Open notebooks/predict_new_taxi_trip.ipynb in Colab. Change the input values in the New Taxi Trip Input cell and run it. The result shows predicted_long_trip_class and long_trip_probability.", styles["BodyCustom"]))
    story.append(
        code_block(
            """# Meaning of the prediction output
predicted_long_trip_class = 0  # Under 30 minutes
predicted_long_trip_class = 1  # 30 minutes or more

# Example input fields
pickup_datetime = "2024-01-15 17:30:00"
trip_distance = 14.2
passenger_count = 2
vendor_id = 2
ratecode_id = 1
pu_location_id = 132
do_location_id = 48""",
            styles["CodeSmall"],
        )
    )

    story.append(para("9. Generated Outputs", styles["H1Custom"]))
    story.append(
        bullets(
            [
                "reports/metrics.json - dataset, target distribution, split summary, and model metrics.",
                "reports/preprocessing_audit.csv - row counts before and after each cleaning step.",
                "reports/model_metrics.csv - compact baseline, initial logistic, and optimized model table.",
                "reports/tuning_results.csv - validation hyperparameter and threshold tuning results.",
                "reports/model_feature_importance.csv - permutation importance for the optimized model.",
                "reports/model_coefficients.csv - reference coefficients from the initial logistic model.",
                "reports/figures/ - charts and confusion matrix.",
                "reports/NYC_Taxi_AI_Analytics_APA7_Report.docx - APA 7 written report.",
            ],
            styles["BodyCustom"],
        )
    )

    story.append(PageBreak())
    story.append(para("10. Key Figures", styles["H1Custom"]))
    add_figure(story, REPORTS / "figures" / "duration_distribution.png", "Figure 1. Distribution of cleaned trip duration.", styles)
    add_figure(story, REPORTS / "figures" / "hourly_long_trip_rate.png", "Figure 2. Long-trip rate by pickup hour.", styles)
    add_figure(story, REPORTS / "figures" / "confusion_matrix.png", "Figure 3. Optimized model confusion matrix.", styles)
    add_figure(story, REPORTS / "figures" / "feature_importance.png", "Figure 4. Optimized model feature importance.", styles)

    story.append(PageBreak())
    story.append(para("11. Core Prediction Notebook Code", styles["H1Custom"]))
    story.append(para("The prediction notebook contains setup, dependency verification, model creation/loading, feature construction, and new-trip prediction cells. The most important code cells are included below.", styles["BodyCustom"]))
    for idx, cell_source in enumerate(prediction_cells, start=1):
        if idx > 6:
            break
        story.append(para(f"Prediction notebook code cell {idx}", styles["H2Custom"]))
        story.append(code_block(cell_source, styles["CodeSmall"], width=94))

    story.append(PageBreak())
    story.append(para("12. Complete Main Pipeline Source Code", styles["H1Custom"]))
    story.append(para("The full training, preprocessing, evaluation, chart-generation, and artifact-writing pipeline is included below for submission review.", styles["BodyCustom"]))
    story.append(code_block(main_code, styles["CodeSmall"], width=96))

    story.append(PageBreak())
    story.append(para("13. Troubleshooting Notes", styles["H1Custom"]))
    story.append(
        bullets(
            [
                "If Colab cannot find files, run %cd /content/project_day_1 and then !git pull origin main.",
                "If preprocessing_audit.csv is missing, run !python src/nyc_taxi_long_trip_model.py.",
                "If the model file is missing, run the training pipeline; the model is generated locally as models/long_trip_optimized_model.joblib.",
                "If Colab shows a NumPy binary error, choose Runtime > Restart session and run the updated notebook from the top.",
                "Raw data and model binaries are intentionally not committed to GitHub because they are reproducible generated files.",
            ],
            styles["BodyCustom"],
        )
    )

    story.append(para("14. References", styles["H1Custom"]))
    refs = [
        "Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. Computing in Science & Engineering, 9(3), 90-95. https://doi.org/10.1109/MCSE.2007.55",
        "McKinney, W. (2010). Data structures for statistical computing in Python. Proceedings of the 9th Python in Science Conference, 56-61. https://doi.org/10.25080/Majora-92bf1922-00a",
        "New York City Taxi and Limousine Commission. (2024). TLC trip record data. https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
        "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825-2830. https://jmlr.org/papers/v12/pedregosa11a.html",
        "Waskom, M. L. (2021). Seaborn: Statistical data visualization. Journal of Open Source Software, 6(60), 3021. https://doi.org/10.21105/joss.03021",
    ]
    for ref in refs:
        story.append(para(ref, styles["BodyCustom"]))

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="NYC Taxi AI Analytics Submission Guide",
        author="Soumith Kumar Ananthula, Varun Reddy Beesam, Vivek Doppalapudi",
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(OUTPUT_PDF)


if __name__ == "__main__":
    build_pdf()
