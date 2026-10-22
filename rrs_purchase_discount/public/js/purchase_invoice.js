// Override and extend ERPNext's client-side taxes_and_totals calculation for Purchase Invoice
(function () {
	if (erpnext && erpnext.taxes_and_totals) {
		let orig_calculate_item_values = erpnext.taxes_and_totals.prototype.calculate_item_values;

		erpnext.taxes_and_totals.prototype.calculate_item_values = function () {
			// Call original calculation
			orig_calculate_item_values.apply(this, arguments);

			if (this.frm && this.frm.doc && (this.frm.doc.doctype === "Purchase Invoice" || this.frm.doc.doctype === "Purchase Receipt")) {
				let total_discount = 0.0;

				for (const item of this.frm.doc.items || []) {
					let gross = flt(item.qty * item.rate, precision("custom_item_gross_amount", item) || 2);
					item.custom_item_gross_amount = gross;

					let disc_pct = flt(item.custom_item_discount_percentage);
					let disc_amt = flt(item.custom_item_discount_amount);

					// Compute total row discount from both independent inputs
					let pct_discount = disc_pct > 0 ? flt(gross * (disc_pct / 100.0), precision("custom_item_discount_amount", item) || 2) : 0.0;
					let row_discount = flt(pct_discount + disc_amt, precision("custom_item_discount_amount", item) || 2);

					if (row_discount > gross && gross > 0) {
						row_discount = gross;
					}

					let net = flt(gross - row_discount, precision("custom_item_net_amount", item) || 2);
					item.custom_item_net_amount = net;

					if (row_discount > 0) {
						// Update net_amount and net_rate for tax calculation
						item.net_amount = net;
						item.net_rate = item.qty ? flt(net / item.qty, precision("net_rate", item) || 2) : 0;
						total_discount += row_discount;

						this.set_in_company_currency(item, [
							"net_rate",
							"net_amount",
						]);
					}
				}

				this.frm.doc.custom_total_item_discount = flt(total_discount, precision("custom_total_item_discount") || 2);
			}
		};
	}
})();

["Purchase Invoice", "Purchase Receipt"].forEach(function(dt) {
	frappe.ui.form.on(dt, {
		refresh: function (frm) {
			// Ensure summary fields are visible and updated
		},
	});
});

["Purchase Invoice Item", "Purchase Receipt Item"].forEach(function(item_dt) {
	frappe.ui.form.on(item_dt, {
		qty: function (frm, cdt, cdn) {
			calculate_custom_item_discount(frm, cdt, cdn);
		},
		rate: function (frm, cdt, cdn) {
		calculate_custom_item_discount(frm, cdt, cdn);
	},
	custom_item_discount_percentage: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row) return;

		let disc_pct = flt(row.custom_item_discount_percentage);
		if (disc_pct < 0) {
			frappe.msgprint(__("Discount % cannot be negative."));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_percentage", 0);
		} else if (disc_pct > 100) {
			frappe.msgprint(__("Discount % cannot exceed 100%."));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_percentage", 100);
		}
		calculate_custom_item_discount(frm, cdt, cdn);
	},
	custom_item_discount_amount: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row) return;

		let disc_amt = flt(row.custom_item_discount_amount);
		let gross = flt(flt(row.qty) * flt(row.rate));
		if (disc_amt < 0) {
			frappe.msgprint(__("Discount Amount cannot be negative."));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_amount", 0);
		} else if (disc_amt > gross && gross > 0) {
			frappe.msgprint(__("Discount Amount ({0}) cannot exceed Gross Amount ({1}).", [disc_amt, gross]));
			frappe.model.set_value(cdt, cdn, "custom_item_discount_amount", gross);
		}
		calculate_custom_item_discount(frm, cdt, cdn);
	},
	});
});

function calculate_custom_item_discount(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (!row) return;

	let qty = flt(row.qty);
	let rate = flt(row.rate);
	let gross_amount = flt(qty * rate, precision("custom_item_gross_amount", row) || 2);
	frappe.model.set_value(cdt, cdn, "custom_item_gross_amount", gross_amount);

	let disc_pct = flt(row.custom_item_discount_percentage);
	let disc_amt = flt(row.custom_item_discount_amount);

	let pct_discount = disc_pct > 0 ? flt(gross_amount * (disc_pct / 100.0), precision("custom_item_discount_amount", row) || 2) : 0.0;
	let total_row_disc = flt(pct_discount + disc_amt, precision("custom_item_discount_amount", row) || 2);

	if (total_row_disc > gross_amount && gross_amount > 0) {
		total_row_disc = gross_amount;
	}

	let net_amount = flt(gross_amount - total_row_disc, precision("custom_item_net_amount", row) || 2);
	frappe.model.set_value(cdt, cdn, "custom_item_net_amount", net_amount);
	frappe.model.set_value(cdt, cdn, "net_amount", net_amount);

	let net_rate = qty ? flt(net_amount / qty, precision("net_rate", row) || 2) : 0;
	frappe.model.set_value(cdt, cdn, "net_rate", net_rate);

	// Trigger taxes and totals recalculation
	if (frm.cscript && frm.cscript.calculate_taxes_and_totals) {
		frm.cscript.calculate_taxes_and_totals();
	}
}
