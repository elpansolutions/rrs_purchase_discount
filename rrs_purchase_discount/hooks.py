app_name = "rrs_purchase_discount"
app_title = "RRS Purchase Discount"
app_publisher = "RRS"
app_description = "Item-level purchase discount for ERPNext that reduces payable and taxable amounts while preserving original item rates."
app_email = "info@example.com"
app_license = "MIT"

# Includes in <head>
# ------------------
app_include_js = "/assets/rrs_purchase_discount/js/purchase_invoice.js?v=20261022_1"

# DocType JavaScript
doctype_js = {
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Purchase Receipt": "public/js/purchase_invoice.js",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Invoice": {
		"validate": "rrs_purchase_discount.events.purchase_invoice.validate_purchase_invoice",
		"before_save": "rrs_purchase_discount.events.purchase_invoice.validate_purchase_invoice",
		"before_submit": "rrs_purchase_discount.events.purchase_invoice.validate_purchase_invoice",
	},
	"Purchase Receipt": {
		"validate": "rrs_purchase_discount.events.purchase_invoice.validate_purchase_invoice",
		"before_save": "rrs_purchase_discount.events.purchase_invoice.validate_purchase_invoice",
		"before_submit": "rrs_purchase_discount.events.purchase_invoice.validate_purchase_invoice",
	},
}

# Installation and Migration Hooks
# --------------------------------
after_install = "rrs_purchase_discount.setup_custom_fields.setup_custom_fields"
after_migrate = "rrs_purchase_discount.setup_custom_fields.setup_custom_fields"
