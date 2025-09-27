# Project Instructions

## PayPay transaction import → budget worksheet format

### Source data (PayPay TSV)
- Columns arrive without a header: `date (YYYY/MM/DD)`, `merchant`, `payment method`, blank, `amount (JPY, negative for spend)`, two blank placeholders, `month (YYYY-MM)`, `category`.
- Amounts are integers in yen; no currency symbol, debit values are negative.

### Target structure (Numbers → CSV/TSV export)
- The budget sheet is laid out as a series of category blocks inside a single table:
  - Detail rows populate columns B–J: `Date (M/D)`, `Merchant`, `Method`, `金額 (USD)`, `金額 (JPY)`, `Notes`, `備考`, `月`, `Category`.
  - Column A stays blank for detail rows (Numbers uses it for grouping totals automatically).
- Amount fields in the Numbers export are formatted strings (e.g. "-¥3,497") because Numbers applies currency formatting during export. Keep raw numeric values during processing; formatting happens when the data is pasted back into Numbers.

### Transformation checklist
1. **Normalize PayPay rows**
   - Parse the source file using UTF-8.
   - Convert the PayPay date (`YYYY/MM/DD`) into `M/D` for the `Date` column (omit leading zeros to match existing rows).
   - Carry over `merchant` into the `Merchant` column exactly as-is (include chain + branch if provided).
   - Set the `Method` column to the constant `PayPay W` so it matches the budget sheet convention (ignore the PayPay export's payment-method field).
   - Map the yen amount into `金額 (JPY)` keeping the numeric value (negative for spend, positive for refunds). Leave the USD column blank.
   - Ignore any category text that may appear in the PayPay export; categories are determined by our mapping and prior budget usage.
   - Copy the PayPay `month` string into the `月` column.
   - Use `備考`/`Notes` only when PayPay provides extra context (e.g., memo field).
2. **Review totals (offline)**
   - Optionally compute per-category sums for QA, but do **not** emit summary rows in the final output because Numbers already groups by `Category`.
3. **Export for Numbers**
   - Write the dataset to **TSV** (tab-delimited) with columns matching the budget export order.
   - Do **not** include a header row; start directly with the first detail line so pasting into Numbers populates the existing table.
   - Ensure fields containing commas remain unquoted (TSV avoids comma-escaping issues when pasting).

### Merchant → category mapping
- Maintain shared mappings in `MERCHANT_CATEGORY_MAP.md` using the format: merchant pattern, default category, optional notes.
- Use exact merchant text when possible; fall back to wildcard descriptions (e.g., `IKEA*`) if the export varies.
- When a mapping note says to confirm the context (e.g., Daiso might be `玲お小遣い`), pause and ask before finalizing the category.
- If an unknown or ambiguous merchant appears, flag it, confirm the category here, and append the agreed mapping before importing the data.
- Document any exceptions (for example, IKEA purchases that belong to `食費` vs. `諸々`).

### Open items / decisions
- Decide whether to automate the process (e.g., Python script) or keep a manual spreadsheet workflow. Document the chosen approach here once implemented.
- Clarify how to handle duplicate transactions (PayPay sometimes exports repeated rows). Add rules when you encounter them.
- If a PayPay merchant still lacks a mapping, get a decision before running the transformation.
- Build up the merchant mapping table as you discover recurring merchants so future imports auto-classify.

---
Add further project instructions to this document as workflows evolve.
