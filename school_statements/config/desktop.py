from frappe import _

def get_data():
    return [
        {
            "module_name": "School Statements",
            "label": _("School Statements"),
            "color": "purple",
            "icon": "octicon octicon-file-directory",
            "type": "module",
            "description": _("Student statements, bulk downloads, and statement reporting"),
        }
    ]
