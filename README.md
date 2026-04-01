# School Statements

A production-ready Frappe app for school fee statements built on ERPNext receivables.

## Features

- Student statement control report with filters for company, report date, customer, grade, class, and customer group
- Single student detailed statement report
- Bulk ZIP download of PDF statements
- Bulk merged PDF generation for class / grade / customer group
- Statement balances computed from receivable GL entries so the closing balance aligns with receivables
- Dynamic detection of grade and class custom fields on Customer

## Assumptions

- Each student is a Customer
- Customer Group is already used
- Grade and class fields already exist on Customer, under one of these fieldnames:

### Grade candidates
`grade`, `student_grade`, `school_grade`, `custom_grade`

### Class candidates
`class`, `student_class`, `school_class`, `custom_class`

If your fieldnames are different, update the lists in:
`school_statements/school_statements/utils/student_statement.py`

## Install

```bash
bench new-app school_statements
# replace scaffold with these files
bench --site yoursite install-app school_statements
bench --site yoursite migrate
bench build --app school_statements
```

## Reports

1. **Student Statement Control**
   - summary report
   - bulk buttons
2. **Student Statement Detail**
   - one student ledger style statement
   - PDF export button

## Security

Only users with one of these roles can generate statements:
- System Manager
- Accounts Manager
- Accounts User
- Education Manager
- School Administrator

Adjust `ALLOWED_ROLES` in `api.py` to fit your site.

## Notes

This app intentionally uses a dedicated custom report instead of patching the standard Accounts Receivable report, because overriding core ERPNext report behavior is more brittle during upgrades. The report is built as a standard Script Report inside the app, which is the recommended pattern in Frappe.
