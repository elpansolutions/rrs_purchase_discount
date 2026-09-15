# RRS Purchase Discount

A custom Frappe/ERPNext v16 application that provides an independent, item-level purchase discount on Purchase Invoices. It reduces the final payable amount, invoice net total, and taxable base while strictly preserving the original item **Rate**.

---

## 1. What the App Does

- Adds custom fields to **Purchase Invoice Item**:
  - `custom_item_gross_amount`: Item Gross Amount (`Qty × Rate` before discount).
  - `custom_item_discount_percentage`: Item Discount % (e.g. `5%`).
  - `custom_item_discount_amount`: Item Discount Amount (Flat currency amount, e.g. `₹3,000`).
  - `custom_item_net_amount`: Item Net Amount (`Gross Amount - Discount Amount`).
- Adds a summary field on **Purchase Invoice**:
  - `custom_total_item_discount`: Total Item Discount (sum of all row-level discounts).
- Provides **Bi-Directional Synchronisation**:
  - Entering Discount % calculates Discount Amount.
  - Entering Discount Amount calculates effective Discount %.
  - When Qty or Rate changes, discount and net amounts recalculate automatically.
- **Rate Invariant**: The authoritative item `rate` and `base_rate` remain completely untouched (e.g. ₹123 is preserved, never rewritten to ₹121).
- **Tax Calculation Parity**: Reduces the taxable amount so that GST / Purchase Taxes calculate on `Gross - Discount` (e.g. 5% GST on ₹181,500 = ₹9,075).
- **Balanced GL Accounting**: Supports direct net expense booking or optional separate discount account booking.

---

## 2. Why Standard ERPNext Discount Fields Are Not Used

In standard ERPNext, the native `Discount on Price List (%)` and `Discount Amount` fields modify the item's `Rate` (`Rate = Price List Rate - Discount`). 

This causes major issues for businesses that need to:
1. Preserve the contractual / agreed unit purchase price (`Rate`) on invoices, printouts, and reports.
2. Record line-level supplier trade/commercial discounts without distorting unit rates.
3. Keep clean audit trails for purchasing rates.

`rrs_purchase_discount` bypasses native rate reduction and implements a standalone discount engine.

---

## 3. How the Custom Discount Works

For each Purchase Invoice Item row:
$$\text{Gross Amount} = \text{Qty} \times \text{Rate}$$
$$\text{Net Amount} = \text{Gross Amount} - \text{Discount Amount}$$
$$\text{Rate} = \text{Rate (Unchanged)}$$

### Server-Side Validations
- $\text{Discount Amount} \ge 0$ and $\text{Discount \%} \ge 0$
- $\text{Discount \%} \le 100\%$
- $\text{Discount Amount} \le \text{Gross Amount}$
- Conflicts with standard ERPNext discount fields are rejected to prevent duplicate discounting.

---

## 4. Installation

```bash
cd /path/to/frappe-bench

# Install app package
bench get-app /home/frappe/frappe-bench/apps/rrs_purchase_discount
# OR editable install:
./env/bin/pip install -e apps/rrs_purchase_discount

# Install app on site
bench --site site1.local install-app rrs_purchase_discount

# Run migrations
bench --site site1.local migrate
```

---

## 5. Configuration

Access **Purchase Discount Settings** via the Awesome Bar:
1. **Enable Item-Level Purchase Discount**: Master switch (Default: Checked).
2. **Enable Separate Purchase Discount Accounting**:
   - **Unchecked (Default)**: Purchase Expense is debited directly at Net Amount (`Gross - Discount`).
   - **Checked**: Purchase Expense is debited at Gross Amount, and the discount amount is credited to the configured **Purchase Discount Account**.
3. **Default Purchase Discount Account**: Chart of accounts head for purchase discounts.
4. **Company Specific Discount Accounts**: Table to configure discount accounts per company in multi-company setups.

---

## 6. Example Calculation

| Field | Value |
| :--- | :--- |
| **Item Code** | BAKP0500 |
| **Quantity** | 1,500 |
| **Rate** | **₹123.00** |
| **Item Gross Amount** | ₹184,500.00 |
| **Item Discount Amount** | ₹3,000.00 (1.626%) |
| **Item Net Amount** | ₹181,500.00 |
| **GST (5%)** | ₹9,075.00 (CGST ₹4,537.50 + SGST ₹4,537.50) |
| **Grand Total** | ₹190,575.00 |

*Notice: The rate displayed and stored remains ₹123.00.*

---

## 7. Accounting Behavior

### Option A: Standard Net Booking (Default)
| Account Head | Debit (₹) | Credit (₹) |
| :--- | :--- | :--- |
| Purchase / Expense Account | 181,500.00 | - |
| Input Tax CGST | 4,537.50 | - |
| Input Tax SGST | 4,537.50 | - |
| Creditors / Supplier | - | 190,575.00 |
| **Total** | **190,575.00** | **190,575.00** |

### Option B: Separate Discount Account (Configurable)
| Account Head | Debit (₹) | Credit (₹) |
| :--- | :--- | :--- |
| Purchase / Expense Account | 184,500.00 | - |
| Purchase Discount Account | - | 3,000.00 |
| Input Tax CGST | 4,537.50 | - |
| Input Tax SGST | 4,537.50 | - |
| Creditors / Supplier | - | 190,575.00 |
| **Total** | **193,575.00** | **193,575.00** |

---

## 8. GST / India Compliance Behavior

- Taxable Amount is updated to `item.base_net_amount` (₹181,500.00).
- Compatible with:
  - In-State GST (CGST + SGST)
  - Out-State GST (IGST)
  - Reverse Charge (RCM)
  - Multi-tax rate invoices
- India Compliance GST Breakup table renders the discounted taxable base accurately.

---

## 9. Purchase Receipt & Stock Valuation Relationship

In version 1.0, this functionality is implemented on **Purchase Invoice**.
- In ERPNext's valuation architecture, stock valuation rate is computed as $\text{base\_net\_amount} / \text{stock\_qty}$.
- When updating stock via Purchase Invoice with Perpetual Inventory, incoming valuation reflects the true net purchase cost while preserving the agreed contractual rate on invoice lines.

---

## 10. How to Uninstall Safely

```bash
# Uninstall from site
bench --site site1.local uninstall-app rrs_purchase_discount

# Remove app from bench
bench remove-app rrs_purchase_discount
```

---

## 11. Known Limitations & Notes

- Standard ERPNext native discount fields (`discount_percentage` / `discount_amount`) must not be used on the same line as custom item discounts to avoid duplicate discounting.
- Multi-currency transactions automatically convert both gross and discount amounts using the document's `conversion_rate`.
