"""PDF layout built from persisted server results, never client-supplied counts."""
from html import escape
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from ..config import LABELS

DISCLAIMER = "This assessment is generated using an AI-based prototype and should be validated against official onion grading standards before commercial deployment."


def generate_report(result, image_path, output_path):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallNote", fontSize=8, leading=11, textColor=colors.HexColor("#52605b")))
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=42, leftMargin=42,
                            topMargin=36, bottomMargin=40, title="AI Onion Quality Assessment Report")
    story = [Paragraph("AI Onion Quality Assessment Report", styles["Title"]),
             Paragraph("ACADEMIC PROTOTYPE / VISUAL INSPECTION", styles["SmallNote"]), Spacer(1, 12),
             Paragraph(f"<b>Report ID:</b> {escape(result['report_id'])}<br/><b>Date / time (UTC):</b> {escape(result['created_at'])}", styles["Normal"]),
             Spacer(1, 14)]
    rows = [["Quality measure", "Count", "Percentage"], ["Total onions detected", str(result["total_onions"]), "100%" if result["total_onions"] else "N/A"]]
    for key, label in LABELS.items():
        rows.append([label, str(result[key]["count"]), f"{result[key]['percentage']:.2f}%"])
    # Preserve totals when explicitly regenerating an older saved analysis.
    if result.get("uncertain", {}).get("count", 0):
        rows.append(["Uncertain (legacy analysis)", str(result["uncertain"]["count"]), f"{result['uncertain']['percentage']:.2f}%"])
    rows.append(["URS (configured categories)", str(result["urs_count"]), f"{result['urs_percentage']:.2f}%"])
    table = Table(rows, colWidths=[285, 75, 151], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#35543e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#eff4ef"), colors.white]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [table, Spacer(1, 12), Paragraph("Analyzed image", styles["Heading2"])]
    with PILImage.open(image_path) as image:
        ratio = min(511 / image.width, 220 / image.height)
        story.append(Image(str(image_path), width=image.width * ratio, height=image.height * ratio))
    story += [Spacer(1, 10), Paragraph("Rules and interpretation", styles["Heading2"])]
    rules = result["rules"]
    note = (f"Minimum diameter: {rules['minimum_diameter_cm']} cm. Reference marker: {rules['marker_size_cm']} cm. "
            f"Review threshold: {rules['confidence_threshold']}. URS: {', '.join(rules['urs_classes'])}. "
            f"Predictions needing review: {result.get('needs_review_count', 0)}. All detections are included in the denominator. "
            "Grade A means healthy appearance; size is verified only when measured. "
            "CLIP scores are not calibrated probabilities. Size is an approximate planar measurement.")
    story.append(Paragraph(escape(note), styles["SmallNote"]))
    for warning in result["warnings"]:
        story.append(Paragraph(escape(warning), styles["SmallNote"]))
    story += [Spacer(1, 12), Paragraph(DISCLAIMER, styles["SmallNote"])]

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#52605b"))
        canvas.drawString(42, 22, "Onion Quality Analyzer | Pretrained CLIP")
        canvas.drawRightString(A4[0] - 42, 22, f"Page {document.page}")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
