import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def get_custom_fields():
	receipt_item_fields = [
		{
			"fieldname": "custom_item_gross_amount",
			"label": "Item Gross Amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"insert_after": "rate",
			"read_only": 1,
			"in_list_view": 1,
			"description": "Gross Amount (Qty × Rate) before item discount",
		},
		{
			"fieldname": "custom_item_discount_percentage",
			"label": "Item Discount %",
			"fieldtype": "Percent",
			"insert_after": "custom_item_gross_amount",
			"default": 0,
			"in_list_view": 1,
			"description": "Item Discount %",
		},
		{
			"fieldname": "custom_item_discount_amount",
			"label": "Item Discount Amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"insert_after": "custom_item_discount_percentage",
			"default": 0,
			"in_list_view": 1,
			"description": "Item Discount Amount (Flat)",
		},
		{
			"fieldname": "custom_item_net_amount",
			"label": "Item Net Amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"insert_after": "custom_item_discount_amount",
			"read_only": 1,
			"in_list_view": 1,
			"description": "Item Net Amount (Gross - Discount)",
		},
	]

	parent_receipt_fields = [
		{
			"fieldname": "custom_total_item_discount",
			"label": "Total Item Discount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"insert_after": "net_total",
			"read_only": 1,
			"default": 0,
			"description": "Total Item-Level Discounts applied on this receipt",
		},
	]

	return {
		"Purchase Invoice Item": [
			{
				"fieldname": "custom_item_gross_amount",
				"label": "Item Gross Amount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"insert_after": "rate",
				"read_only": 1,
				"in_list_view": 1,
				"description": "Gross Amount (Qty × Rate) before item discount",
			},
			{
				"fieldname": "custom_item_discount_percentage",
				"label": "Item Discount %",
				"fieldtype": "Percent",
				"insert_after": "custom_item_gross_amount",
				"default": 0,
				"in_list_view": 1,
				"description": "Item Discount %",
			},
			{
				"fieldname": "custom_item_discount_amount",
				"label": "Item Discount Amount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"insert_after": "custom_item_discount_percentage",
				"default": 0,
				"in_list_view": 1,
				"description": "Item Discount Amount (Flat)",
			},
			{
				"fieldname": "custom_item_net_amount",
				"label": "Item Net Amount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"insert_after": "custom_item_discount_amount",
				"read_only": 1,
				"in_list_view": 1,
				"description": "Item Net Amount (Gross - Discount)",
			},
		],
		"Purchase Invoice": [
			{
				"fieldname": "custom_total_item_discount",
				"label": "Total Item Discount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"insert_after": "net_total",
				"read_only": 1,
				"default": 0,
				"description": "Total Item-Level Discounts applied on this invoice",
			},
		],
		"Purchase Receipt Item": receipt_item_fields,
		"Purchase Receipt": parent_receipt_fields,
	}


def setup_custom_fields():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
