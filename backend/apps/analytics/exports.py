"""CSV, XLSX, and pure-Python PDF report exporters with formula sanitization."""
import csv
import io
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


def _sanitize_csv_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


def export_cohort_csv(analytics: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    cohort = analytics["cohort"]
    writer.writerow(["MCA Career Compass — Cohort Analytics Report", cohort["label"]])
    writer.writerow(["Notice", analytics["notice"]])
    writer.writerow([])
    writer.writerow([
        "registration_no",
        "full_name",
        "attempts_count",
        "demonstrated_average_pct",
        "top_strength",
        "primary_gap",
        "needs_additional_training",
    ])
    for s in analytics["student_comparison"]:
        writer.writerow([
            _sanitize_csv_cell(s["registration_no"]),
            _sanitize_csv_cell(s["full_name"]),
            s["attempts_count"],
            s["average_percentage"] if s["average_percentage"] is not None else "Insufficient data",
            _sanitize_csv_cell(s["top_strength"] or "—"),
            _sanitize_csv_cell(s["primary_gap"] or "—"),
            "Yes" if s["needs_additional_training"] else "No",
        ])
    return buf.getvalue()


def export_student_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    stu = report["student"]
    writer.writerow(["MCA Career Compass — Individual Student Report", stu["registration_no"], stu["full_name"]])
    writer.writerow(["Notice", report["notice"]])
    writer.writerow([])
    writer.writerow(["measurement_family", "dimension_code", "dimension_name", "score_or_rating", "status"])
    for d in report["demonstrated_performance"]["dimensions"]:
        writer.writerow([
            "Demonstrated Performance",
            _sanitize_csv_cell(d["code"]),
            _sanitize_csv_cell(d["name"]),
            f"{d['percentage']}%" if d["percentage"] is not None else "Insufficient data",
            d["status"],
        ])
    for d in report["self_reported_proficiency"]:
        writer.writerow([
            "Self-Reported Proficiency",
            _sanitize_csv_cell(d["code"]),
            _sanitize_csv_cell(d["name"]),
            d["average_rating"] if d["average_rating"] is not None else "Recorded",
            d["status"],
        ])
    for d in report["stated_interest"]:
        writer.writerow([
            "Stated Career Interest",
            _sanitize_csv_cell(d["code"]),
            _sanitize_csv_cell(d["name"]),
            d["average_rating"] if d["average_rating"] is not None else "Recorded",
            d["status"],
        ])
    return buf.getvalue()


def export_cohort_xlsx(analytics: dict[str, Any]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Student Comparison"

    header_fill = PatternFill(start_color="0F2942", end_color="0F2942", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    headers = [
        "Registration No",
        "Student Name",
        "Attempts",
        "Demonstrated Avg %",
        "Top Strength",
        "Primary Gap",
        "Additional Training Recommended",
    ]
    ws.append(headers)
    for idx in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=idx)
        c.fill = header_fill
        c.font = header_font
        ws.column_dimensions[c.column_letter].width = 22

    for s in analytics["student_comparison"]:
        ws.append([
            s["registration_no"],
            s["full_name"],
            s["attempts_count"],
            s["average_percentage"] if s["average_percentage"] is not None else "Insufficient data",
            s["top_strength"] or "—",
            s["primary_gap"] or "—",
            "Yes" if s["needs_additional_training"] else "No",
        ])

    ws_demo = wb.create_sheet("Demonstrated Domains")
    ws_demo.append(["Code", "Dimension", "Cohort Avg %", "Status"])
    for d in analytics["demonstrated_performance_domains"]:
        ws_demo.append([
            d["code"],
            d["name"],
            d["average_percentage"] if d["average_percentage"] is not None else "Insufficient data",
            d["status"],
        ])

    ws_other = wb.create_sheet("Self-Report & Interests")
    ws_other.append(["Measurement Family", "Code", "Dimension", "Average Rating", "Responses"])
    for d in analytics["self_reported_proficiency_domains"]:
        ws_other.append(["Self-Reported Proficiency", d["code"], d["name"], d["average_rating"], d["responses_count"]])
    for d in analytics["stated_interest_domains"]:
        ws_other.append(["Stated Career Interest", d["code"], d["name"], d["average_rating"], d["responses_count"]])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_student_xlsx(report: dict[str, Any]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Demonstrated Performance"
    stu = report["student"]
    ws.append(["Student", stu["registration_no"], stu["full_name"], stu["cohort_label"] or ""])
    ws.append(["Notice", report["notice"]])
    ws.append([])
    ws.append(["Code", "Dimension", "Awarded", "Max", "Percentage", "Status"])
    for d in report["demonstrated_performance"]["dimensions"]:
        ws.append([
            d["code"],
            d["name"],
            d["awarded_marks"],
            d["max_marks"],
            d["percentage"] if d["percentage"] is not None else "Insufficient data",
            d["status"],
        ])

    ws2 = wb.create_sheet("Self-Report & Interests")
    ws2.append(["Measurement Family", "Code", "Dimension", "Avg Rating", "Responses"])
    for d in report["self_reported_proficiency"]:
        ws2.append(["Self-Reported Proficiency", d["code"], d["name"], d["average_rating"], d["responses_count"]])
    for d in report["stated_interest"]:
        ws2.append(["Stated Career Interest", d["code"], d["name"], d["average_rating"], d["responses_count"]])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pdf_escape(text: str) -> str:
    ascii_text = text.encode("latin-1", "replace").decode("latin-1")
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_lines_pdf(title: str, lines: list[str]) -> bytes:
    """Generate a clean valid PDF 1.4 document with paginated Helvetica text lines."""
    lines_per_page = 46
    all_lines = [title, "-" * min(72, max(20, len(title))), ""] + lines
    pages = [all_lines[i : i + lines_per_page] for i in range(0, len(all_lines), lines_per_page)] or [[title]]

    objects: list[bytes] = []
    # 1: Catalog, 2: Pages, 3: Font
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    page_obj_ids = [4 + idx * 2 for idx in range(len(pages))]
    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(pages)} >>\nendobj\n".encode("ascii"))
    objects.append(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    for idx, page_lines in enumerate(pages):
        page_id = 4 + idx * 2
        content_id = page_id + 1
        stream_cmds = ["BT", "/F1 10 Tf", "50 755 Td", "14 TL"]
        for line_idx, line in enumerate(page_lines):
            escaped = _pdf_escape(line[:105])
            if line_idx == 0:
                stream_cmds.append(f"({escaped}) Tj")
            else:
                stream_cmds.append(f"T* ({escaped}) Tj")
        stream_cmds.append("ET")
        stream_bytes = "\n".join(stream_cmds).encode("latin-1")

        objects.append(
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>\nendobj\n".encode("ascii")
        )
        objects.append(
            f"{content_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream\nendobj\n"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def export_cohort_pdf(analytics: dict[str, Any]) -> bytes:
    c = analytics["cohort"]
    s = analytics["summary"]
    lines = [
        f"Cohort: {c['label']}",
        f"Students: {s['total_students']} | Assessed: {s['assessed_students']} | Avg: {s['cohort_average_percentage']}% | Need Support: {s['students_needing_training']}",
        f"Notice: {analytics['notice']}",
        "",
        "Demonstrated Performance Domains:",
    ]
    for d in analytics["demonstrated_performance_domains"]:
        pct = f"{d['average_percentage']}%" if d["average_percentage"] is not None else "Insufficient data"
        lines.append(f"  - {d['code']} ({d['name']}): {pct}")
    lines.append("")
    lines.append("Student Comparison:")
    for stu in analytics["student_comparison"]:
        pct = f"{stu['average_percentage']}%" if stu["average_percentage"] is not None else "N/A"
        lines.append(
            f"  {stu['registration_no']} | {stu['full_name']} | Avg: {pct} | Top: {stu['top_strength'] or '-'} | Gap: {stu['primary_gap'] or '-'}"
        )
    return render_lines_pdf(f"MCA Career Compass - Cohort Report ({c['label']})", lines)


def export_student_pdf(report: dict[str, Any]) -> bytes:
    stu = report["student"]
    summary = report["summary"]
    lines = [
        f"Student: {stu['registration_no']} - {stu['full_name']} ({stu['cohort_label'] or 'No cohort'})",
        f"Assessments: {summary['assessments_count']} | Overall Demonstrated Avg: {summary['overall_demonstrated_percentage']}%",
        f"Notice: {report['notice']}",
        "",
        "Demonstrated Performance:",
    ]
    for d in report["demonstrated_performance"]["dimensions"]:
        pct = f"{d['percentage']}%" if d["percentage"] is not None else "Insufficient data"
        lines.append(f"  - {d['code']} ({d['name']}): {d['awarded_marks']}/{d['max_marks']} ({pct})")
    lines.append("")
    lines.append("Self-Reported Proficiency:")
    for d in report["self_reported_proficiency"]:
        lines.append(f"  - {d['code']} ({d['name']}): Avg rating {d['average_rating']}")
    lines.append("")
    lines.append("Stated Career Interests:")
    for d in report["stated_interest"]:
        lines.append(f"  - {d['code']} ({d['name']}): Interest rating {d['average_rating']}")
    return render_lines_pdf(f"MCA Career Compass - Student Report ({stu['registration_no']})", lines)


def export_executive_csv(exec_data: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    inst = exec_data["institution"]
    s = exec_data["summary"]
    writer.writerow(["MCA Career Compass — Institution Executive Report", f"{inst['code']} - {inst['name']}"])
    writer.writerow(["Notice", exec_data["notice"]])
    writer.writerow([
        "Total Students",
        s["total_students"],
        "Participation %",
        s["participation_rate"],
        "Demonstrated Avg %",
        s["overall_demonstrated_percentage"] if s["overall_demonstrated_percentage"] is not None else "Insufficient data",
        "Placement Ready %",
        s["placement_ready_rate"],
    ])
    writer.writerow([])
    writer.writerow([
        "cohort_label",
        "total_students",
        "assessed_students",
        "demonstrated_average_pct",
        "placement_ready_count",
        "near_ready_count",
        "needs_support_count",
        "plan_adoption_rate",
        "avg_plan_completion_pct",
    ])
    for c in exec_data["cohort_rollups"]:
        writer.writerow([
            _sanitize_csv_cell(c["cohort_label"]),
            c["total_students"],
            c["assessed_students"],
            c["average_demonstrated_percentage"] if c["average_demonstrated_percentage"] is not None else "Insufficient data",
            c["placement_ready_count"],
            c["near_ready_count"],
            c["needs_support_count"],
            f"{c['plan_adoption_rate']}%",
            f"{c['avg_plan_completion_percent']}%",
        ])
    return buf.getvalue()


def export_executive_xlsx(exec_data: dict[str, Any]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Cohort Rollup"

    header_fill = PatternFill(start_color="0F2942", end_color="0F2942", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    headers = [
        "Cohort",
        "Total Students",
        "Assessed Students",
        "Demonstrated Avg %",
        "Placement Ready",
        "Near Ready",
        "Needs Support",
        "Plan Adoption %",
        "Avg Plan Completion %",
    ]
    ws.append(headers)
    for idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=idx)
        cell.fill = header_fill
        cell.font = header_font

    for c in exec_data["cohort_rollups"]:
        ws.append([
            _sanitize_csv_cell(c["cohort_label"]),
            c["total_students"],
            c["assessed_students"],
            c["average_demonstrated_percentage"] if c["average_demonstrated_percentage"] is not None else "Insufficient data",
            c["placement_ready_count"],
            c["near_ready_count"],
            c["needs_support_count"],
            c["plan_adoption_rate"],
            c["avg_plan_completion_percent"],
        ])

    ws2 = wb.create_sheet("Institution Domains")
    d_headers = ["Measurement Family", "Code", "Dimension", "Average"]
    ws2.append(d_headers)
    for idx in range(1, len(d_headers) + 1):
        cell = ws2.cell(row=1, column=idx)
        cell.fill = header_fill
        cell.font = header_font

    for d in exec_data["demonstrated_domains"]:
        ws2.append([
            "Demonstrated Performance",
            _sanitize_csv_cell(d["code"]),
            _sanitize_csv_cell(d["name"]),
            f"{d['average_percentage']}%" if d["average_percentage"] is not None else "Insufficient data",
        ])
    for d in exec_data["self_reported_domains"]:
        ws2.append(["Self-Reported Proficiency", _sanitize_csv_cell(d["code"]), _sanitize_csv_cell(d["name"]), d["average_rating"]])
    for d in exec_data["stated_interest_domains"]:
        ws2.append(["Stated Career Interest", _sanitize_csv_cell(d["code"]), _sanitize_csv_cell(d["name"]), d["average_rating"]])

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def export_executive_pdf(exec_data: dict[str, Any]) -> bytes:
    inst = exec_data["institution"]
    s = exec_data["summary"]
    lines = [
        f"Institution: {inst['code']} - {inst['name']}",
        f"Students: {s['total_students']} | Assessed: {s['assessed_students']} ({s['participation_rate']}%) | Mean: {s['overall_demonstrated_percentage']}%",
        f"Placement Ready: {s['placement_ready_count']} ({s['placement_ready_rate']}%) | Plans Avg: {s['avg_plan_completion_percent']}%",
        f"Notice: {exec_data['notice']}",
        "",
        "Cohort Rollup:",
    ]
    for c in exec_data["cohort_rollups"]:
        avg_s = f"{c['average_demonstrated_percentage']}%" if c["average_demonstrated_percentage"] is not None else "N/A"
        lines.append(
            f"  - {c['cohort_label']} | Stu: {c['total_students']} | Avg: {avg_s} | Ready: {c['placement_ready_count']} | Support: {c['needs_support_count']}"
        )
    lines.append("")
    lines.append("Demonstrated Performance Domains:")
    for d in exec_data["demonstrated_domains"]:
        pct = f"{d['average_percentage']}%" if d["average_percentage"] is not None else "Insufficient data"
        lines.append(f"  - {d['code']} ({d['name']}): {pct}")
    return render_lines_pdf(f"MCA Career Compass - Executive Report ({inst['code']})", lines)

