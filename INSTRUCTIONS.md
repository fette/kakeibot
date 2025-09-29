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

### Prestia card statement import → budget worksheet format

### Source data (Prestia PDF statements)
- Statements are downloaded as PDFs from SMBC Trust Bank (Prestia) and list card transactions for specific cards (masked numbers such as `****-****-****-3249`).
- Text is embedded in the PDF streams, so we can extract it programmatically without manual export.

### Extraction + normalization checklist
1. **Parse statement text**
   - Run `python3 scripts/parse_prestia_statement.py <input.pdf> <output.tsv>`; the helper script inflates the PDF content streams, decodes Shift-JIS text, and emits a raw table with columns: `card_last4`, `date (YYYY-MM-DD)`, `merchant`, `currency`, `amount` (negative for spend), `notes` (currently blank).
   - The script treats year values like `25/08/22` as 2025-08-22 (prefix `20`), assumes amounts shown are positive outflows, and preserves the currency code (`JPY`, `USD`, etc.).
   - Any strings the parser cannot decode cleanly are written to STDERR so they can be inspected manually.
2. **Map to budget columns**
   - Apply `MERCHANT_CATEGORY_MAP.md` (reuse the same lookup as PayPay) to determine the budget category. Add new Prestia-specific merchants to the mapping as they appear.
   - Convert the ISO date (`YYYY-MM-DD`) into `M/D` for the `Date` column when generating the Numbers import file.
   - Set `Method` to `Prestia <last4>` so we can distinguish which card generated the spend.
   - For foreign-currency lines, keep `金額 (JPY)` blank for now and use `Notes` to capture the original `currency` + amount until we implement FX conversion rules.
3. **Export for Numbers**
   - Just like the PayPay workflow, produce a TSV with columns `['', Date, Merchant, Method, 金額 (USD), 金額 (JPY), Notes, 備考, 月, Category]` and no header row.
   - Populate `金額 (JPY)` with the signed yen amount once we have a conversion (for pure JPY transactions, use the statement amount directly and negate it).
   - Include `月` based on the transaction date (`YYYY-MM`).

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
- For Prestia statements, define how to capture foreign-currency purchases (conversion source, rate, which column stores the FX amount) before importing large batches.

---
Add further project instructions to this document as workflows evolve.

## USAA credit card paste → budget worksheet format

### Source data (USAA clipboard paste)
- Pasting the web portal transaction list yields repeating blocks: a combined date/description line (`Aug 29, 2025August 29, 2025	Merchant`), followed by `Category`, then `Amount`.
- Dates always appear twice in the first field; we grab the first `Mon DD, YYYY` occurrence and use the text after the tab as the merchant name.

### Transformation checklist
1. **Normalize blocks**
   - Drop the static headers (`Date`, `Description`, `Category`, `Amount`).
   - Walk the remaining lines in groups of three (date/merchant, category, amount).
   - Parse the date with `%b %d, %Y`, convert to `M/D` for display and `YYYY-MM` for the month column.
   - Strip the dollar sign, negate the value for spends, and keep USD amounts (leave `金額 (JPY)` blank).
   - Preserve the USAA web category as a note for later review/map it via `MERCHANT_CATEGORY_MAP.md` once rules are defined.
2. **Export for Numbers**
   - Emit a TSV with the usual column order (`['', Date, Merchant, Method, 金額 (USD), 金額 (JPY), Notes, 備考, 月, Category']`).
   - Set `Method` to `USAA` (or `USAA <last4>` if multiple cards).
   - For now store the USAA portal category in `Notes`; overwrite it with a plain-language memo for any allowance (`Wおかづかい`) spend so it copies cleanly into Numbers, and mark `Category` as `要確認` until we build a dedicated mapping table.

### Automation
- Parser script lives in `scripts/parse_usaa_clip.py`. Running
  `python3 scripts/parse_usaa_clip.py USAA/<month> USAA/<month>_raw.tsv USAA/<month>_numbers.tsv`
  converts the clipboard dump into both a normalized raw TSV and a Numbers-ready TSV.

