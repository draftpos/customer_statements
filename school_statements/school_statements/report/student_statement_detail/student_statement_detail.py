from __future__ import annotations

from frappe import _

from school_statements.school_statements.utils.student_statement import (
    build_statement_context,
    validate_filters,
)


def execute(filters=None):
    filters = validate_filters(filters or {})
    if not filters.get("customer"):
        return get_columns(), []

    context = build_statement_context(filters, filters["customer"])

    data = []
    for row in context["rows"]:
        data.append(
            {
                "posting_date": row["posting_date"],
                "description": row["description"],
                "voucher_type": row["voucher_type"],
                "reference_no": row["reference_no"],
                "debit": row["debit"],
                "credit": row["credit"],
                "running_balance": row["running_balance"],
            }
        )

    return get_columns(), data


def get_columns():
    return [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "fieldname": "description",
            "label": _("Description"),
            "fieldtype": "Data",
            "width": 260,
        },
        {
            "fieldname": "voucher_type",
            "label": _("Type"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "reference_no",
            "label": _("Ref No."),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "debit",
            "label": _("Dr"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "credit",
            "label": _("Cr"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "running_balance",
            "label": _("Balance"),
            "fieldtype": "Currency",
            "width": 140,
        },
    ]