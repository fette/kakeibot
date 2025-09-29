#!/usr/bin/env python3
"""Convert USAA clipboard paste into raw + Numbers-ready TSV files."""
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

DATE_PATTERN = re.compile(r"([A-Za-z]{3} \d{2}, \d{4})")
HEADER_WORDS = {"date", "description", "category", "amount"}


@dataclass
class Transaction:
    date: datetime
    merchant: str
    usaa_category: str
    amount_usd: float

    def raw_row(self) -> List[str]:
        return [
            self.date.strftime("%Y-%m-%d"),
            self.merchant,
            self.usaa_category,
            f"{self.amount_usd:.2f}",
        ]

    def numbers_row(self) -> List[str]:
        return [
            "",
            f"{self.date.month}/{self.date.day}",
            self.merchant,
            "USAA",
            f"{self.amount_usd:.2f}",
            "",
            self.usaa_category,
            "",
            self.date.strftime("%Y-%m"),
            "要確認",
        ]


def normalize_lines(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [line for line in lines if line.lower() not in HEADER_WORDS]


def parse_transactions(lines: Sequence[str]) -> List[Transaction]:
    txns: List[Transaction] = []
    i = 0
    while i + 2 < len(lines):
        date_merchant = lines[i]
        usaa_category = lines[i + 1]
        amount_str = lines[i + 2]
        i += 3

        match = DATE_PATTERN.search(date_merchant)
        if not match:
            continue
        date = datetime.strptime(match.group(1), "%b %d, %Y")
        if "\t" in date_merchant:
            merchant = date_merchant.split("\t", 1)[1].strip()
        else:
            merchant = date_merchant[match.end():].strip()
        amount = -float(amount_str.replace("$", "").replace(",", ""))
        txns.append(Transaction(date, merchant, usaa_category, amount))
    return txns


def write_raw(txns: Sequence[Transaction], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["date", "merchant", "usaa_category", "amount_usd"])
        for txn in txns:
            writer.writerow(txn.raw_row())


def write_numbers(txns: Sequence[Transaction], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        for txn in txns:
            writer.writerow(txn.numbers_row())


def main(argv: Sequence[str]) -> int:
    if len(argv) != 4:
        print("Usage: python3 scripts/parse_usaa_clip.py <input_txt> <raw_tsv> <numbers_tsv>", file=sys.stderr)
        return 1

    input_path = Path(argv[1])
    raw_path = Path(argv[2])
    numbers_path = Path(argv[3])

    text = input_path.read_text(encoding="utf-8")
    lines = normalize_lines(text)
    txns = parse_transactions(lines)

    write_raw(txns, raw_path)
    write_numbers(txns, numbers_path)

    print(f"Parsed {len(txns)} USAA transactions → {numbers_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
