import unittest
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today, nowdate


class TestPurchaseDiscount(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or "_Test Company"
		if not frappe.db.exists("Company", self.company):
			comp = frappe.get_doc({
				"doctype": "Company",
				"company_name": self.company,
				"abbr": "_TC",
				"default_currency": "INR",
				"country": "India",
			})
			comp.insert(ignore_permissions=True, ignore_if_duplicate=True)

		# Ensure Settings enabled
		settings = frappe.get_single_value("Purchase Discount Settings", "enable_purchase_item_discount")
		if not settings:
			frappe.db.set_single_value("Purchase Discount Settings", "enable_purchase_item_discount", 1)

		# Ensure test supplier
		self.supplier = "_Test Purchase Discount Supplier"
		if not frappe.db.exists("Supplier", self.supplier):
			supp = frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": self.supplier,
				"supplier_group": "All Supplier Groups",
			})
			supp.insert(ignore_permissions=True, ignore_if_duplicate=True)

		# Ensure test items
		self.item1 = self.create_test_item("_Test Item Discount 1")
		self.item2 = self.create_test_item("_Test Item Discount 2")

	def create_test_item(self, item_code):
		if not frappe.db.exists("Item", item_code):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"gst_hsn_code": "01023100",
			})
			item.insert(ignore_permissions=True, ignore_if_duplicate=True)
		return item_code

	def create_purchase_invoice(self, items_data, do_not_save=False):
		pi = frappe.new_doc("Purchase Invoice")
		pi.company = self.company
		pi.supplier = self.supplier
		pi.currency = "INR"
		pi.conversion_rate = 1.0
		pi.bill_no = f"BILL-{frappe.generate_hash(length=8)}"
		pi.bill_date = today()
		pi.posting_date = today()

		for d in items_data:
			pi.append("items", {
				"item_code": d.get("item_code", self.item1),
				"qty": d.get("qty", 1),
				"rate": d.get("rate", 100),
				"custom_item_discount_amount": d.get("custom_item_discount_amount", 0),
				"custom_item_discount_percentage": d.get("custom_item_discount_percentage", 0),
				"expense_account": d.get("expense_account") or frappe.get_cached_value("Company", self.company, "default_expense_account"),
				"cost_center": frappe.get_cached_value("Company", self.company, "cost_center"),
			})

		if not do_not_save:
			pi.save()
		return pi

	def test_01_rate_preservation_with_flat_discount(self):
		"""
		TEST 1:
		qty = 1500, rate = 123, discount = 3000
		Expected:
		rate = 123 (unchanged)
		gross = 184500
		net = 181500
		discount % calculated = 1.626%
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 1500,
			"rate": 123,
			"custom_item_discount_amount": 3000,
		}])

		item = pi.items[0]
		self.assertEqual(flt(item.rate), 123.0, "Rate must remain exactly 123")
		self.assertEqual(flt(item.custom_item_gross_amount), 184500.0)
		self.assertEqual(flt(item.custom_item_discount_amount), 3000.0)
		self.assertEqual(flt(item.custom_item_net_amount), 181500.0)
		self.assertEqual(flt(item.net_amount), 181500.0)
		self.assertEqual(flt(pi.net_total), 181500.0)
		self.assertEqual(flt(pi.custom_total_item_discount), 3000.0)

	def test_02_zero_discount(self):
		"""
		TEST 2:
		qty = 100, rate = 500, discount = 0
		Expected:
		rate = 500, gross = 50000, net = 50000
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 100,
			"rate": 500,
			"custom_item_discount_amount": 0,
		}])

		item = pi.items[0]
		self.assertEqual(flt(item.rate), 500.0)
		self.assertEqual(flt(item.custom_item_gross_amount), 50000.0)
		self.assertEqual(flt(item.custom_item_net_amount), 50000.0)
		self.assertEqual(flt(item.net_amount), 50000.0)
		self.assertEqual(flt(pi.net_total), 50000.0)

	def test_03_rate_preservation_partial_discount(self):
		"""
		TEST 3:
		qty = 10, rate = 100, discount = 100
		Expected:
		rate = 100, gross = 1000, net = 900
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 10,
			"rate": 100,
			"custom_item_discount_amount": 100,
		}])

		item = pi.items[0]
		self.assertEqual(flt(item.rate), 100.0)
		self.assertEqual(flt(item.custom_item_gross_amount), 1000.0)
		self.assertEqual(flt(item.custom_item_discount_amount), 100.0)
		self.assertEqual(flt(item.custom_item_net_amount), 900.0)
		self.assertEqual(flt(item.net_amount), 900.0)
		self.assertEqual(flt(pi.net_total), 900.0)

	def test_04_discount_exceeding_gross_throws_error(self):
		"""
		TEST 4:
		qty = 10, rate = 100 (gross = 1000), discount = 1500
		Expected: ValidationError
		"""
		with self.assertRaises(frappe.ValidationError):
			self.create_purchase_invoice([{
				"item_code": self.item1,
				"qty": 10,
				"rate": 100,
				"custom_item_discount_amount": 1500,
			}])

	def test_05_negative_discount_throws_error(self):
		"""
		TEST 5:
		qty = 10, rate = 100, discount = -10
		Expected: ValidationError
		"""
		with self.assertRaises(frappe.ValidationError):
			self.create_purchase_invoice([{
				"item_code": self.item1,
				"qty": 10,
				"rate": 100,
				"custom_item_discount_amount": -10,
			}])

	def test_06_percentage_above_100_throws_error(self):
		"""
		Discount % > 100% throws ValidationError
		"""
		with self.assertRaises(frappe.ValidationError):
			self.create_purchase_invoice([{
				"item_code": self.item1,
				"qty": 10,
				"rate": 100,
				"custom_item_discount_percentage": 105.0,
			}])

	def test_07_multiple_items_with_varying_discounts(self):
		"""
		TEST 6:
		Item 1: Qty = 10, Rate = ₹100, Discount = ₹50 -> Net = ₹950
		Item 2: Qty = 5, Rate = ₹200, Discount = ₹100 -> Net = ₹900
		Invoice item total should be: ₹1,850
		"""
		pi = self.create_purchase_invoice([
			{
				"item_code": self.item1,
				"qty": 10,
				"rate": 100,
				"custom_item_discount_amount": 50,
			},
			{
				"item_code": self.item2,
				"qty": 5,
				"rate": 200,
				"custom_item_discount_amount": 100,
			},
		])

		self.assertEqual(flt(pi.items[0].rate), 100.0)
		self.assertEqual(flt(pi.items[0].custom_item_net_amount), 950.0)
		self.assertEqual(flt(pi.items[1].rate), 200.0)
		self.assertEqual(flt(pi.items[1].custom_item_net_amount), 900.0)
		self.assertEqual(flt(pi.net_total), 1850.0)
		self.assertEqual(flt(pi.custom_total_item_discount), 150.0)

	def test_08_gst_applied_to_discounted_taxable_amount(self):
		"""
		TEST 7:
		Gross = 184500, Discount = 3000 -> Taxable = 181500
		GST 5% = 9075 (not 9225)
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 1500,
			"rate": 123,
			"custom_item_discount_amount": 3000,
		}], do_not_save=True)

		tax_acc = frappe.get_cached_value("Company", self.company, "default_payable_account") or "Taxes - _TC"
		pi.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": tax_acc,
			"description": "GST 5%",
			"rate": 5.0,
		})
		pi.save()

		self.assertEqual(flt(pi.net_total), 181500.0)
		self.assertEqual(flt(pi.taxes[0].tax_amount), 9075.0)
		self.assertEqual(flt(pi.grand_total), 190575.0)

	def test_09_in_state_gst(self):
		"""
		TEST 8: In-State GST (CGST 2.5% + SGST 2.5%)
		Gross = 184500, Discount = 3000, Net = 181500
		CGST = 4537.50, SGST = 4537.50, Grand Total = 190575
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 1500,
			"rate": 123,
			"custom_item_discount_amount": 3000,
		}], do_not_save=True)

		tax_acc = frappe.get_cached_value("Company", self.company, "default_payable_account") or "Taxes - _TC"
		pi.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": tax_acc,
			"description": "Input Tax CGST",
			"rate": 2.5,
		})
		pi.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": tax_acc,
			"description": "Input Tax SGST",
			"rate": 2.5,
		})
		pi.save()

		self.assertEqual(flt(pi.net_total), 181500.0)
		self.assertEqual(flt(pi.taxes[0].tax_amount), 4537.50)
		self.assertEqual(flt(pi.taxes[1].tax_amount), 4537.50)
		self.assertEqual(flt(pi.grand_total), 190575.0)

	def test_10_out_state_gst_igst(self):
		"""
		TEST 9: Out-State GST (IGST 5.0%)
		Gross = 184500, Discount = 3000, Net = 181500
		IGST = 9075.0, Grand Total = 190575
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 1500,
			"rate": 123,
			"custom_item_discount_amount": 3000,
		}], do_not_save=True)

		tax_acc = frappe.get_cached_value("Company", self.company, "default_payable_account") or "Taxes - _TC"
		pi.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": tax_acc,
			"description": "Input Tax IGST",
			"rate": 5.0,
		})
		pi.save()

		self.assertEqual(flt(pi.net_total), 181500.0)
		self.assertEqual(flt(pi.taxes[0].tax_amount), 9075.0)
		self.assertEqual(flt(pi.grand_total), 190575.0)

	def test_11_submit_and_cancel_gl_entries_balanced(self):
		"""
		TEST 10 & 11:
		Submit Purchase Invoice -> verify GL entries balance.
		Cancel Purchase Invoice -> verify cancellation.
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 10,
			"rate": 100,
			"custom_item_discount_amount": 100,
		}])

		expense_acc = pi.items[0].expense_account
		supplier_acc = pi.credit_to

		if expense_acc and supplier_acc:
			pi.submit()
			gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": pi.name, "is_cancelled": 0}, fields=["debit", "credit"])
			self.assertTrue(len(gl_entries) > 0)
			total_debit = sum(flt(d.debit) for d in gl_entries)
			total_credit = sum(flt(d.credit) for d in gl_entries)
			self.assertAlmostEqual(total_debit, total_credit, places=2)
			self.assertAlmostEqual(total_debit, 900.0, places=2)

			# Test cancellation
			pi.cancel()
			active_gles = frappe.get_all("GL Entry", filters={"voucher_no": pi.name, "is_cancelled": 0})
			self.assertEqual(len(active_gles), 0, "All GL entries should be cancelled")

	def test_12_zero_discount_regression(self):
		"""
		TEST 12: Invoice without custom discount behaves exactly like normal ERPNext.
		"""
		pi = self.create_purchase_invoice([{
			"item_code": self.item1,
			"qty": 5,
			"rate": 200,
		}])

		item = pi.items[0]
		self.assertEqual(flt(item.rate), 200.0)
		self.assertEqual(flt(item.amount), 1000.0)
		self.assertEqual(flt(item.net_amount), 1000.0)
		self.assertEqual(flt(pi.net_total), 1000.0)
		self.assertEqual(flt(pi.custom_total_item_discount), 0.0)
