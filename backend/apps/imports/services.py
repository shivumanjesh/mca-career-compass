"""Staged Excel/CSV student import parser, validator, transactional commit, and CSV export."""
import csv
import io
import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from rest_framework.exceptions import ValidationError

from apps.academics.models import Cohort
from apps.accounts.models import Role, User
from apps.accounts.rbac import ROLE_STUDENT
from apps.audit.services import log_audit_event, sanitize_audit_payload
from apps.imports.models import ImportJob, ImportRowError
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole

REQUIRED_IMPORT_FIELDS = ("registration_no", "email", "first_name")
OPTIONAL_IMPORT_FIELDS = (
    "last_name",
    "programme_code",
    "batch_name",
    "semester",
    "section",
    "admission_year",
    "phone",
)
ALL_IMPORT_FIELDS = REQUIRED_IMPORT_FIELDS + OPTIONAL_IMPORT_FIELDS

HEADER_ALIASES: dict[str, str] = {
    "registration_no": "registration_no",
    "registration no": "registration_no",
    "registration number": "registration_no",
    "reg_no": "registration_no",
    "reg no": "registration_no",
    "usn": "registration_no",
    "roll_no": "registration_no",
    "roll no": "registration_no",
    "email": "email",
    "email_address": "email",
    "email address": "email",
    "e-mail": "email",
    "first_name": "first_name",
    "first name": "first_name",
    "fname": "first_name",
    "last_name": "last_name",
    "last name": "last_name",
    "lname": "last_name",
    "surname": "last_name",
    "programme_code": "programme_code",
    "programme code": "programme_code",
    "program": "programme_code",
    "programme": "programme_code",
    "batch_name": "batch_name",
    "batch name": "batch_name",
    "batch": "batch_name",
    "semester": "semester",
    "sem": "semester",
    "section": "section",
    "sec": "section",
    "admission_year": "admission_year",
    "admission year": "admission_year",
    "phone": "phone",
    "mobile": "phone",
    "phone_number": "phone",
}


def suggest_column_mapping(headers: list[str]) -> dict[str, str]:
    """Auto-suggest canonical field -> uploaded header mapping."""
    mapping: dict[str, str] = {}
    for header in headers:
        norm = " ".join(header.strip().lower().replace("-", "_").split())
        target = HEADER_ALIASES.get(norm) or HEADER_ALIASES.get(norm.replace("_", " "))
        if target and target not in mapping:
            mapping[target] = header
    return mapping


def generate_student_template_workbook() -> bytes:
    """Build a standard .xlsx student import template with instructions."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"

    headers = list(ALL_IMPORT_FIELDS)
    ws.append(headers)

    header_fill = PatternFill(start_color="0F2942", end_color="0F2942", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        ws.column_dimensions[cell.column_letter].width = 20

    # Synthetic example row
    ws.append([
        "4MT25MC001",
        "asha.sample@institution.edu",
        "Asha",
        "Rao",
        "MCA",
        "2025-2027",
        1,
        "A",
        2025,
        "9000000001",
    ])

    inst_ws = wb.create_sheet(title="Instructions")
    inst_ws.append(["Field", "Required", "Notes"])
    notes = [
        ("registration_no", "Yes", "Unique student registration number / USN within institution."),
        ("email", "Yes", "Valid institutional email address. Never include passwords in this file."),
        ("first_name", "Yes", "Student given name."),
        ("last_name", "No", "Student family name."),
        ("programme_code", "No", "Must match an existing Programme code (e.g. MCA) if assigning cohort via sheet."),
        ("batch_name", "No", "Must match an existing Cohort batch_name (e.g. 2025-2027)."),
        ("semester", "No", "Integer 1 to 8 matching the target Cohort."),
        ("section", "No", "Section code (e.g. A). Defaults to A when matching cohorts."),
        ("admission_year", "No", "Four-digit admission year (e.g. 2025)."),
        ("phone", "No", "Optional contact number."),
    ]
    for row in notes:
        inst_ws.append(list(row))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _inspect_xlsx(file_bytes: bytes) -> tuple[list[str], str, list[str], list[dict[str, str]]]:
    if not file_bytes.startswith(b"PK"):
        raise ValidationError({"file": "Uploaded .xlsx file is invalid or corrupted."})
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    try:
        sheets = wb.sheetnames
        if not sheets:
            raise ValidationError({"file": "Workbook contains no sheets."})
        active_sheet = sheets[0]
        ws = wb[active_sheet]
        headers, sample = _extract_sheet_preview(ws.iter_rows(values_only=True))
        return sheets, active_sheet, headers, sample
    finally:
        wb.close()


def _decode_csv_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def _inspect_csv(file_bytes: bytes) -> tuple[list[str], str, list[str], list[dict[str, str]]]:
    text = _decode_csv_text(file_bytes)
    reader = csv.reader(io.StringIO(text))
    headers, sample = _extract_sheet_preview(reader)
    return ["CSV"], "CSV", headers, sample


def _extract_sheet_preview(rows_iter) -> tuple[list[str], list[dict[str, str]]]:
    headers: list[str] = []
    sample: list[dict[str, str]] = []
    for idx, row in enumerate(rows_iter):
        cells = ["" if v is None else str(v).strip() for v in row]
        if idx == 0:
            headers = [c for c in cells if c]
            if not headers:
                raise ValidationError({"file": "The header row is empty."})
            # Preserve exact column positions using original header list
            headers = [c if c else f"Column_{i+1}" for i, c in enumerate(cells)]
        else:
            if not any(cells):
                continue
            record = {
                headers[i]: (cells[i] if i < len(cells) else "")
                for i in range(len(headers))
            }
            sample.append(record)
            if len(sample) >= 5:
                break
    if not headers:
        raise ValidationError({"file": "No header row found in uploaded file."})
    return headers, sample


def _read_all_rows(stored_path: Path, sheet_name: str | None = None) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    ext = stored_path.suffix.lower()
    raw_bytes = stored_path.read_bytes()
    rows_out: list[tuple[int, dict[str, str]]] = []

    if ext == ".csv":
        text = _decode_csv_text(raw_bytes)
        reader = csv.reader(io.StringIO(text))
        headers: list[str] = []
        for idx, row in enumerate(reader, start=1):
            cells = ["" if v is None else str(v).strip() for v in row]
            if idx == 1:
                headers = [c if c else f"Column_{i+1}" for i, c in enumerate(cells)]
                continue
            if not any(cells):
                continue
            row_dict = {headers[i]: (cells[i] if i < len(cells) else "") for i in range(len(headers))}
            rows_out.append((idx, row_dict))
        return headers, rows_out

    wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    try:
        target_sheet = sheet_name if sheet_name and sheet_name in wb.sheetnames else wb.sheetnames[0]
        ws = wb[target_sheet]
        headers = []
        for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = ["" if v is None else str(v).strip() for v in row]
            if idx == 1:
                headers = [c if c else f"Column_{i+1}" for i, c in enumerate(cells)]
                continue
            if not any(cells):
                continue
            row_dict = {headers[i]: (cells[i] if i < len(cells) else "") for i in range(len(headers))}
            rows_out.append((idx, row_dict))
        return headers, rows_out
    finally:
        wb.close()


@transaction.atomic
def create_import_upload(
    *,
    institution: Institution,
    user: User,
    uploaded_file,
    request=None,
) -> ImportJob:
    original_name = Path(uploaded_file.name).name
    ext = Path(original_name).suffix.lower()
    if ext not in {".xlsx", ".csv"}:
        raise ValidationError({"file": "Only .xlsx and .csv files are supported."})

    max_bytes = getattr(settings, "MAX_IMPORT_FILE_SIZE_BYTES", 10 * 1024 * 1024)
    if uploaded_file.size > max_bytes:
        raise ValidationError({"file": f"File exceeds maximum allowed size ({max_bytes // (1024 * 1024)} MB)."})

    file_bytes = uploaded_file.read()
    if not file_bytes:
        raise ValidationError({"file": "Uploaded file is empty."})

    if ext == ".xlsx":
        sheets, active_sheet, headers, sample = _inspect_xlsx(file_bytes)
    else:
        sheets, active_sheet, headers, sample = _inspect_csv(file_bytes)

    job_id = uuid.uuid4()
    dest_dir = Path(settings.MEDIA_ROOT) / "imports" / str(institution.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{job_id}{ext}"
    dest_path.write_bytes(file_bytes)

    suggested = suggest_column_mapping(headers)
    job = ImportJob.objects.create(
        id=job_id,
        institution=institution,
        created_by=user,
        file_name=original_name[:255],
        stored_file_path=str(dest_path),
        status=ImportJob.Status.UPLOADED,
        summary_json={
            "sheet_names": sheets,
            "selected_sheet": active_sheet,
            "headers": headers,
            "sample_rows": sanitize_audit_payload(sample),
            "suggested_mapping": suggested,
        },
    )

    log_audit_event(
        action="IMPORT_JOB_UPLOADED",
        entity_type="ImportJob",
        entity_id=job.id,
        institution=institution,
        actor_user=user,
        after={"file_name": job.file_name, "headers_count": len(headers)},
        request=request,
    )
    return job


def _evaluate_rows(
    *,
    institution: Institution,
    rows: list[tuple[int, dict[str, str]]],
    column_mapping: dict[str, str],
    default_cohort: Cohort | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate mapped rows against format, cohort, in-file duplicates, and DB uniqueness."""
    existing_reg_nos = {
        r.upper()
        for r in StudentProfile.objects.filter(institution=institution).values_list("registration_no", flat=True)
    }
    existing_inst_emails = {
        e.lower()
        for e in Membership.objects.filter(institution=institution).values_list("user__email", flat=True)
    }
    existing_global_emails = {
        e.lower() for e in User.objects.values_list("email", flat=True)
    }

    cohorts_by_key: dict[tuple[str, str, int, str], Cohort] = {}
    for c in Cohort.objects.filter(institution=institution).select_related("programme"):
        key = (
            c.programme.code.strip().upper(),
            c.batch_name.strip().lower(),
            int(c.semester),
            c.section.strip().upper(),
        )
        cohorts_by_key[key] = c

    seen_regs: set[str] = set()
    seen_emails: set[str] = set()

    valid_records: list[dict[str, Any]] = []
    error_entries: list[dict[str, Any]] = []
    preview_rows: list[dict[str, Any]] = []

    for row_number, raw_row in rows:
        mapped: dict[str, str] = {}
        for target_field in ALL_IMPORT_FIELDS:
            src_header = column_mapping.get(target_field)
            mapped[target_field] = raw_row.get(src_header, "").strip() if src_header else ""

        row_errors: list[dict[str, str]] = []

        reg_no = mapped["registration_no"].upper()
        email = mapped["email"].lower()
        first_name = mapped["first_name"]

        if not reg_no:
            row_errors.append({"field": "registration_no", "code": "REQUIRED_FIELD", "message": "Registration number is required."})
        if not email:
            row_errors.append({"field": "email", "code": "REQUIRED_FIELD", "message": "Email address is required."})
        else:
            try:
                validate_email(email)
            except DjangoValidationError:
                row_errors.append({"field": "email", "code": "INVALID_EMAIL", "message": f"Invalid email format: '{email}'."})

        if not first_name:
            row_errors.append({"field": "first_name", "code": "REQUIRED_FIELD", "message": "First name is required."})

        admission_year: int | None = None
        if mapped["admission_year"]:
            try:
                admission_year = int(float(mapped["admission_year"]))
                if not (1990 <= admission_year <= 2100):
                    raise ValueError()
            except ValueError:
                row_errors.append({"field": "admission_year", "code": "INVALID_NUMBER", "message": "Admission year must be between 1990 and 2100."})

        resolved_cohort = default_cohort
        has_cohort_cols = any(mapped[k] for k in ("programme_code", "batch_name", "semester"))
        if has_cohort_cols:
            prog_code = mapped["programme_code"].upper()
            batch_name = mapped["batch_name"].lower()
            sec = (mapped["section"] or "A").upper()
            try:
                sem = int(float(mapped["semester"]))
            except ValueError:
                sem = -1
            if not prog_code or not batch_name or sem < 1 or sem > 8:
                row_errors.append({
                    "field": "cohort",
                    "code": "INVALID_COHORT_DATA",
                    "message": "Cohort lookup requires valid programme_code, batch_name, and semester (1-8).",
                })
            else:
                matched = cohorts_by_key.get((prog_code, batch_name, sem, sec))
                if matched is None:
                    row_errors.append({
                        "field": "cohort",
                        "code": "COHORT_NOT_FOUND",
                        "message": f"No matching cohort found for {prog_code} / {mapped['batch_name']} / Sem {sem} / Sec {sec}.",
                    })
                else:
                    resolved_cohort = matched

        if reg_no:
            if reg_no in seen_regs:
                row_errors.append({"field": "registration_no", "code": "DUPLICATE_IN_FILE", "message": f"Duplicate registration number '{reg_no}' within file."})
            elif reg_no in existing_reg_nos:
                row_errors.append({"field": "registration_no", "code": "DUPLICATE_REGISTRATION_NO", "message": f"Registration number '{reg_no}' already exists in this institution."})

        if email:
            if email in seen_emails:
                row_errors.append({"field": "email", "code": "DUPLICATE_IN_FILE", "message": f"Duplicate email '{email}' within file."})
            elif email in existing_inst_emails:
                row_errors.append({"field": "email", "code": "DUPLICATE_EMAIL", "message": f"Email '{email}' is already a member of this institution."})
            elif email in existing_global_emails:
                row_errors.append({"field": "email", "code": "EMAIL_CONFLICT", "message": f"Email '{email}' is already registered on the platform."})

        if reg_no:
            seen_regs.add(reg_no)
        if email:
            seen_emails.add(email)

        safe_row_data = sanitize_audit_payload(mapped)
        if row_errors:
            for err in row_errors:
                error_entries.append({
                    "row_number": row_number,
                    "field_name": err["field"],
                    "error_code": err["code"],
                    "message": err["message"],
                    "row_data": safe_row_data,
                })
            if len(preview_rows) < 100:
                preview_rows.append({
                    "row_number": row_number,
                    "status": "error",
                    "data": safe_row_data,
                    "errors": row_errors,
                })
        else:
            valid_records.append({
                "row_number": row_number,
                "registration_no": reg_no,
                "email": email,
                "first_name": first_name,
                "last_name": mapped["last_name"],
                "cohort_id": resolved_cohort.id if resolved_cohort else None,
                "cohort_label": str(resolved_cohort) if resolved_cohort else None,
                "admission_year": admission_year,
                "phone": mapped["phone"],
            })
            if len(preview_rows) < 100:
                preview_rows.append({
                    "row_number": row_number,
                    "status": "valid",
                    "data": {**safe_row_data, "cohort_label": str(resolved_cohort) if resolved_cohort else ""},
                    "errors": [],
                })

    return valid_records, error_entries, preview_rows


@transaction.atomic
def validate_import_job(
    *,
    import_job: ImportJob,
    column_mapping: dict[str, str],
    sheet_name: str | None = None,
    default_cohort_id=None,
    actor_user=None,
    request=None,
) -> dict[str, Any]:
    if import_job.status == ImportJob.Status.COMMITTED:
        raise ValidationError({"status": "This import job has already been committed."})

    missing_required = [f for f in REQUIRED_IMPORT_FIELDS if not column_mapping.get(f)]
    if missing_required:
        raise ValidationError({
            "column_mapping": f"Missing required column mappings: {', '.join(missing_required)}"
        })

    default_cohort = None
    if default_cohort_id:
        default_cohort = Cohort.objects.filter(institution=import_job.institution, id=default_cohort_id).first()
        if default_cohort is None:
            raise ValidationError({"default_cohort_id": "Default cohort not found in active institution."})

    stored_path = Path(import_job.stored_file_path)
    if not stored_path.exists():
        raise ValidationError({"file": "Uploaded import file is no longer available on disk."})

    _, rows = _read_all_rows(stored_path, sheet_name=sheet_name)
    if not rows:
        raise ValidationError({"file": "No data rows found in the uploaded file."})

    valid_records, error_entries, preview_rows = _evaluate_rows(
        institution=import_job.institution,
        rows=rows,
        column_mapping=column_mapping,
        default_cohort=default_cohort,
    )

    ImportRowError.objects.filter(import_job=import_job).delete()
    if error_entries:
        ImportRowError.objects.bulk_create([
            ImportRowError(
                import_job=import_job,
                row_number=e["row_number"],
                field_name=e["field_name"],
                error_code=e["error_code"],
                message=e["message"],
                row_data=e["row_data"],
            )
            for e in error_entries
        ])

    failed_row_numbers = {e["row_number"] for e in error_entries}
    import_job.status = ImportJob.Status.VALIDATED
    import_job.total_rows = len(rows)
    import_job.success_rows = len(valid_records)
    import_job.error_rows = len(failed_row_numbers)
    import_job.summary_json = {
        **(import_job.summary_json or {}),
        "selected_sheet": sheet_name or (import_job.summary_json or {}).get("selected_sheet"),
        "column_mapping": column_mapping,
        "default_cohort_id": str(default_cohort.id) if default_cohort else None,
        "valid_rows_count": len(valid_records),
        "error_rows_count": len(failed_row_numbers),
    }
    import_job.save()

    log_audit_event(
        action="IMPORT_JOB_VALIDATED",
        entity_type="ImportJob",
        entity_id=import_job.id,
        institution=import_job.institution,
        actor_user=actor_user,
        after={
            "total_rows": import_job.total_rows,
            "valid_rows": import_job.success_rows,
            "error_rows": import_job.error_rows,
        },
        request=request,
    )
    return {
        "job": import_job,
        "preview_rows": preview_rows,
    }


def commit_import_job(
    *,
    import_job: ImportJob,
    mode: str = "skip_invalid",
    actor_user=None,
    request=None,
) -> ImportJob:
    if import_job.status != ImportJob.Status.VALIDATED:
        raise ValidationError({"status": "Only a validated import job can be committed."})
    if mode not in {"skip_invalid", "all_or_nothing"}:
        raise ValidationError({"mode": "Mode must be 'skip_invalid' or 'all_or_nothing'."})

    summary = import_job.summary_json or {}
    column_mapping = summary.get("column_mapping") or {}
    sheet_name = summary.get("selected_sheet")
    default_cohort_id = summary.get("default_cohort_id")

    default_cohort = None
    if default_cohort_id:
        default_cohort = Cohort.objects.filter(institution=import_job.institution, id=default_cohort_id).first()

    stored_path = Path(import_job.stored_file_path)
    _, rows = _read_all_rows(stored_path, sheet_name=sheet_name)

    try:
        with transaction.atomic():
            valid_records, error_entries, _ = _evaluate_rows(
                institution=import_job.institution,
                rows=rows,
                column_mapping=column_mapping,
                default_cohort=default_cohort,
            )

            if mode == "all_or_nothing" and error_entries:
                raise ValidationError({
                    "mode": f"Strict all-or-nothing commit aborted because {len({e['row_number'] for e in error_entries})} row(s) have errors."
                })

            ImportRowError.objects.filter(import_job=import_job).delete()
            if error_entries:
                ImportRowError.objects.bulk_create([
                    ImportRowError(
                        import_job=import_job,
                        row_number=e["row_number"],
                        field_name=e["field_name"],
                        error_code=e["error_code"],
                        message=e["message"],
                        row_data=e["row_data"],
                    )
                    for e in error_entries
                ])

            student_role = Role.objects.get(code=ROLE_STUDENT)
            created_count = 0
            for rec in valid_records:
                user = User.objects.create_user(
                    email=rec["email"],
                    password=None,  # Unusable password; requires secure reset/onboarding link
                    first_name=rec["first_name"],
                    last_name=rec["last_name"],
                    is_active=True,
                    must_change_password=True,
                )
                membership = Membership.objects.create(
                    institution=import_job.institution,
                    user=user,
                    status=Membership.Status.ACTIVE,
                )
                MembershipRole.objects.create(
                    membership=membership,
                    role=student_role,
                    assigned_by=actor_user if getattr(actor_user, "is_authenticated", False) else None,
                )
                StudentProfile.objects.create(
                    institution=import_job.institution,
                    membership=membership,
                    cohort_id=rec["cohort_id"],
                    registration_no=rec["registration_no"],
                    admission_year=rec["admission_year"],
                    phone=rec["phone"],
                    status=StudentProfile.Status.ACTIVE,
                )
                created_count += 1

            skipped_count = len({e["row_number"] for e in error_entries})
            import_job.status = ImportJob.Status.COMMITTED
            import_job.total_rows = len(rows)
            import_job.success_rows = created_count
            import_job.error_rows = skipped_count
            import_job.summary_json = {
                **summary,
                "mode": mode,
                "created_rows": created_count,
                "skipped_rows": skipped_count,
                "failed_rows": skipped_count,
            }
            import_job.save()

            log_audit_event(
                action="IMPORT_JOB_COMMITTED",
                entity_type="ImportJob",
                entity_id=import_job.id,
                institution=import_job.institution,
                actor_user=actor_user,
                after={
                    "file_name": import_job.file_name,
                    "created_rows": created_count,
                    "skipped_rows": skipped_count,
                },
                request=request,
            )
    except ValidationError:
        raise
    except Exception as exc:
        import_job.status = ImportJob.Status.FAILED
        import_job.summary_json = {**summary, "failure_reason": str(exc)}
        import_job.save(update_fields=["status", "summary_json", "updated_at"])
        log_audit_event(
            action="IMPORT_JOB_FAILED",
            entity_type="ImportJob",
            entity_id=import_job.id,
            institution=import_job.institution,
            actor_user=actor_user,
            after={"file_name": import_job.file_name, "error": str(exc)},
            request=request,
        )
        raise ValidationError({"import": "Import transaction failed and was rolled back safely."})

    return import_job


def _sanitize_csv_cell(value: Any) -> str:
    """Prevent CSV formula injection by prefixing risky leading characters."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


def export_import_errors_csv(import_job: ImportJob) -> str:
    """Export row-level errors to CSV without exposing any passwords or tokens."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "row_number",
        "field_name",
        "error_code",
        "message",
        "registration_no",
        "email",
        "first_name",
        "last_name",
    ])
    for err in import_job.row_errors.all().order_by("row_number"):
        rd = err.row_data or {}
        writer.writerow([
            err.row_number,
            _sanitize_csv_cell(err.field_name),
            _sanitize_csv_cell(err.error_code),
            _sanitize_csv_cell(err.message),
            _sanitize_csv_cell(rd.get("registration_no", "")),
            _sanitize_csv_cell(rd.get("email", "")),
            _sanitize_csv_cell(rd.get("first_name", "")),
            _sanitize_csv_cell(rd.get("last_name", "")),
        ])
    return buf.getvalue()

