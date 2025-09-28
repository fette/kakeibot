#!/usr/bin/env python3
"""Convert parsed Prestia transactions into Numbers-ready TSV rows."""
from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

MAP_PATH = Path("MERCHANT_CATEGORY_MAP.md")


@dataclass
class Mapping:
    pattern: str
    prefix: bool
    category: str
    notes: str


CONFIRM_KEYWORDS = {"ask", "confirm", "確認", "should"}


def load_mapping() -> List[Mapping]:
    mappings: List[Mapping] = []
    if not MAP_PATH.exists():
        return mappings
    with MAP_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or not line.startswith("|") or line.startswith("| ---"):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) < 3:
                continue
            pattern, category, notes = cols[:3]
            prefix = pattern.endswith("*")
            if prefix:
                pattern = pattern[:-1]
            mappings.append(Mapping(pattern, prefix, category, notes))
    return mappings


def find_category(merchant: str, mappings: Sequence[Mapping]) -> Tuple[str | None, str | None]:
    merchant = merchant.strip()
    for mapping in mappings:
        if mapping.prefix:
            if merchant.startswith(mapping.pattern):
                return mapping.category, mapping.notes
        else:
            if merchant == mapping.pattern:
                return mapping.category, mapping.notes
    return None, None


def needs_confirmation(notes: str | None) -> bool:
    if not notes:
        return False
    lowered = notes.lower()
    return any(keyword in lowered for keyword in CONFIRM_KEYWORDS)


def iter_rows(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            yield row


def format_date(date_str: str) -> Tuple[str, str]:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.month}/{dt.day}", dt.strftime("%Y-%m")


def main(argv: Sequence[str]) -> int:
    if len(argv) != 3:
        print("Usage: python3 scripts/prestia_to_numbers.py <input_raw_tsv> <output_numbers_tsv>", file=sys.stderr)
        return 1

    input_path = Path(argv[1])
    output_path = Path(argv[2])
    mappings = load_mapping()

    unmatched: List[str] = []
    confirmations: List[str] = []
    rows_out: List[List[str]] = []

    for row in iter_rows(input_path):
        merchant = row["merchant"].strip()
        category, notes = find_category(merchant, mappings)
        if category is None:
            unmatched.append(merchant)
            category = "要確認"
        if needs_confirmation(notes):
            confirmations.append(merchant)
        date_display, month = format_date(row["date"].strip())
        currency = row["currency"].strip().upper()
        amount = float(row["amount"].strip())
        amount_jpy = ""
        usd_amount = ""
        note_field = row.get("note", "").strip()
        if currency == "JPY":
            amount_jpy = str(int(round(amount)))
        elif currency == "USD":
            usd_amount = f"{amount:.2f}"
            note_field = (note_field + f" USD {amount:.2f}").strip()
        else:
            note_field = (note_field + f" {currency} {amount:.2f}").strip()
        method = f"Prestia {row['card_last4'].strip()}"
        rows_out.append([
            "",  # Column A stays blank for detail rows
            date_display,
            merchant,
            method,
            usd_amount,
            amount_jpy,
            note_field,
            "",
            month,
            category,
        ])

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerows(rows_out)

    if unmatched:
        print("Unmapped merchants:", sorted(set(unmatched)), file=sys.stderr)
    if confirmations:
        print("Needs confirmation:", sorted(set(confirmations)), file=sys.stderr)

    print(f"Wrote {len(rows_out)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
