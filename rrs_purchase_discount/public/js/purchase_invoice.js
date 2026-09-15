frappe.ui.form.on("Purchase Invoice", {
	refresh: function (frm) {
		// Custom setup or filters if needed
	},
});

frappe.ui.form.on("Purchase Invoice Item", {
	qty: function (frm, cdt, cdn) {
		calculate_custom_item_discount(frm, cdt, cdn, "qty");
	},
	rate: function (frm, cdt, cdn) {
		calculate_custom_item_discount(frm, cdt, cdn, "rate");
	},
	custom_item_discount_percentage: function (frm, cdt, cdn) {
		calculate_custom_item_discount(frm, cdt, cdn, "custom_item_discount_percentage");
	},
	custom_item_discount_amount: function (frm, cdt, cdn) {
		calculate_custom_item_discount(frm, cdt, cdn, "custom_item_discount_amount");
	},
});

function calculate_custom_item_discount(frm, cdt, cdn, trigger_field) {
	let row = locals[cdt][cdn];
	if (!row) return;

	let qty = flt(row.qty);
	let rate = flt(row.rate);
	let gross_amount = flt(qty * rate, precision("custom_item_gross_amount", row) || 2);
	frappe.model.set_value(cdt, cdn, "custom_item_gross_amount", gross_amount);

	let disc_pct = flt(row.custom_item_discount_percentage);
	let disc_amt = flt(row.custom_item_discount_amount);

	if (trigger_field === "custom_item_discount_percentage") {
		if (disc_pct < 0) {
			frappe.msgprint(__("Discount % cannot be negative."));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_percentage", 0);
			disc_pct = 0;
		} else if (disc_pct > 100) {
			frappe.msgprint(__("Discount % cannot exceed 100%."));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_percentage", 100);
			disc_pct = 100;
		}
		disc_amt = flt(gross_amount * (disc_pct / 100.0), precision("custom_item_discount_amount", row) || 2);
		frappe.model.set_value(cdt, cdn, "custom_item_discount_amount", disc_amt);
	} else if (trigger_field === "custom_item_discount_amount") {
		if (disc_amt < 0) {
			frappe.msgprint(__("Discount Amount cannot be negative."));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_amount", 0);
			disc_amt = 0;
		} else if (disc_amt > gross_amount && gross_amount > 0) {
			frappe.msgprint(__("Discount Amount ({0}) cannot exceed Gross Amount ({1}).", [disc_amt, gross_amount]));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_amount", gross_amount);
			disc_amt = gross_amount;
		}
		disc_pct = gross_amount > 0 ? flt((disc_amt / gross_amount) * 100.0, precision("custom_item_discount_percentage", row) || 2) : 0;
		frappe.model.set_value(cdt, cdn, "custom_item_discount_percentage", disc_pct);
	} else {
		// If qty or rate changed, recompute discount based on percentage if set, else maintain flat amount within bounds
		if (disc_pct > 0) {
			disc_amt = flt(gross_amount * (disc_pct / 100.0), precision("custom_item_discount_amount", row) || 2);
			frappe.model.set_value(cdt, cdn, "custom_item_discount_amount", disc_amt);
		} else if (disc_amt > 0) {
			if (disc_amt > gross_amount) {
				disc_amt = gross_amount;
				frappe.model.set_value(cdt, cdn, "custom_item_discount_amount", disc_amt);
			}
			disc_pct = gross_amount > 0 ? flt((disc_amt / gross_amount) * 100.0, precision("custom_item_discount_percentage", row) || 2) : 0;
			frappe.model.set_value(cdt, cdn, "custom_item_discount_percentage", disc_pct);
		}
	}

	let net_amount = flt(gross_amount - disc_amt, precision("custom_item_net_amount", row) || 2);
	frappe.model.set_value(cdt, cdn, "custom_item_net_amount", net_amount);

	// Standard fields sync (preserving row.rate!)
	frappe.model.set_value(cdt, cdn, "net_amount", net_amount);
	let net_rate = qty ? flt(net_amount / qty, precision("net_rate", row) || 2) : 0;
	frappe.model.set_value(cdt, cdn, "net_rate", net_rate);

	// Trigger standard recalculation
	if (frm.cscript && frm.cscript.calculate_taxes_and_totals) {
		frm.cscript.calculate_taxes_and_totals();
	}
}
