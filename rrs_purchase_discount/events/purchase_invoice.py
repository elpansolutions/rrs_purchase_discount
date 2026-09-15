import json
import frappe
from frappe import _
from frappe.utils import cint, flt, round_based_on_smallest_currency_fraction
from erpnext.controllers.taxes_and_totals import (
	get_item_tax_map,
	_get_item_tax_template,
	ItemDetailsCtx,
)


def validate_purchase_invoice(doc, method=None):
	"""
	Hook for Purchase Invoice validate event.
	Enforces item-level discount calculations while strictly preserving the original item Rate.
	Both Discount % and Flat Discount Amount are independent.
	"""
	settings = frappe.get_cached_doc("Purchase Discount Settings")
	if not cint(settings.enable_purchase_item_discount):
		return

	has_custom_discount = False
	total_custom_discount = 0.0
	conversion_rate = flt(doc.conversion_rate or 1.0)

	for item in doc.get("items", []):
		# Calculate gross amount (Qty * Rate)
		gross_amount = flt(
			flt(item.qty) * flt(item.rate),
			item.precision("custom_item_gross_amount") or item.precision("amount") or 2,
		)

		disc_pct = flt(item.get("custom_item_discount_percentage") or 0.0)
		disc_amt = flt(item.get("custom_item_discount_amount") or 0.0)

		# Validation rules
		if disc_amt < 0 or disc_pct < 0:
			frappe.throw(
				_("Row #{0}: Item Discount cannot be negative.").format(item.idx),
				title=_("Invalid Discount"),
			)

		if disc_pct > 100:
			frappe.throw(
				_("Row #{0}: Item Discount percentage cannot exceed 100%.").format(item.idx),
				title=_("Invalid Discount"),
			)

		# Compute total row discount from both independent inputs
		pct_discount = (
			flt(gross_amount * (disc_pct / 100.0), item.precision("custom_item_discount_amount") or 2)
			if disc_pct > 0
			else 0.0
		)
		total_row_disc = flt(
			pct_discount + disc_amt,
			item.precision("custom_item_discount_amount") or 2,
		)

		if total_row_disc > gross_amount:
			frappe.throw(
				_(
					"Row #{0}: Total Item Discount ({1}) cannot be greater than Item Gross Amount ({2})."
				).format(item.idx, total_row_disc, gross_amount),
				title=_("Discount Exceeds Gross Amount"),
			)

		# Clear native discount fields if custom discount is active
		if total_row_disc > 0:
			item.discount_percentage = 0.0
			item.discount_amount = 0.0

		net_amount = flt(
			gross_amount - total_row_disc,
			item.precision("custom_item_net_amount") or item.precision("net_amount") or 2,
		)

		# Store values (Preserving user's % and flat amount inputs independently)
		item.custom_item_gross_amount = gross_amount
		item.custom_item_discount_amount = disc_amt
		item.custom_item_discount_percentage = disc_pct
		item.custom_item_net_amount = net_amount

		if total_row_disc > 0:
			has_custom_discount = True
			total_custom_discount += total_row_disc

		# Invariant: item.rate and item.base_rate are NEVER modified
		item.net_amount = net_amount
		item.base_net_amount = flt(
			net_amount * conversion_rate,
			item.precision("base_net_amount") or 2,
		)

		item.net_rate = (
			flt(net_amount / item.qty, item.precision("net_rate") or 2)
			if flt(item.qty)
			else 0.0
		)
		item.base_net_rate = flt(
			item.net_rate * conversion_rate,
			item.precision("base_net_rate") or 2,
		)

	doc.custom_total_item_discount = flt(
		total_custom_discount,
		doc.precision("custom_total_item_discount") or 2,
	)

	# If custom discounts are present, recalculate taxes and totals accurately
	if has_custom_discount:
		recalculate_purchase_invoice_taxes_and_totals(doc)


def recalculate_purchase_invoice_taxes_and_totals(doc):
	"""
	Recalculates net total, taxes (On Net Total, etc.), grand total, rounded total,
	and India Compliance GST values using the discounted item net amounts.
	"""
	conversion_rate = flt(doc.conversion_rate or 1.0)

	# 1. Recalculate Net Totals
	doc.net_total = sum(flt(d.net_amount) for d in doc.get("items", []))
	doc.base_net_total = flt(
		doc.net_total * conversion_rate,
		doc.precision("base_net_total") or 2,
	)

	doc.total = sum(flt(d.custom_item_gross_amount or d.amount) for d in doc.get("items", []))
	doc.base_total = flt(
		doc.total * conversion_rate,
		doc.precision("base_total") or 2,
	)

	# 2. Recalculate Taxes
	if doc.get("taxes"):
		# Reset tax running totals
		for tax in doc.get("taxes"):
			tax.tax_amount = 0.0
			tax.total = 0.0
			tax.tax_amount_after_discount_amount = 0.0
			tax.base_tax_amount = 0.0
			tax.base_tax_amount_after_discount_amount = 0.0
			tax.base_total = 0.0
			tax.net_amount = 0.0

		doc._item_wise_tax_details = []

		for item in doc.get("items", []):
			item_tax_map = {}
			if item.get("item_tax_rate"):
				try:
					item_tax_map = json.loads(item.item_tax_rate)
				except Exception:
					item_tax_map = {}

			for i, tax in enumerate(doc.get("taxes")):
				tax_rate = flt(item_tax_map.get(tax.account_head, tax.rate))
				current_tax_amount = 0.0
				current_net_amount = 0.0

				if tax.charge_type == "On Net Total":
					current_net_amount = flt(item.net_amount)
					current_tax_amount = flt((tax_rate / 100.0) * current_net_amount)
				elif tax.charge_type == "Actual":
					current_net_amount = flt(item.net_amount)
					if doc.net_total:
						current_tax_amount = flt(
							item.net_amount * flt(tax.tax_amount) / doc.net_total
						)
				elif tax.charge_type == "On Item Quantity":
					current_tax_amount = flt(tax_rate * flt(item.qty))

				tax.tax_amount += current_tax_amount
				tax.net_amount += current_net_amount
				tax.tax_amount_after_discount_amount += current_tax_amount

		# Cumulative totals for taxes
		for i, tax in enumerate(doc.get("taxes")):
			tax.tax_amount = flt(tax.tax_amount, doc.precision("tax_amount", tax) or 2)
			tax.tax_amount_after_discount_amount = flt(
				tax.tax_amount_after_discount_amount, doc.precision("tax_amount", tax) or 2
			)
			tax.base_tax_amount = flt(tax.tax_amount * conversion_rate, doc.precision("base_tax_amount", tax) or 2)
			tax.base_tax_amount_after_discount_amount = flt(
				tax.tax_amount_after_discount_amount * conversion_rate,
				doc.precision("base_tax_amount_after_discount_amount", tax) or 2,
			)

			multiplier = -1.0 if (getattr(tax, "add_deduct_tax", None) == "Deduct") else 1.0
			tax_addition = tax.tax_amount_after_discount_amount * multiplier

			if i == 0:
				tax.total = flt(doc.net_total + tax_addition, doc.precision("total", tax) or 2)
			else:
				tax.total = flt(doc.get("taxes")[i - 1].total + tax_addition, doc.precision("total", tax) or 2)

			tax.base_total = flt(tax.total * conversion_rate, doc.precision("base_total", tax) or 2)

		doc.grand_total = flt(doc.get("taxes")[-1].total, doc.precision("grand_total") or 2)
		doc.total_taxes_and_charges = flt(
			doc.grand_total - doc.net_total,
			doc.precision("total_taxes_and_charges") or 2,
		)
	else:
		doc.grand_total = flt(doc.net_total, doc.precision("grand_total") or 2)
		doc.total_taxes_and_charges = 0.0

	doc.base_grand_total = flt(
		doc.grand_total * conversion_rate,
		doc.precision("base_grand_total") or 2,
	)
	doc.base_total_taxes_and_charges = flt(
		doc.total_taxes_and_charges * conversion_rate,
		doc.precision("base_total_taxes_and_charges") or 2,
	)

	# 3. Rounded Total
	if doc.meta.get_field("rounded_total"):
		if doc.get("disable_rounded_total"):
			doc.rounded_total = 0.0
			doc.rounding_adjustment = 0.0
			doc.base_rounded_total = 0.0
			doc.base_rounding_adjustment = 0.0
		else:
			doc.rounded_total = round_based_on_smallest_currency_fraction(
				doc.grand_total, doc.currency, doc.precision("rounded_total") or 2
			)
			doc.rounding_adjustment = flt(
				doc.rounded_total - doc.grand_total, doc.precision("rounding_adjustment") or 2
			)
			doc.base_rounded_total = flt(
				doc.rounded_total * conversion_rate, doc.precision("base_rounded_total") or 2
			)
			doc.base_rounding_adjustment = flt(
				doc.rounding_adjustment * conversion_rate,
				doc.precision("base_rounding_adjustment") or 2,
			)

	# 4. Total In Words
	if hasattr(doc, "set_total_in_words"):
		doc.set_total_in_words()

	# 5. India Compliance Integration
	update_india_compliance_taxable_values(doc)


def update_india_compliance_taxable_values(doc):
	"""
	Triggers India Compliance GST and taxable value updates if the app is installed.
	"""
	if "india_compliance" not in frappe.get_installed_apps():
		return

	try:
		from india_compliance.gst_india.overrides.transaction import (
			update_taxable_values,
			set_gst_breakup,
		)

		update_taxable_values(doc)
		set_gst_breakup(doc)
	except Exception as e:
		frappe.log_error(title="India Compliance Taxable Value Update Error", message=frappe.get_traceback())


def make_purchase_discount_gl_entries(gl_entries, doc):
	"""
	Hook to adjust GL Entries when separate discount accounting is enabled.
	If separate discount accounting is disabled, standard net booking is used.
	"""
	settings = frappe.get_cached_doc("Purchase Discount Settings")
	if not (settings.enable_purchase_item_discount and settings.enable_separate_discount_accounting):
		return gl_entries

	total_discount = flt(doc.get("custom_total_item_discount") or 0.0)
	if not total_discount:
		return gl_entries

	# Determine discount account
	from rrs_purchase_discount.purchase_discount.doctype.purchase_discount_settings.purchase_discount_settings import (
		get_purchase_discount_account,
	)

	discount_account = get_purchase_discount_account(doc.company)
	if not discount_account:
		return gl_entries

	conversion_rate = flt(doc.conversion_rate or 1.0)
	base_total_discount = flt(total_discount * conversion_rate, doc.precision("base_grand_total") or 2)

	# Increase expense debit entries by discount amount
	for gle in gl_entries:
		for item in doc.get("items", []):
			if gle.get("account") == item.expense_account:
				item_disc = flt(item.custom_item_gross_amount - item.custom_item_net_amount)
				if item_disc > 0:
					item_disc_base = flt(
						item_disc * conversion_rate,
						item.precision("base_net_amount") or 2,
					)
					if gle.get("debit"):
						gle["debit"] = flt(gle["debit"]) + item_disc_base
						gle["debit_in_account_currency"] = flt(gle.get("debit_in_account_currency", 0.0)) + item_disc
						gle["debit_in_transaction_currency"] = flt(gle.get("debit_in_transaction_currency", 0.0)) + item_disc

	# Add Credit entry for Purchase Discount Account
	account_currency = frappe.get_cached_value("Account", discount_account, "account_currency") or doc.company_currency
	credit_in_account_currency = base_total_discount if account_currency == doc.company_currency else total_discount

	gl_entries.append(
		doc.get_gl_dict(
			{
				"account": discount_account,
				"against": doc.supplier,
				"credit": base_total_discount,
				"credit_in_account_currency": credit_in_account_currency,
				"credit_in_transaction_currency": total_discount,
				"cost_center": doc.cost_center or erpnext.get_default_cost_center(doc.company),
				"project": doc.project,
				"remarks": _("Item Purchase Discount on {0}").format(doc.name),
			},
			account_currency,
			item=doc,
		)
	)

	return gl_entries
