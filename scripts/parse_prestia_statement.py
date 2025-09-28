#!/usr/bin/env python3
"""Extract transaction lines from a Prestia (SMBC Trust Bank) PDF statement.

Usage
-----
python3 scripts/parse_prestia_statement.py input.pdf output.tsv

The parser inflates PDF content streams, decodes embedded Shift-JIS strings,
locates transaction blocks, and writes a tab-delimited file with columns:
    card_last4, date (YYYY-MM-DD), merchant, currency, amount, note

Amounts are emitted as negative numbers for spends and positive for refunds.
"""
from __future__ import annotations

import csv
import re
import sys
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence


CURRENCY_CODES = {
    "JPY",
    "USD",
    "EUR",
    "GBP",
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "HKD",
    "SGD",
    "KRW",
}


@dataclass
class Transaction:
    card_last4: str
    date: datetime
    merchant: str
    currency: str
    amount: float
    note: str = ""

    def to_row(self) -> List[str]:
        return [
            self.card_last4,
            self.date.strftime("%Y-%m-%d"),
            self.merchant,
            self.currency,
            f"{self.amount:.2f}",
            self.note,
        ]


def parse_pdf_strings(stream_bytes: bytes) -> List[bytes]:
    """Extract literal strings from a PDF content stream."""
    strings: List[bytes] = []
    i = 0
    length = len(stream_bytes)
    while i < length:
        if stream_bytes[i] != ord("("):
            i += 1
            continue
        i += 1
        buf = bytearray()
        depth = 1
        while i < length and depth > 0:
            c = stream_bytes[i]
            if c == ord("\\"):
                i += 1
                if i >= length:
                    break
                esc = stream_bytes[i]
                if esc in b"nrtbf\\()":
                    mapping = {
                        ord("n"): ord("\n"),
                        ord("r"): ord("\r"),
                        ord("t"): ord("\t"),
                        ord("b"): ord("\b"),
                        ord("f"): ord("\f"),
                        ord("("): ord("("),
                        ord(")"): ord(")"),
                        ord("\\"): ord("\\"),
                    }
                    buf.append(mapping.get(esc, esc))
                elif ord("0") <= esc <= ord("7"):
                    oct_digits = [esc]
                    for _ in range(2):
                        if i + 1 < length and ord("0") <= stream_bytes[i + 1] <= ord("7"):
                            i += 1
                            oct_digits.append(stream_bytes[i])
                        else:
                            break
                    value = int(bytes(oct_digits).decode("ascii"), 8)
                    buf.append(value % 256)
                else:
                    buf.append(esc)
            elif c == ord("("):
                depth += 1
                buf.append(c)
            elif c == ord(")"):
                depth -= 1
                if depth == 0:
                    break
                buf.append(c)
            else:
                buf.append(c)
            i += 1
        strings.append(bytes(buf))
        i += 1
    return strings


def iter_text_strings(pdf_bytes: bytes) -> Iterable[str]:
    pattern = re.compile(rb"stream\r?\n(.*?)endstream", re.DOTALL)
    for match in pattern.finditer(pdf_bytes):
        chunk = match.group(1)
        try:
            chunk = zlib.decompress(chunk)
        except zlib.error:
            continue
        if b" Tj" not in chunk and b" TJ" not in chunk:
            continue
        for raw in parse_pdf_strings(chunk):
            if not raw:
                continue
            for encoding in ("cp932", "shift_jis", "utf-8"):
                try:
                    yield raw.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # Emit repr for debugging but do not raise
                yield raw.decode("latin1", errors="ignore")


def normalize_lines(strings: Sequence[str]) -> List[str]:
    cleaned: List[str] = []
    for s in strings:
        line = s.replace("\r", "").strip()
        if not line:
            continue
        cleaned.append(line)
    return cleaned


def parse_transactions(lines: Sequence[str]) -> List[Transaction]:
    txns: List[Transaction] = []
    card_last4: str | None = None
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        masked = re.match(r"\*{4}-\*{4}-\*{4}-(\d{4})", line)
        if masked:
            card_last4 = masked.group(1)
            i += 1
            continue
        if line in CURRENCY_CODES:
            if card_last4 is None or i == 0 or i + 2 >= n:
                i += 1
                continue
            merchant = lines[i - 1]
            currency = line
            date_str = lines[i + 1]
            amount_str = lines[i + 2]
            try:
                date = datetime.strptime(date_str, "%y/%m/%d")
            except ValueError:
                # Occasionally the statement prints YYYY/MM/DD.
                date = datetime.strptime(date_str, "%Y/%m/%d")
            amount = float(amount_str.replace(",", ""))
            amount = -amount  # statement lists debits as positive numbers
            txns.append(Transaction(card_last4, date, merchant, currency, amount))
            i += 3
            continue
        i += 1
    return txns


def write_tsv(txns: Sequence[Transaction], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["card_last4", "date", "merchant", "currency", "amount", "note"])
        for txn in txns:
            writer.writerow(txn.to_row())


def main(argv: Sequence[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    input_path = Path(argv[1])
    output_path = Path(argv[2])
    pdf_bytes = input_path.read_bytes()
    strings = list(iter_text_strings(pdf_bytes))
    lines = normalize_lines(strings)
    txns = parse_transactions(lines)
    if not txns:
        print("No transactions parsed", file=sys.stderr)
        return 2
    write_tsv(txns, output_path)
    print(f"Parsed {len(txns)} transactions from {input_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
