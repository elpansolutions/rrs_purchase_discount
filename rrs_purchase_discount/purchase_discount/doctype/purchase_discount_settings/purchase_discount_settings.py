import frappe
from frappe.model.document import Document


class PurchaseDiscountSettings(Document):
	def validate(self):
		if self.enable_separate_discount_accounting:
			if not self.default_purchase_discount_account and not self.company_accounts:
				frappe.msgprint(
					frappe._(
						"Please specify a Default Purchase Discount Account or Company Specific Discount Accounts when separate discount accounting is enabled."
					),
					alert=True,
				)


def get_purchase_discount_account(company=None):
	settings = frappe.get_cached_doc("Purchase Discount Settings")
	if not settings.enable_purchase_item_discount or not settings.enable_separate_discount_accounting:
		return None

	if company and settings.company_accounts:
		for row in settings.company_accounts:
			if row.company == company and row.purchase_discount_account:
				return row.purchase_discount_account

	return settings.default_purchase_discount_account or None
