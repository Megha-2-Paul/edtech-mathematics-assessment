"""Generate the fixed two-page Improvia student performance PDF."""
from io import BytesIO
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#18324F")
BLUE = colors.HexColor("#4779B8")
PALE = colors.HexColor("#F2F6FA")
BORDER = colors.HexColor("#D9E1EA")
MUTED = colors.HexColor("#5D6B7A")


def _text(value, fallback="N/A"):
    if value is None or value == "":
        value = fallback
    return escape(str(value))


def _number(value, suffix=""):
    if value is None:
        return "N/A"
    try:
        number = float(value)
        rendered = f"{number:.1f}".rstrip("0").rstrip(".")
        return f"{rendered}{suffix}"
    except (TypeError, ValueError):
        return _text(value)


def _p(value, style):
    return Paragraph(_text(value), style)


def _table(data, widths, header=True, font_size=8):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ])
        if len(data) > 1:
            commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]))
    table.setStyle(TableStyle(commands))
    return table


def render_report_pdf(report):
    """Return a two-page PDF for a report that has passed data validation."""
    diagnosis = report.get("diagnosis") or {}
    if not diagnosis.get("report_ready"):
        raise ValueError("Cannot generate a final report before evaluation and data validation are complete.")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ImproviaTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=17, leading=20, textColor=NAVY, alignment=TA_LEFT, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="ImproviaSub", parent=styles["Normal"], fontSize=8.5, leading=11,
        textColor=MUTED, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=13, textColor=NAVY, spaceBefore=7, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="BodySmall", parent=styles["BodyText"], fontSize=8, leading=10,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="Metric", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=11, leading=13, textColor=NAVY, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="MetricLabel", parent=styles["Normal"], fontSize=7.5, leading=9,
        textColor=MUTED, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SmallCenter", parent=styles["Normal"], fontSize=7.5, leading=9,
        textColor=MUTED, alignment=TA_CENTER,
    ))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=12 * mm, bottomMargin=14 * mm,
        title=f"Improvia Performance Report - {report.get('student_id', '')}",
        author="Improvia",
    )
    width = A4[0] - 28 * mm
    story = []

    # PAGE 1: student/guardian summary.
    story.append(Paragraph("IMPROVIA | Mathematics Performance Report", styles["ImproviaTitle"]))
    story.append(Paragraph(
        f"{_text(report.get('test_title'))}  |  {_text(report.get('test_date'))}  |  "
        f"Assessment ID: {_text(report.get('test_id'))}",
        styles["ImproviaSub"],
    ))
    meta = [[
        _p(f"Student: {report.get('student_name')}", styles["BodySmall"]),
        _p(f"Student ID: {report.get('student_id')}", styles["BodySmall"]),
        _p(f"Class: {report.get('class_level')}", styles["BodySmall"]),
    ], [
        _p(f"Board: {report.get('board')}", styles["BodySmall"]),
        _p(f"Subject: {report.get('subject', 'Mathematics')}", styles["BodySmall"]),
        _p(f"Duration: {report.get('duration_minutes')} min", styles["BodySmall"]),
    ]]
    meta_table = Table(meta, colWidths=[width * .43, width * .31, width * .26])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), .5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([meta_table, Spacer(1, 7)])

    metrics = [
        [Paragraph("SCORE", styles["MetricLabel"]),
         Paragraph("ATTEMPT RATE", styles["MetricLabel"]),
         Paragraph("ATTEMPTED-WORK ACCURACY", styles["MetricLabel"]),
         Paragraph("UNATTEMPTED", styles["MetricLabel"])],
        [Paragraph(f"{_number(diagnosis.get('score'))}/{_number(diagnosis.get('total_marks'))}<br/>{_number(diagnosis.get('percentage'), '%')}", styles["Metric"]),
         Paragraph(_number(diagnosis.get("attempt_rate"), "%"), styles["Metric"]),
         Paragraph(_number(diagnosis.get("accuracy"), "%"), styles["Metric"]),
         Paragraph(f"{diagnosis.get('unattempted', 'N/A')}<br/><font size='7'>questions</font>", styles["Metric"])],
        [Paragraph(f"{diagnosis.get('attempted', 0)} of {diagnosis.get('total_questions', 0)} questions attempted", styles["SmallCenter"]),
         Paragraph("Share of questions attempted", styles["SmallCenter"]),
         Paragraph("Marks earned / marks available on attempted work", styles["SmallCenter"]),
         Paragraph(f"{_number(diagnosis.get('unattempted_available_marks'))} marks available", styles["SmallCenter"])],
    ]
    metric_table = Table(metrics, colWidths=[width / 4] * 4)
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), .6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), .35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([metric_table, Paragraph("Chapter performance", styles["Section"])])

    chapters = sorted(
        diagnosis.get("chapter_analysis", []),
        key=lambda item: item.get("percentage", 0),
        reverse=True,
    )[:8]
    chapter_data = [[
        Paragraph("<b>Chapter</b>", styles["BodySmall"]),
        Paragraph("<b>Marks</b>", styles["BodySmall"]),
        Paragraph("<b>Performance</b>", styles["BodySmall"]),
        Paragraph("<b>Evidence</b>", styles["BodySmall"]),
    ]]
    for item in chapters:
        evidence = "Insufficient evidence" if item.get("evidence_status") == "insufficient_evidence" else "Observed"
        chapter_data.append([
            _p(item.get("name"), styles["BodySmall"]),
            _p(f"{_number(item.get('marks'))}/{_number(item.get('max_marks'))}", styles["BodySmall"]),
            _p(_number(item.get("percentage"), "%"), styles["BodySmall"]),
            _p(evidence, styles["BodySmall"]),
        ])
    if len(chapter_data) == 1:
        chapter_data.append([_p("No chapter data available", styles["BodySmall"]), "", "", ""])
    story.append(_table(chapter_data, [width * .39, width * .18, width * .18, width * .25], font_size=8))

    strengths = diagnosis.get("strengths", [])
    weaknesses = diagnosis.get("weaknesses", [])
    story.append(Paragraph("What the evidence suggests", styles["Section"]))
    if strengths:
        story.append(Paragraph(
            "<b>Demonstrated strength:</b> " + _text(strengths[0].get("name")) +
            " (" + _number(strengths[0].get("percentage"), "%") + ").",
            styles["BodySmall"],
        ))
    if weaknesses:
        story.append(Paragraph(
            "<b>Priority area:</b> " + _text(weaknesses[0].get("name")) +
            " (" + _number(weaknesses[0].get("percentage"), "%") + "). "
            "Review the evaluated questions before concluding whether the cause is conceptual, methodological, or presentation-related.",
            styles["BodySmall"],
        ))
    if not strengths and not weaknesses:
        story.append(Paragraph("No strong chapter-level conclusion is available from the current evidence.", styles["BodySmall"]))

    summary = (
        f"This assessment establishes a baseline. The student earned "
        f"{_number(diagnosis.get('score'))} of {_number(diagnosis.get('total_marks'))} marks. "
        "Use the priorities on page 2 to guide focused practice; future assessments will show whether the patterns change."
        if not diagnosis.get("previous_attempt_count")
        else
        f"The student earned {_number(diagnosis.get('score'))} of {_number(diagnosis.get('total_marks'))} marks. "
        "Compare the trend and recurring patterns on page 2, then review the next-step plan together."
    )
    story.append(Paragraph("Summary for student and parent", styles["Section"]))
    story.append(Paragraph(_text(summary), styles["BodySmall"]))

    # PAGE 2: diagnostic evidence and next steps.
    story.append(PageBreak())
    story.append(Paragraph("Diagnosis, progress and next steps", styles["ImproviaTitle"]))
    story.append(Paragraph(
        "Error tags are evaluator observations. Their frequency does not by itself prove how many marks each error caused.",
        styles["ImproviaSub"],
    ))
    story.append(Paragraph("Recorded error patterns", styles["Section"]))
    error_counts = diagnosis.get("error_counts", [])[:9]
    error_data = [[
        Paragraph("<b>Code</b>", styles["BodySmall"]),
        Paragraph("<b>Error pattern</b>", styles["BodySmall"]),
        Paragraph("<b>Questions tagged</b>", styles["BodySmall"]),
        Paragraph("<b>Prior assessments</b>", styles["BodySmall"]),
    ]]
    recurring = {item.get("code"): item for item in diagnosis.get("recurring_errors", [])}
    for item in error_counts:
        prior = recurring.get(item.get("code"), {}).get("prior_assessments", 0)
        error_data.append([
            _p(item.get("code"), styles["BodySmall"]),
            _p(item.get("label"), styles["BodySmall"]),
            _p(item.get("count"), styles["BodySmall"]),
            _p(prior if prior else "Not recurring", styles["BodySmall"]),
        ])
    if len(error_data) == 1:
        error_data.append([_p("No error codes recorded", styles["BodySmall"]), "", "", ""])
    story.append(_table(error_data, [width * .13, width * .39, width * .23, width * .25], font_size=8))

    story.append(Paragraph("Progress compared with the previous assessment", styles["Section"]))
    if diagnosis.get("previous_attempt_count"):
        prev_score = diagnosis.get("previous_score")
        prev_pct = diagnosis.get("previous_percentage")
        score_change = diagnosis.get("score_change")
        pct_change = diagnosis.get("percentage_change")
        comparison = (
            f"Previous score: {_number(prev_score)} marks / {_number(prev_pct, '%')}. "
            f"Current score: {_number(diagnosis.get('score'))} marks / {_number(diagnosis.get('percentage'), '%')}. "
            f"Marks change: {('+' if diagnosis.get('marks_change') is not None and diagnosis.get('marks_change') >= 0 else '')}{_number(diagnosis.get('marks_change'))} marks; "
            f"percentage-point change: {('+' if pct_change is not None and pct_change >= 0 else '')}{_number(pct_change)} percentage points. " + _text(diagnosis.get('comparison_note', ''))
        )
        story.append(Paragraph(_text(comparison), styles["BodySmall"]))
    else:
        story.append(Paragraph("Baseline assessment: no previous assessment is available for comparison.", styles["BodySmall"]))

    if diagnosis.get("recurring_errors"):
        names = ", ".join(
            f"{item.get('label')} ({item.get('prior_assessments')} prior assessment(s))"
            for item in diagnosis.get("recurring_errors", [])[:5]
        )
        story.append(Paragraph("<b>Recurring across assessments:</b> " + _text(names), styles["BodySmall"]))
    else:
        story.append(Paragraph("No error code is currently confirmed as recurring across assessments.", styles["BodySmall"]))

    story.append(Paragraph("Personalised next steps", styles["Section"]))
    recommendations = report.get("recommendations", [])[:3]
    for index, item in enumerate(recommendations, 1):
        story.append(Paragraph(
            f"<b>{index}. {_text(item.get('title'))}</b><br/>{_text(item.get('action'))}",
            styles["BodySmall"],
        ))
        story.append(Spacer(1, 3))
    if not recommendations:
        story.append(Paragraph("Review the evaluated answers with the teacher and choose a focused practice target.", styles["BodySmall"]))

    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "<b>How to interpret this report:</b> Chapter results with limited attempts are flagged. "
        "Error frequency is not equivalent to marks lost. Comparisons may be limited when assessments differ in syllabus coverage, difficulty, or question mix. "
        "Use this report to guide practice, not as a prediction of board-exam marks.",
        styles["BodySmall"],
    ))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(BORDER)
        canvas.line(14 * mm, 10 * mm, A4[0] - 14 * mm, 10 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(14 * mm, 6 * mm, "Improvia | Learn. Improve. Ace.")
        canvas.drawRightString(A4[0] - 14 * mm, 6 * mm, f"Page {document.page} of 2")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    if len(PdfReader(buffer).pages) != 2:
        raise RuntimeError("Generated report did not fit the required two-page layout.")
    buffer.seek(0)
    return buffer
