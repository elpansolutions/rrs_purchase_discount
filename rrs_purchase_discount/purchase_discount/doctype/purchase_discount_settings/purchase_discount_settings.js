frappe.ui.form.on("Purchase Discount Settings", {
	refresh: function (frm) {
		frm.set_query("default_purchase_discount_account", function () {
			return {
				filters: {
					is_group: 0,
					account_type: ["in", ["Income", "Expense", "Direct Income", "Indirect Income", "Temporary"]],
				},
			};
		});

		frm.set_query("purchase_discount_account", "company_accounts", function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			return {
				filters: {
					company: row.company,
					is_group: 0,
				},
			};
		});
	},
});
