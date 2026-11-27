# Copyright (c) 2026, sanskar technolab and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ServiceRequest(Document):
	# ---------- Save se pehle ----------
	def before_validate(self):
		# Data saaf karo (validation se pehle)
		if self.description:
			self.description = self.description.strip()

	def validate(self):
		# Rules aur calculations: DB me likhne se PEHLE
		self.validate_sla_date()
		self.validate_spare_parts()
		self.validate_status_change()
		self.calculate_part_amounts()

	def validate_sla_date(self):
		if self.sla_date and self.request_date:
			if getdate(self.sla_date) < getdate(self.request_date):
				frappe.throw(_("SLA Date cannot be before Request Date"))

	def validate_spare_parts(self):
		for row in self.spare_parts:
			if (row.qty or 0) <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than 0").format(row.idx))
			if (row.rate or 0) < 0:
				frappe.throw(_("Row {0}: Rate cannot be negative").format(row.idx))

	def validate_status_change(self):
		if self.status == "In Progress" and not self.assigned_to:
			frappe.throw(_("Assign an Employee before moving to In Progress"))

		before = self.get_doc_before_save()  # save se pehle ka purana doc
		if before and self.has_value_changed("status"):
			if before.status == "Closed":
				frappe.throw(_("A Closed request cannot be reopened"))
			self.flags.status_changed = True  # sirf is save ke liye signal
			self.flags.old_status = before.status

	def calculate_part_amounts(self):
		for row in self.spare_parts:
			row.amount = (row.qty or 0) * (row.rate or 0)

	# ---------- Submit / Cancel ----------
	def before_submit(self):
		if not self.assigned_to:
			frappe.throw(_("Assign an Employee before submitting"))

	def on_submit(self):
		# Submit hote hi kaam shuru: seedha DB me status (hooks dobara nahi chalte)
		self.db_set("status", "In Progress")

	def on_cancel(self):
		self.add_comment("Info", _("Service Request was cancelled"))

	# ---------- Save ke baad ----------
	def on_update(self):
		# DB me save ho chuka hai, ab side-kaam
		if self.flags.get("status_changed"):
			try:
				self.add_comment(
					"Info",
					_("Status changed from {0} to {1}").format(self.flags.old_status, self.status),
				)
			except Exception:
				frappe.log_error(
					title="Service Request: status comment failed",
					message=frappe.get_traceback(),
				)
