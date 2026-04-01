from frappe.tests.utils import FrappeTestCase

from school_statements.school_statements.utils.student_statement import validate_filters


class TestStudentStatementUtils(FrappeTestCase):
    def test_validate_filters_sets_defaults(self):
        filters = validate_filters({"company": "_Test Company"})
        self.assertTrue(filters.get("report_date"))
        self.assertTrue(filters.get("from_date"))
        self.assertTrue(filters.get("to_date"))
