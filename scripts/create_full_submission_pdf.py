from __future__ import annotations

import csv
import html
import json
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
NOTEBOOKS = ROOT / "notebooks"
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_PDF = OUTPUT_DIR / "NYC_Taxi_Deliverable_2_Full_Submission_Report.pdf"

INK = colors.HexColor("#111111")
DARK_GRAY = colors.HexColor("#333333")
MID_GRAY = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#F1F1F1")
LINE_GRAY = colors.HexColor("#B8B8B8")
SOFT_GRAY = colors.HexColor("#FAFAFA")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def safe(text: object) -> str:
    return html.escape(str(text), quote=False)


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(safe(text), style)


def bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"- {safe(text)}", style)


def add_bullets(story: list, items: list[str], style: ParagraphStyle) -> None:
    for item in items:
        story.append(bullet(item, style))


def code_block(text: str, style: ParagraphStyle, width: int = 95) -> Preformatted:
    wrapped_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if len(line) <= width:
            wrapped_lines.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        subsequent = " " * min(indent + 4, 16)
        wrapped_lines.extend(
            textwrap.wrap(
                line,
                width=width,
                subsequent_indent=subsequent,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return Preformatted("\n".join(wrapped_lines), style)


def notebook_code_cells(path: Path) -> list[str]:
    notebook = load_json(path)
    cells: list[str] = []
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if source.strip():
                cells.append(source)
    return cells


def metric(metrics: dict, key: str) -> str:
    return f"{metrics[key]:.4f}"


def pct(metrics: dict, key: str) -> str:
    return f"{metrics[key] * 100:.2f}%"


def metric_change(new: float, old: float) -> str:
    return f"{(new - old) * 100:+.2f} pts"


def make_table(
    data: list[list[str]],
    widths: list[float],
    font_size: float = 8.2,
    header: bool = True,
) -> Table:
    table = Table(data, colWidths=[w * inch for w in widths], repeatRows=1 if header else 0)
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT_GRAY]),
    ]
    if header:
        commands.extend(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def add_captioned_figure(
    story: list,
    image_path: Path,
    caption: str,
    styles,
    width: float = 6.0,
    height: float = 3.75,
) -> None:
    if not image_path.exists():
        return
    story.append(
        KeepTogether(
            [
                para(caption, styles["FigureCaption"]),
                Image(str(image_path), width=width * inch, height=height * inch),
            ]
        )
    )
    story.append(Spacer(1, 0.16 * inch))


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE_GRAY)
    canvas.setLineWidth(0.4)
    canvas.line(0.72 * inch, 0.58 * inch, 7.78 * inch, 0.58 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(0.72 * inch, 0.42 * inch, "NYC Taxi Deliverable 2 Full Submission Report")
    canvas.drawRightString(7.78 * inch, 0.42 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=26,
            alignment=TA_CENTER,
            textColor=INK,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=DARK_GRAY,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=INK,
            spaceBefore=14,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subsection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=INK,
            spaceBefore=9,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=13.2,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletCustom",
            parent=styles["Body"],
            leftIndent=14,
            firstLineIndent=-9,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Body"],
            fontSize=8.4,
            leading=11.2,
            textColor=DARK_GRAY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FigureCaption",
            parent=styles["Body"],
            fontName="Helvetica-Bold",
            fontSize=8.6,
            leading=11,
            alignment=TA_CENTER,
            textColor=INK,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeBlockCustom",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=6.1,
            leading=7.2,
            borderColor=LINE_GRAY,
            borderWidth=0.4,
            borderPadding=5,
            backColor=SOFT_GRAY,
            textColor=INK,
            spaceBefore=3,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TOCLine",
            parent=styles["Body"],
            fontName="Helvetica",
            fontSize=9.8,
            leading=13,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="RightSmall",
            parent=styles["Small"],
            alignment=TA_RIGHT,
        )
    )
    return styles


def add_markdown_report(story: list, styles) -> None:
    """Render the assignment markdown in a simple, controlled way."""
    for line in read_text(REPORTS / "assignment_report.md").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            story.append(para(stripped[2:], styles["Section"]))
        elif stripped.startswith("## "):
            story.append(para(stripped[3:], styles["Section"]))
        elif stripped.startswith("- "):
            story.append(bullet(stripped[2:], styles["BulletCustom"]))
        elif stripped.startswith("|"):
            continue
        else:
            clean = stripped.replace("**", "").replace("`", "")
            story.append(para(clean, styles["Body"]))


def build_pdf() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = load_json(REPORTS / "metrics.json")
    model_rows = load_csv(REPORTS / "model_metrics.csv")
    tuning_rows = load_csv(REPORTS / "tuning_results.csv")
    feature_importance = load_csv(REPORTS / "model_feature_importance.csv")
    audit = load_csv(REPORTS / "preprocessing_audit.csv")
    feature_summary = load_csv(REPORTS / "feature_engineering_summary.csv")
    requirements = read_text(ROOT / "requirements.txt").strip()
    main_code = read_text(SRC / "nyc_taxi_long_trip_model.py")
    pdf_script = read_text(SCRIPTS / "create_full_submission_pdf.py")
    prediction_cells = notebook_code_cells(NOTEBOOKS / "predict_new_taxi_trip.ipynb")
    day2_cells = notebook_code_cells(NOTEBOOKS / "nyc_taxi_long_trip_model_day2.ipynb")

    baseline = metrics["baseline_most_frequent"]
    initial = metrics["initial_logistic_regression"]
    final = metrics["optimized_hist_gradient_boosting"]
    selected = metrics["model_optimization"]["selected_candidate"]

    styles = build_styles()
    story: list = []

    story.append(Spacer(1, 0.55 * inch))
    story.append(para("NYC Taxi AI Analytics Project", styles["CoverTitle"]))
    story.append(
        para(
            "Deliverable 2 Full Submission Report: Model Optimization, Metrics, Ethics, Outputs, and Code",
            styles["CoverSubtitle"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))
    story.append(
        make_table(
            [
                ["Field", "Value"],
                ["Repository branch", "project_day_2"],
                ["Project objective", "Predict whether a cleaned NYC yellow taxi trip lasts at least 30 minutes"],
                ["Final model", "Optimized histogram gradient boosting classifier"],
                ["Final test accuracy", pct(final, "accuracy")],
                ["Final test precision", pct(final, "precision")],
                ["Team members", "Soumith Kumar Ananthula, Varun Reddy Beesam, Vivek Doppalapudi"],
            ],
            [1.65, 4.85],
            font_size=8.7,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        para(
            "This PDF is designed as a one-file submission packet. It includes the written deliverable, dataset and preprocessing summary, hyperparameter tuning details, final evaluation metrics, figures, run instructions, dependencies, generated output inventory, and core source code.",
            styles["Body"],
        )
    )

    story.append(PageBreak())
    story.append(para("Submission Contents", styles["Section"]))
    contents = [
        "1. Executive summary",
        "2. Required Deliverable 2 report sections",
        "3. Dataset, preprocessing, and feature engineering evidence",
        "4. Hyperparameter tuning details and selected configuration",
        "5. Final model metrics and metric changes",
        "6. Key generated figures",
        "7. Reproducibility guide for Google Colab and local Python",
        "8. Generated artifacts inventory",
        "9. Appendix A: requirements.txt",
        "10. Appendix B: main training pipeline source code",
        "11. Appendix C: prediction notebook code cells",
        "12. Appendix D: Day 2 Colab notebook setup and pipeline cells",
        "13. Appendix E: PDF generation script",
    ]
    for item in contents:
        story.append(para(item, styles["TOCLine"]))

    story.append(PageBreak())
    story.append(para("1. Executive Summary", styles["Section"]))
    story.append(
        para(
            "The Day 2 work refined the Day 1 taxi long-trip classifier by adding a validation split, testing histogram gradient boosting candidates, tuning model hyperparameters, and selecting a precision-focused probability threshold. The final model predicts whether a trip is likely to last 30 minutes or longer.",
            styles["Body"],
        )
    )
    story.append(
        para(
            f"Compared with the Day 1 logistic regression model, the optimized model increased accuracy from {metric(initial, 'accuracy')} to {metric(final, 'accuracy')} and precision from {metric(initial, 'precision')} to {metric(final, 'precision')}. F1 improved from {metric(initial, 'f1')} to {metric(final, 'f1')}, and ROC-AUC improved from {metric(initial, 'roc_auc')} to {metric(final, 'roc_auc')}. Recall decreased from {metric(initial, 'recall')} to {metric(final, 'recall')} because the final threshold was raised to reduce false positives.",
            styles["Body"],
        )
    )
    add_bullets(
        story,
        [
            "Primary gain: fewer false long-trip alerts and much stronger precision.",
            f"False positives dropped from {initial['false_positive']:,} to {final['false_positive']:,}.",
            f"False negatives increased from {initial['false_negative']:,} to {final['false_negative']:,}, which is the cost of the precision-focused threshold.",
            "Recommended use: aggregate planning and decision support, not automated ride denial or neighborhood-level service restriction.",
        ],
        styles["BulletCustom"],
    )

    story.append(para("2. Deliverable 2 Written Report", styles["Section"]))
    add_markdown_report(story, styles)

    story.append(PageBreak())
    story.append(para("3. Dataset and Preprocessing Evidence", styles["Section"]))
    story.append(
        para(
            f"The pipeline used the official NYC TLC January 2024 yellow taxi parquet file. It loaded {metrics['dataset']['raw_rows']:,} raw rows, retained {metrics['dataset']['clean_rows_before_sampling']:,} realistic rows after cleaning, and used a deterministic {metrics['dataset']['model_sample_rows']:,}-row sample for modeling.",
            styles["Body"],
        )
    )
    selected_steps = {
        "03_filter_pickup_month",
        "04_filter_duration",
        "05_filter_distance",
        "06_filter_passengers",
        "07_filter_positive_fare",
        "09_filter_standard_ratecode",
        "13_model_sample",
    }
    audit_table = [["Preprocessing step", "Rows removed", "Rows after"]]
    for row in audit:
        if row["step"] in selected_steps:
            audit_table.append(
                [
                    row["description"],
                    f"{int(row['rows_removed']):,}",
                    f"{int(row['rows_after']):,}",
                ]
            )
    story.append(make_table(audit_table, [4.35, 1.05, 1.1], font_size=7.3))

    story.append(para("Feature Engineering Summary", styles["Subsection"]))
    feature_table = [["Feature", "Type", "Purpose"]]
    for row in feature_summary:
        feature_table.append([row["column"], row["type"], row["purpose"]])
    story.append(make_table(feature_table, [1.45, 1.25, 3.8], font_size=7.0))

    story.append(PageBreak())
    story.append(para("4. Hyperparameter Tuning Details", styles["Section"]))
    story.append(
        para(
            f"The selected model was {metrics['model_optimization']['selected_model']}. Five histogram-gradient-boosting candidates were tested on the validation set. The selected candidate was {selected['candidate']} with max_iter = {selected['max_iter']}, learning_rate = {selected['learning_rate']}, max_leaf_nodes = {selected['max_leaf_nodes']}, l2_regularization = {selected['l2_regularization']}, class_weight = {{0: 1, 1: 6}}, and a decision threshold of {metrics['model_optimization']['decision_threshold']:.2f}.",
            styles["Body"],
        )
    )
    story.append(
        para(
            "The selection metric was validation F0.5 with recall at or above 0.72. F0.5 gives more weight to precision than recall, which matches the assignment request to make the model more accurate and precise, while the recall floor prevents the model from ignoring too many actual long trips.",
            styles["Body"],
        )
    )
    tuning_table = [[
        "Candidate",
        "Threshold",
        "Max iter",
        "Learning rate",
        "Leaves",
        "L2",
        "Val precision",
        "Val recall",
        "Selected",
    ]]
    for row in tuning_rows:
        tuning_table.append(
            [
                row["candidate"],
                f"{float(row['selected_threshold']):.2f}",
                row["max_iter"],
                row["learning_rate"],
                row["max_leaf_nodes"],
                row["l2_regularization"],
                f"{float(row['validation_precision']):.4f}",
                f"{float(row['validation_recall']):.4f}",
                row["selected"],
            ]
        )
    story.append(make_table(tuning_table, [1.35, 0.62, 0.62, 0.78, 0.55, 0.45, 0.78, 0.68, 0.67], font_size=6.6))

    story.append(para("5. Final Model Metrics and Changes", styles["Section"]))
    model_table = [["Model", "Accuracy", "Precision", "Recall", "F1", "F0.5", "ROC-AUC"]]
    for row in model_rows:
        model_table.append(
            [
                row["model"],
                f"{float(row['accuracy']):.4f}",
                f"{float(row['precision']):.4f}",
                f"{float(row['recall']):.4f}",
                f"{float(row['f1']):.4f}",
                f"{float(row['f0_5']):.4f}",
                f"{float(row['roc_auc']):.4f}",
            ]
        )
    story.append(make_table(model_table, [1.9, 0.72, 0.78, 0.72, 0.62, 0.62, 0.72], font_size=7.5))
    impact_table = [
        ["Metric", "Day 1 logistic", "Day 2 optimized", "Change"],
        ["Accuracy", metric(initial, "accuracy"), metric(final, "accuracy"), metric_change(final["accuracy"], initial["accuracy"])],
        ["Precision", metric(initial, "precision"), metric(final, "precision"), metric_change(final["precision"], initial["precision"])],
        ["Recall", metric(initial, "recall"), metric(final, "recall"), metric_change(final["recall"], initial["recall"])],
        ["F1", metric(initial, "f1"), metric(final, "f1"), metric_change(final["f1"], initial["f1"])],
        ["ROC-AUC", metric(initial, "roc_auc"), metric(final, "roc_auc"), metric_change(final["roc_auc"], initial["roc_auc"])],
        ["False positives", f"{initial['false_positive']:,}", f"{final['false_positive']:,}", f"{final['false_positive'] - initial['false_positive']:,}"],
        ["False negatives", f"{initial['false_negative']:,}", f"{final['false_negative']:,}", f"{final['false_negative'] - initial['false_negative']:,}"],
    ]
    story.append(make_table(impact_table, [1.55, 1.25, 1.35, 1.25], font_size=7.8))
    story.append(para("Final classification report", styles["Subsection"]))
    classification_table = [
        ["Class", "Precision", "Recall", "F1-score", "Support"],
        ["Under 30 min", "0.9717", "0.9826", "0.9771", "21,893"],
        ["30+ min", "0.7954", "0.7029", "0.7463", "2,107"],
        ["Weighted avg", "0.9562", "0.9580", "0.9569", "24,000"],
    ]
    story.append(make_table(classification_table, [1.6, 0.95, 0.95, 0.95, 0.95], font_size=8.0))

    story.append(PageBreak())
    story.append(para("6. Figures and Model Interpretation", styles["Section"]))
    add_captioned_figure(story, FIGURES / "duration_distribution.png", "Figure 1. Cleaned trip duration distribution with the 30-minute threshold.", styles, 5.9, 3.55)
    add_captioned_figure(story, FIGURES / "hourly_long_trip_rate.png", "Figure 2. Long-trip rate by pickup hour.", styles, 5.9, 3.55)
    story.append(PageBreak())
    add_captioned_figure(story, FIGURES / "confusion_matrix.png", "Figure 3. Optimized model confusion matrix on the held-out test set.", styles, 5.0, 4.0)
    add_captioned_figure(story, FIGURES / "feature_importance.png", "Figure 4. Permutation feature importance for the optimized model.", styles, 5.9, 3.55)
    story.append(PageBreak())
    story.append(para("Feature importance values", styles["Subsection"]))
    importance_table = [["Feature", "Importance mean", "Importance std", "Scoring"]]
    for row in feature_importance[:10]:
        importance_table.append(
            [
                row["feature"],
                f"{float(row['importance_mean']):.6f}",
                f"{float(row['importance_std']):.6f}",
                row["scoring"],
            ]
        )
    story.append(make_table(importance_table, [2.2, 1.35, 1.25, 1.0], font_size=7.5))

    story.append(PageBreak())
    story.append(para("7. Reproducibility Guide", styles["Section"]))
    story.append(para("Google Colab setup", styles["Subsection"]))
    story.append(
        code_block(
            """!git clone --branch project_day_2 https://github.com/soumithkumara/project_day_1.git
%cd project_day_1
!pip install -r requirements.txt
!python src/nyc_taxi_long_trip_model.py""",
            styles["CodeBlockCustom"],
            width=92,
        )
    )
    story.append(para("Recommended notebook", styles["Subsection"]))
    story.append(
        para(
            "Open notebooks/nyc_taxi_long_trip_model_day2.ipynb for a fresh Colab run. The setup cell forces the project_day_2 branch and prints the active branch and commit.",
            styles["Body"],
        )
    )
    story.append(para("Local run", styles["Subsection"]))
    story.append(
        code_block(
            """.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\python.exe src\\nyc_taxi_long_trip_model.py""",
            styles["CodeBlockCustom"],
            width=92,
        )
    )
    story.append(para("Generated artifact inventory", styles["Subsection"]))
    inventory = [
        ["Path", "Purpose"],
        ["reports/assignment_report.md", "Written Deliverable 2 report"],
        ["reports/NYC_Taxi_Deliverable_2_Model_Optimization_Report.docx", "Word report version"],
        ["reports/metrics.json", "Dataset summary, split summary, metrics, and classification report"],
        ["reports/model_metrics.csv", "Baseline, logistic, and optimized model metrics"],
        ["reports/tuning_results.csv", "Validation tuning candidates and selected model"],
        ["reports/model_feature_importance.csv", "Permutation importance for optimized model"],
        ["reports/figures/", "EDA and model evaluation figures"],
        ["src/nyc_taxi_long_trip_model.py", "Main training, tuning, evaluation, and artifact pipeline"],
        ["notebooks/predict_new_taxi_trip.ipynb", "Notebook for new-trip prediction"],
    ]
    story.append(make_table(inventory, [2.55, 3.95], font_size=7.3))

    story.append(PageBreak())
    story.append(para("Appendix A: requirements.txt", styles["Section"]))
    story.append(code_block(requirements, styles["CodeBlockCustom"], width=96))

    story.append(PageBreak())
    story.append(para("Appendix B: Complete Main Training Pipeline", styles["Section"]))
    story.append(
        para(
            "This is the core project code that downloads/loads the data, preprocesses trips, tunes the model, evaluates metrics, writes artifacts, and saves the optimized model.",
            styles["Body"],
        )
    )
    story.append(code_block(main_code, styles["CodeBlockCustom"], width=98))

    story.append(PageBreak())
    story.append(para("Appendix C: Prediction Notebook Code Cells", styles["Section"]))
    for idx, cell_source in enumerate(prediction_cells, start=1):
        story.append(para(f"Prediction notebook code cell {idx}", styles["Subsection"]))
        story.append(code_block(cell_source, styles["CodeBlockCustom"], width=98))

    story.append(PageBreak())
    story.append(para("Appendix D: Day 2 Colab Notebook Code Cells", styles["Section"]))
    for idx, cell_source in enumerate(day2_cells[:8], start=1):
        story.append(para(f"Day 2 notebook code cell {idx}", styles["Subsection"]))
        story.append(code_block(cell_source, styles["CodeBlockCustom"], width=98))

    story.append(PageBreak())
    story.append(para("Appendix E: PDF Generation Script", styles["Section"]))
    story.append(
        para(
            "This appendix includes the script that generated this one-file submission PDF so the packet itself is reproducible.",
            styles["Body"],
        )
    )
    story.append(code_block(pdf_script, styles["CodeBlockCustom"], width=98))

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
        title="NYC Taxi Deliverable 2 Full Submission Report",
        author="Soumith Kumar Ananthula, Varun Reddy Beesam, Vivek Doppalapudi",
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return OUTPUT_PDF


if __name__ == "__main__":
    print(build_pdf())
