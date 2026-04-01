from __future__ import annotations

from frappe import _

from school_statements.school_statements.utils.student_statement import (
    get_customer_dimension_fields,
    get_statement_summary_rows,
    validate_filters,
)


def execute(filters=None):
    filters = validate_filters(filters or {})
    fields = get_customer_dimension_fields()

    columns = [
        {
            "fieldname": "customer",
            "label": _("Student"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180,
        },
        {
            "fieldname": "customer_name",
            "label": _("Student Name"),
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "fieldname": "customer_group",
            "label": _("Customer Group"),
            "fieldtype": "Link",
            "options": "Customer Group",
            "width": 160,
        },
    ]

    if fields.get("grade_field"):
        columns.append(
            {
                "fieldname": "grade",
                "label": _("Grade"),
                "fieldtype": "Data",
                "width": 120,
            }
        )

    if fields.get("class_field"):
        columns.append(
            {
                "fieldname": "student_class",
                "label": _("Class"),
                "fieldtype": "Data",
                "width": 120,
            }
        )

    columns.append(
        {
            "fieldname": "outstanding",
            "label": _("Outstanding"),
            "fieldtype": "Currency",
            "width": 150,
        }
    )

    return columns, get_statement_summary_rows(filters)