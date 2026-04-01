frappe.query_reports["Student Statement Detail"] = {
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
            reqd: 1,
        },
    ],

    onload(report) {
        report.page.add_inner_button(__("Download PDF"), async () => {
            const filters = report.get_values();
            if (!filters.customer) {
                frappe.msgprint(__("Select a Student first."));
                return;
            }

            frappe.dom.freeze(__("Generating statement..."));
            try {
                const response = await frappe.call({
                    method: "school_statements.school_statements.api.download_student_statements_merged_pdf",
                    args: {
                        filters: {
                            company: filters.company,
                            report_date: filters.report_date,
                            from_date: filters.from_date,
                            to_date: filters.to_date,
                            customer: filters.customer,
                        },
                    },
                });

                const payload = response.message || {};
                if (payload.file_url) {
                    window.open(payload.file_url, "_blank");
                } else {
                    frappe.msgprint(__("No PDF URL was returned."));
                }
            } finally {
                frappe.dom.unfreeze();
            }
        });
    },
};
