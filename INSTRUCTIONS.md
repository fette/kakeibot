# Project Instructions

## PayPay transaction import → budget worksheet format

### Source data (PayPay TSV)
- Columns arrive without a header: `date (YYYY/MM/DD)`, `merchant`, `payment method`, blank, `amount (JPY, negative for spend)`, two blank placeholders, `month (YYYY-MM)`, `category`.
- Amounts are integers in yen; no currency symbol, debit values are negative.

### Target structure (Numbers → CSV export)
- The budget sheet is laid out as a series of category blocks inside a single CSV table:
  - A category summary row: column A holds the category name (e.g. `食費`), the USD/JPY total columns show the aggregated amount for that category, other columns remain blank or store notes.
  - Detail rows immediately follow, with column A left empty. Columns B–J align to: `Date (M/D)`, `Merchant`, `Method`, `金額 (USD)`, `金額 (JPY)`, `Notes`, `備考`, `月`, `Category`.
  - Detail rows typically populate only the fields that make sense (for PayPay imports: date, merchant, method, JPY amount, month, category, optional notes).
- Amount fields in the Numbers export are formatted strings (e.g. "-¥3,497") because Numbers applies currency formatting during export. Keep raw numeric values during processing; formatting happens when the data is pasted back into Numbers.

### Transformation checklist
1. **Normalize PayPay rows**
   - Parse the TSV using UTF-8.
   - Convert the PayPay date (`YYYY/MM/DD`) into `M/D` for the `Date` column (omit leading zeros to match existing rows).
   - Carry over `merchant` into the `Merchant` column exactly as-is.
   - Set `Method` to the PayPay payment source (`W PayPay`, etc.).
   - Map the yen amount into `金額 (JPY)` keeping the numeric value (negative for spend, positive for refunds). Leave the USD column blank.
   - Ignore any category text that may appear in the PayPay export; categories are determined by our mapping and prior budget usage.
   - Copy the PayPay `month` string into the `月` column.
   - Use `備考`/`Notes` only when PayPay provides extra context (e.g., memo field).
2. **Group by category**
   - Sort or cluster the normalized rows by `Category` to mirror the block structure in the budget sheet.
   - For each category block, compute the JPY total and create a leading summary row:
     - Column A = category name.
     - `金額 (JPY)` = summed value (negative spend means outflow). Keep USD blank unless there are USD transactions.
     - Leave detail columns empty (Numbers will format the total on import).
3. **Export for Numbers**
   - Write the combined dataset to CSV using the same column order as the budget export. Include the header row.
   - Ensure fields with commas or quotes are correctly quoted (standard CSV quoting handles this automatically).
   - When pasting back into Numbers, apply the sheet's currency formatting to the amount columns so the `¥` symbol and comma separators reappear.

### Merchant → category mapping
- Maintain shared mappings in `MERCHANT_CATEGORY_MAP.md` using the format: merchant pattern, default category, optional notes.
- Use exact merchant text when possible; fall back to regex-like wildcard descriptions (e.g., `IKEA*`) if the export varies.
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
