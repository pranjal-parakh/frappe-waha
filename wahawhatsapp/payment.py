import frappe

# from frappe.utils import nowdate

@frappe.whitelist(allow_guest=True)
def payment_confirmation():
    # data=frappe.request.get_json()
    # if data.get("status") == "1":

        session_doc = frappe.get_doc("user sessions", "916265064809@c.us")
        session_doc.payment_status = "paid"
        session_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return "OK done"

