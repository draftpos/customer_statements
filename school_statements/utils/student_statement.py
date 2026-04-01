from __future__ import annotations

import io
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import cstr, flt, formatdate, now_datetime
from frappe.utils.pdf import get_pdf

GRADE_FIELD_CANDIDATES = ["grade", "student_grade", "school_grade", "custom_grade"]
CLASS_FIELD_CANDIDATES = ["class", "student_class", "school_class", "custom_class"]

DETAIL_TEMPLATE = "school_statements/templates/includes/student_statement_pdf.html"


def _field_exists(doctype: str, fieldname: str) -> bool:
    meta = frappe.get_meta(doctype)
    return bool(meta.get_field(fieldname))


def _first_existing_field(doctype: str, candidates: List[str]) -> Optional[str]:
    for fieldname in candidates:
        if _field_exists(doctype, fieldname):
            return fieldname
    return None


def get_customer_dimension_fields() -> Dict[str, Optional[str]]:
    return {
        "grade_field": _first_existing_field("Customer", GRADE_FIELD_CANDIDATES),
        "class_field": _first_existing_field("Customer", CLASS_FIELD_CANDIDATES),
    }


def validate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    filters = frappe._dict(filters or {})

    if not filters.get("company"):
        filters.company = frappe.defaults.get_user_default("Company")

    if not filters.get("company"):
        frappe.throw(_("Company is required."))

    if not filters.get("report_date"):
        filters.report_date = now_datetime().date().isoformat()

    if not filters.get("to_date"):
        filters.to_date = filters.report_date

    if not filters.get("from_date"):
        report_date_obj = frappe.utils.getdate(filters.report_date)
        filters.from_date = report_date_obj.replace(day=1).isoformat()

    if frappe.utils.getdate(filters.from_date) > frappe.utils.getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date."))

    return filters


def _customer_filter_sql(filters: Dict[str, Any], fields: Dict[str, Optional[str]]) -> Tuple[str, Dict[str, Any]]:
    conditions = []
    values = {
        "company": filters.get("company"),
        "report_date": filters.get("report_date"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
        "customer": filters.get("customer"),
        "customer_group": filters.get("customer_group"),
        "grade": filters.get("grade"),
        "student_class": filters.get("student_class"),
    }

    if filters.get("customer"):
        conditions.append("c.name = %(customer)s")

    if filters.get("customer_group"):
        conditions.append("c.customer_group = %(customer_group)s")

    if filters.get("grade") and fields.get("grade_field"):
        conditions.append(f"c.`{fields['grade_field']}` = %(grade)s")

    if filters.get("student_class") and fields.get("class_field"):
        conditions.append(f"c.`{fields['class_field']}` = %(student_class)s")

    clause = ""
    if conditions:
        clause = " AND " + " AND ".join(conditions)

    return clause, values


def get_students_for_batch(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    filters = validate_filters(filters)
    fields = get_customer_dimension_fields()
    clause, values = _customer_filter_sql(filters, fields)

    grade_select = f"c.`{fields['grade_field']}` AS grade" if fields.get("grade_field") else "NULL AS grade"
    class_select = f"c.`{fields['class_field']}` AS student_class" if fields.get("class_field") else "NULL AS student_class"

    rows = frappe.db.sql(
        f"""
        SELECT
            c.name AS customer,
            c.customer_name,
            c.customer_group,
            {grade_select},
            {class_select}
        FROM `tabCustomer` c
        WHERE c.disabled = 0
        {clause}
        ORDER BY c.customer_group, c.customer_name, c.name
        """,
        values,
        as_dict=True,
    )
    return rows


def _get_currency(company: str) -> str:
    return frappe.get_cached_value("Company", company, "default_currency") or frappe.defaults.get_global_default("currency")


def _get_party_opening_balance(company: str, customer: str, from_date: str) -> float:
    return flt(
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(gle.debit - gle.credit), 0)
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON acc.name = gle.account
            WHERE gle.company = %(company)s
              AND gle.party_type = 'Customer'
              AND gle.party = %(customer)s
              AND gle.is_cancelled = 0
              AND gle.posting_date < %(from_date)s
              AND acc.account_type = 'Receivable'
            """,
            {"company": company, "customer": customer, "from_date": from_date},
        )[0][0]
    )


def _get_party_closing_balance(company: str, customer: str, to_date: str) -> float:
    return flt(
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(gle.debit - gle.credit), 0)
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON acc.name = gle.account
            WHERE gle.company = %(company)s
              AND gle.party_type = 'Customer'
              AND gle.party = %(customer)s
              AND gle.is_cancelled = 0
              AND gle.posting_date <= %(to_date)s
              AND acc.account_type = 'Receivable'
            """,
            {"company": company, "customer": customer, "to_date": to_date},
        )[0][0]
    )


def _get_statement_entries(company: str, customer: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    rows = frappe.db.sql(
        """
        SELECT
            gle.name,
            gle.posting_date,
            gle.voucher_type,
            gle.voucher_no,
            gle.against_voucher_type,
            gle.against_voucher,
            gle.debit,
            gle.credit,
            gle.remarks
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.company = %(company)s
          AND gle.party_type = 'Customer'
          AND gle.party = %(customer)s
          AND gle.is_cancelled = 0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND acc.account_type = 'Receivable'
        ORDER BY gle.posting_date, gle.creation, gle.name
        """,
        {"company": company, "customer": customer, "from_date": from_date, "to_date": to_date},
        as_dict=True,
    )
    return rows


def _get_formatted_address_for_linked_party(link_doctype: str, link_name: str) -> str:
    result = frappe.db.sql(
        """
        SELECT a.name
        FROM `tabAddress` a
        INNER JOIN `tabDynamic Link` dl ON dl.parent = a.name
        WHERE dl.link_doctype = %(link_doctype)s
          AND dl.link_name = %(link_name)s
          AND a.disabled = 0
        ORDER BY a.is_primary_address DESC, a.modified DESC
        LIMIT 1
        """,
        {"link_doctype": link_doctype, "link_name": link_name},
        as_dict=True,
    )
    if not result:
        return ""
    return frappe.get_cached_value("Address", result[0]["name"], "display") or ""


def _get_company_logo(company: str) -> Optional[str]:
    if _field_exists("Company", "company_logo"):
        logo = frappe.db.get_value("Company", company, "company_logo")
        if logo:
            return logo
    return None


def _get_customer_details(customer: str, fields: Dict[str, Optional[str]]) -> Dict[str, Any]:
    customer_doc = frappe.get_cached_doc("Customer", customer)
    details = {
        "customer": customer_doc.name,
        "customer_name": customer_doc.customer_name,
        "customer_group": customer_doc.customer_group,
        "mobile_no": getattr(customer_doc, "mobile_no", None),
        "email_id": getattr(customer_doc, "email_id", None),
        "address": _get_formatted_address_for_linked_party("Customer", customer_doc.name),
        "grade": getattr(customer_doc, fields["grade_field"], None) if fields.get("grade_field") else None,
        "student_class": getattr(customer_doc, fields["class_field"], None) if fields.get("class_field") else None,
    }
    return details


def _get_school_details(company: str) -> Dict[str, Any]:
    company_doc = frappe.get_cached_doc("Company", company)
    return {
        "company": company_doc.name,
        "company_name": company_doc.company_name,
        "phone_no": getattr(company_doc, "phone_no", None),
        "email": getattr(company_doc, "email", None),
        "address": _get_formatted_address_for_linked_party("Company", company_doc.name),
        "logo": _get_company_logo(company_doc.name),
    }


def build_statement_rows(filters: Dict[str, Any], customer: str) -> Tuple[List[Dict[str, Any]], float, float]:
    filters = validate_filters(filters)
    company = filters["company"]
    from_date = filters["from_date"]
    to_date = filters["to_date"]

    opening_balance = _get_party_opening_balance(company, customer, from_date)
    transactions = _get_statement_entries(company, customer, from_date, to_date)

    rows: List[Dict[str, Any]] = []
    running_balance = flt(opening_balance)

    rows.append(
        {
            "posting_date": from_date,
            "display_date": formatdate(from_date),
            "voucher_type": "",
            "voucher_no": "",
            "reference_no": "",
            "description": "Balance b/d",
            "debit": opening_balance if opening_balance > 0 else 0,
            "credit": abs(opening_balance) if opening_balance < 0 else 0,
            "running_balance": running_balance,
            "is_opening": 1,
            "is_closing": 0,
        }
    )

    for entry in transactions:
        debit = flt(entry.get("debit"))
        credit = flt(entry.get("credit"))
        running_balance += debit - credit

        reference_no = entry.get("voucher_no")
        description = entry.get("remarks") or entry.get("voucher_type") or ""
        rows.append(
            {
                "posting_date": entry.get("posting_date"),
                "display_date": formatdate(entry.get("posting_date")),
                "voucher_type": entry.get("voucher_type"),
                "voucher_no": entry.get("voucher_no"),
                "reference_no": reference_no,
                "description": description,
                "debit": debit,
                "credit": credit,
                "running_balance": running_balance,
                "is_opening": 0,
                "is_closing": 0,
            }
        )

    closing_balance = _get_party_closing_balance(company, customer, to_date)
    rows.append(
        {
            "posting_date": to_date,
            "display_date": formatdate(to_date),
            "voucher_type": "",
            "voucher_no": "",
            "reference_no": "",
            "description": "Balance c/d",
            "debit": closing_balance if closing_balance > 0 else 0,
            "credit": abs(closing_balance) if closing_balance < 0 else 0,
            "running_balance": closing_balance,
            "is_opening": 0,
            "is_closing": 1,
        }
    )

    return rows, opening_balance, closing_balance


def build_statement_context(filters: Dict[str, Any], customer: str) -> Dict[str, Any]:
    filters = validate_filters(filters)
    fields = get_customer_dimension_fields()
    currency = _get_currency(filters["company"])

    rows, opening_balance, closing_balance = build_statement_rows(filters, customer)
    school = _get_school_details(filters["company"])
    student = _get_customer_details(customer, fields)

    context = {
        "title": "Student Statement",
        "filters": filters,
        "currency": currency,
        "school": school,
        "student": student,
        "rows": rows,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "generated_on": now_datetime(),
    }
    return context


def render_statement_html(filters: Dict[str, Any], customer: str) -> str:
    context = build_statement_context(filters, customer)
    return frappe.render_template(DETAIL_TEMPLATE, context)


def _save_private_file(file_name: str, content: bytes, is_private: int = 1):
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name,
            "content": content,
            "is_private": is_private,
        }
    )
    file_doc.save(ignore_permissions=True)
    return file_doc


def render_statement_pdf_bytes(filters: Dict[str, Any], customer: str) -> bytes:
    html = render_statement_html(filters, customer)
    return get_pdf(html)


def render_statement_zip_file(filters: Dict[str, Any]):
    filters = validate_filters(filters)
    students = get_students_for_batch(filters)

    if not students:
        frappe.throw(_("No students matched the selected filters."))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for student in students:
            pdf_bytes = render_statement_pdf_bytes(filters, student["customer"])
            safe_name = cstr(student.get("customer_name") or student["customer"]).replace("/", "-")
            zip_file.writestr(f"{safe_name}.pdf", pdf_bytes)

    zip_buffer.seek(0)
    class_bit = filters.get("student_class") or "all-classes"
    grade_bit = filters.get("grade") or "all-grades"
    file_name = f"Student Statements {filters['company']} {grade_bit} {class_bit}.zip"
    return _save_private_file(file_name, zip_buffer.read())


def render_batch_pdf_file(filters: Dict[str, Any]):
    filters = validate_filters(filters)
    students = get_students_for_batch(filters)

    if not students:
        frappe.throw(_("No students matched the selected filters."))

    statements_html: List[str] = []
    for idx, student in enumerate(students):
        html = render_statement_html(filters, student["customer"])
        if idx > 0:
            statements_html.append('<div style="page-break-before: always;"></div>')
        statements_html.append(html)

    merged_html = "".join(statements_html)
    pdf_bytes = get_pdf(merged_html)
    class_bit = filters.get("student_class") or "all-classes"
    grade_bit = filters.get("grade") or "all-grades"
    file_name = f"Student Statements {filters['company']} {grade_bit} {class_bit}.pdf"
    return _save_private_file(file_name, pdf_bytes)


def get_statement_summary_rows(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    filters = validate_filters(filters)
    fields = get_customer_dimension_fields()
    clause, values = _customer_filter_sql(filters, fields)

    grade_select = f"c.`{fields['grade_field']}` AS grade" if fields.get("grade_field") else "NULL AS grade"
    class_select = f"c.`{fields['class_field']}` AS student_class" if fields.get("class_field") else "NULL AS student_class"

    rows = frappe.db.sql(
        f"""
        SELECT
            gle.party AS customer,
            c.customer_name,
            c.customer_group,
            {grade_select},
            {class_select},
            COALESCE(SUM(gle.debit - gle.credit), 0) AS outstanding
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account
           AND acc.account_type = 'Receivable'
           AND acc.company = %(company)s
        INNER JOIN `tabCustomer` c
            ON c.name = gle.party
        WHERE gle.company = %(company)s
          AND gle.party_type = 'Customer'
          AND gle.is_cancelled = 0
          AND gle.posting_date <= %(report_date)s
          {clause}
        GROUP BY gle.party, c.customer_name, c.customer_group, grade, student_class
        HAVING ABS(COALESCE(SUM(gle.debit - gle.credit), 0)) > 0.0001
        ORDER BY c.customer_group, grade, student_class, c.customer_name
        """,
        values,
        as_dict=True,
    )
    return rows
