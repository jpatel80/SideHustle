#!/usr/bin/env python3
"""KDP paperback printing cost and royalty calculator (Amazon.com, black ink, white or cream paper).

Numbers verified 2026-11-14 against KDP help (fetched with curl):
  * Paperback Printing Cost (topic G201834340): printing cost = fixed cost + page count x per-page cost.
    Black ink, 24-110 pages: fixed cost only, 2.30 USD (regular trim) or 2.84 USD (large trim).
    Black ink, 110-828 pages: 1.00 USD + 0.012 USD/page (regular) or 0.017 USD/page (large).
    Large trim = more than 6.12 in wide or more than 9 in tall (8.5 x 11 is large).
  * Paperback Royalty (topic G201834330): royalty = royalty rate x list price - printing cost.
    Amazon.com: 50% for list prices at or below 9.98 USD, 60% for list prices at or above 9.99 USD.

Other marketplaces have their own tables and thresholds; this script covers Amazon.com only.
Always confirm the figure KDP shows in the Rights & Pricing step before publishing.

Usage:
  python3 scripts/kdp_pricing.py --pages 104                       # table of common prices
  python3 scripts/kdp_pricing.py --pages 64 --price 7.99 --target 300
"""
from __future__ import annotations

import argparse
import json
import math
import sys

RATE_LOW, RATE_HIGH = 0.50, 0.60
RATE_THRESHOLD_USD = 9.99  # 60% at or above this list price, 50% below (Amazon.com)
FIXED_SHORT = {"regular": 2.30, "large": 2.84}  # 24-110 pages
FIXED_LONG = 1.00  # more than 110 pages
PER_PAGE_LONG = {"regular": 0.012, "large": 0.017}
SHORT_MAX_PAGES = 110
MIN_PAGES, MAX_PAGES = 24, 828
COMMON_PRICES = [5.99, 6.99, 7.99, 8.99, 9.99, 10.99, 11.99, 12.99]


def trim_class(trim: tuple[float, float]) -> str:
    w, h = trim
    return "large" if (w > 6.12 or h > 9.0) else "regular"


def printing_cost(pages: int, trim: tuple[float, float] = (8.5, 11.0)) -> float:
    if not MIN_PAGES <= pages <= MAX_PAGES:
        raise ValueError(f"page count must be {MIN_PAGES}-{MAX_PAGES}, got {pages}")
    cls = trim_class(trim)
    if pages <= SHORT_MAX_PAGES:
        return FIXED_SHORT[cls]
    return round(FIXED_LONG + pages * PER_PAGE_LONG[cls], 2)


def royalty_rate(price: float) -> float:
    return RATE_HIGH if price >= RATE_THRESHOLD_USD - 1e-9 else RATE_LOW


def royalty(price: float, pages: int, trim: tuple[float, float] = (8.5, 11.0)) -> float:
    """Royalty per copy sold on Amazon.com (can be negative below the minimum list price)."""
    return round(royalty_rate(price) * price - printing_cost(pages, trim), 2)


def min_list_price(pages: int, trim: tuple[float, float] = (8.5, 11.0)) -> float:
    """Lowest list price at which the royalty is not negative."""
    cost = printing_cost(pages, trim)
    low = math.ceil(cost / RATE_LOW * 100 - 1e-9) / 100
    if low < RATE_THRESHOLD_USD:
        return low
    return max(RATE_THRESHOLD_USD, math.ceil(cost / RATE_HIGH * 100 - 1e-9) / 100)


def sales_for_target(target: float, price: float, pages: int, trim: tuple[float, float] = (8.5, 11.0)) -> int | None:
    """Copies per month needed to earn `target` USD of royalty, or None if the royalty is not positive."""
    r = royalty(price, pages, trim)
    return math.ceil(target / r) if r > 0 else None


def table(pages: int, trim: tuple[float, float] = (8.5, 11.0), prices=COMMON_PRICES, target: float = 0) -> list[dict]:
    rows = []
    for p in prices:
        row = {"price": p, "rate": royalty_rate(p), "printing_cost": printing_cost(pages, trim),
               "royalty": royalty(p, pages, trim)}
        if target:
            row["sales_per_month_for_target"] = sales_for_target(target, p, pages, trim)
        rows.append(row)
    return rows


def markdown_table(pages: int, trim: tuple[float, float] = (8.5, 11.0), prices=COMMON_PRICES) -> str:
    """Pricing table for a listing / upload kit."""
    lines = ["| List price | Royalty rate | Printing cost | Royalty per copy |", "|---|---|---|---|"]
    for r in table(pages, trim, prices):
        lines.append(f"| ${r['price']:.2f} | {int(r['rate'] * 100)}% | ${r['printing_cost']:.2f} | ${r['royalty']:.2f} |")
    return "\n".join(lines)


def _trim(s: str) -> tuple[float, float]:
    try:
        w, h = s.lower().split("x")
        return float(w), float(h)
    except ValueError:
        raise argparse.ArgumentTypeError(f"trim must look like 8.5x11, got {s!r}") from None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pages", type=int, required=True, help="final interior page count")
    p.add_argument("--trim", type=_trim, default=(8.5, 11.0))
    p.add_argument("--price", type=float, action="append", help="list price in USD (repeatable; default: common prices)")
    p.add_argument("--target", type=float, default=0, help="monthly royalty target in USD, to show copies needed")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        rows = table(a.pages, a.trim, a.price or COMMON_PRICES, a.target)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"pages": a.pages, "trim": list(a.trim), "min_list_price": min_list_price(a.pages, a.trim),
                          "rows": rows}, indent=2))
        return 0
    print(f"{a.pages} pages, {a.trim[0]:g} x {a.trim[1]:g} in ({trim_class(a.trim)} trim), black ink, Amazon.com")
    print(f"printing cost ${printing_cost(a.pages, a.trim):.2f}; minimum list price ${min_list_price(a.pages, a.trim):.2f}\n")
    head = f"{'price':>7} {'rate':>5} {'royalty':>8}" + (f" {'copies/month for $' + format(a.target, 'g'):>24}" if a.target else "")
    print(head)
    for r in rows:
        line = f"{r['price']:>7.2f} {int(r['rate'] * 100):>4}% {r['royalty']:>8.2f}"
        if a.target:
            n = r["sales_per_month_for_target"]
            line += f" {n if n is not None else 'n/a':>24}"
        print(line)
    print("\nAmazon.com only. Confirm the royalty KDP shows in the Rights & Pricing step.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
