from __future__ import annotations

from typing import Any, Dict

import frappe
from frappe import _

from school_statements.school_statements.utils.student_statement import (
    build_statement_context,
    get_students_for_batch,
    render_batch_pdf_file,
    render_statement_zip_file,
)

ALLOWED_ROLES = {
    "System Manager",
    "Accounts Manager",
    "Accounts User",
    "Education Manager",
    "School Administrator",
}


def _parse_filters(filters: Any) -> Dict[str, Any]:
    if not filters:
        return {}
    if isinstance(filters, dict):
        return filters
    if isinstance(filters, str):
        return frappe.parse_json(filters) or {}
    raise frappe.ValidationError(_("Invalid filters payload."))


def _assert_permission() -> None:
    roles = set(frappe.get_roles())
    if not (roles & ALLOWED_ROLES):
        frappe.throw(_("You do not have permission to generate statements."), frappe.PermissionError)


@frappe.whitelist()
def download_student_statements_zip(filters=None):
    _assert_permission()
    parsed_filters = _parse_filters(filters)
    file_doc = render_statement_zip_file(parsed_filters)
    return {
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
    }


@frappe.whitelist()
def download_student_statements_merged_pdf(filters=None):
    _assert_permission()
    parsed_filters = _parse_filters(filters)
    file_doc = render_batch_pdf_file(parsed_filters)
    return {
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
    }


@frappe.whitelist()
def preview_student_statement(filters=None):
    _assert_permission()
    parsed_filters = _parse_filters(filters)
    customer = parsed_filters.get("customer")
    if not customer:
        frappe.throw(_("Student is required."))
    return build_statement_context(parsed_filters, customer)


@frappe.whitelist()
def get_batch_student_count(filters=None):
    _assert_permission()
    parsed_filters = _parse_filters(filters)
    students = get_students_for_batch(parsed_filters)
    return {"count": len(students)}