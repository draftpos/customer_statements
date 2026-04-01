frappe.query_reports["Student Statement Control"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "report_date",
            label: __("Report Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "customer",
            label: __("Student"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "customer_group",
            label: __("Customer Group"),
            fieldtype: "Link",
            options: "Customer Group",
        },
        {
            fieldname: "grade",
            label: __("Grade"),
            fieldtype: "Data",
        },
        {
            fieldname: "student_class",
            label: __("Class"),
            fieldtype: "Data",
        },
    ],

    onload(report) {
        report.page.add_inner_button(__("Bulk Download ZIP"), async () => {
            await school_statements_bulk_action(report, "school_statements.school_statements.api.download_student_statements_zip");
        });

        report.page.add_inner_button(__("Bulk Print PDF"), async () => {
            await school_statements_bulk_action(report, "school_statements.school_statements.api.download_student_statements_merged_pdf");
        });

        report.page.add_inner_button(__("Open Single Student Statement"), async () => {
            const filters = report.get_values();
            if (!filters.customer) {
                frappe.msgprint(__("Select a Student filter first."));
                return;
            }

            frappe.set_route("query-report", "Student Statement Detail", {
                company: filters.company,
                customer: filters.customer,
                from_date: filters.from_date,
                to_date: filters.to_date,
                report_date: filters.report_date,
            });
        });
    },
};

async function school_statements_bulk_action(report, method) {
    const filters = report.get_values();

    frappe.dom.freeze(__("Preparing statements..."));

    try {
        const countResponse = await frappe.call({
            method: "school_statements.school_statements.api.get_batch_student_count",
            args: { filters: filters },
        });

        const count = (countResponse.message || {}).count || 0;
        if (!count) {
            frappe.msgprint(__("No students matched the selected filters."));
            return;
        }

        const response = await frappe.call({
            method: method,
            args: { filters: filters },
        });

        const payload = response.message || {};
        if (payload.file_url) {
            window.open(payload.file_url, "_blank");
        } else {
            frappe.msgprint(__("The file was generated but no download URL was returned."));
        }
    } finally {
        frappe.dom.unfreeze();
    }
}
