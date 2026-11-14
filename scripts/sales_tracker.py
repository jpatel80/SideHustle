#!/usr/bin/env python3
"""Sales tracker: turn the KDP sales reports the owner downloads into one page of decisions.

Owner routine (about 5 minutes a month):
  1. KDP > Reports > (Royalties Estimator or Month-to-Date / Prior Months' Royalties) > download the
     report for the month (.xlsx or .csv) [verify the menu names in your account].
  2. Put the file in tracking/kdp_reports/ (any name) and tell Claude, or upload it in a session.
  3. Claude runs:  python3 scripts/sales_tracker.py   -> tracking/REPORT.md

The script reads every file in tracking/kdp_reports/, finds the title / units / royalty / date columns
by their header names (KDP changes the layout from time to time), matches rows to books by title, and
applies the kill rule below. Publication dates come from `published` in each books/NNN-slug/book.json.

Kill rule (per book):
  * live < 60 days                      -> TOO EARLY
  * live >= 60 days, 0 units in 60 days -> RETIRE NICHE (leave the listing up; make no more books like it)
  * >= 8 units in the last 30 days      -> SCALE (make a sibling / volume 2 in the same niche)
  * otherwise                           -> HOLD (one listing fix, look again in 30 days)
Portfolio gate: 90 days after the first book went live, if no book is at SCALE, add no money.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EARLY_DAYS, WINDOW_DAYS, SCALE_UNITS_30, GATE_DAYS = 60, 60, 8, 90
HEADERS = {  # canonical field -> header fragments, first match wins (lower case)
    "title": ["title"],
    "units": ["net units sold", "net units", "units sold", "units"],
    "royalty": ["royalty"],
    "date": ["royalty date", "order date", "date", "month"],
    "currency": ["currency"],
    "marketplace": ["marketplace"],
}


def norm_title(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def parse_date(v) -> datetime.date | None:
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v or "").strip()
    for pat, fmt in ((r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"\d{4}-\d{2}", "%Y-%m"), (r"\d{1,2}/\d{1,2}/\d{4}", "%m/%d/%Y"),
                     (r"[A-Za-z]+ \d{4}", "%B %Y")):
        m = re.match(pat, s)
        if m:
            try:
                return datetime.datetime.strptime(m.group(0), fmt).date()
            except ValueError:
                continue
    return None


def num(v) -> float:
    s = re.sub(r"[^0-9.\-]", "", str(v if v is not None else ""))
    try:
        return float(s) if s not in ("", "-", ".") else 0.0
    except ValueError:
        return 0.0


def map_headers(header: list) -> dict[str, int] | None:
    low = [str(h or "").strip().lower() for h in header]
    out = {}
    for field, frags in HEADERS.items():
        for frag in frags:
            hit = [i for i, h in enumerate(low) if frag in h and (field != "royalty" or ("date" not in h and "type" not in h))]
            if hit:
                out[field] = hit[0]
                break
    return out if {"title", "units", "royalty"} <= set(out) else None


def rows_from_table(table: list[list], source: str) -> list[dict]:
    """Find the header row (it need not be the first line) and return normalized rows."""
    for i, row in enumerate(table[:15]):
        cols = map_headers(row)
        if cols:
            out = []
            for r in table[i + 1:]:
                get = lambda f: r[cols[f]] if f in cols and cols[f] < len(r) else None
                title = str(get("title") or "").strip()
                if not title:
                    continue
                out.append({"title": title, "units": num(get("units")), "royalty": num(get("royalty")),
                            "date": parse_date(get("date")), "currency": str(get("currency") or "USD").strip() or "USD",
                            "marketplace": str(get("marketplace") or "").strip(), "source": source})
            return out
    return []


def read_report(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            return rows_from_table(list(csv.reader(f)), path.name)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("reading .xlsx needs openpyxl (pip install openpyxl), or save the report as .csv")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        rows = []
        for ws in wb.worksheets:
            if "ebook" in ws.title.lower() or "kenp" in ws.title.lower() or "combined" in ws.title.lower():
                continue  # paperback sheets only; "Combined Sales" would double count
            rows += rows_from_table([list(r) for r in ws.iter_rows(values_only=True)], f"{path.name}:{ws.title}")
        return rows
    return []


def load_books(books_dir: Path) -> list[dict]:
    out = []
    for d in sorted(books_dir.iterdir()):
        f = d / "book.json"
        if f.is_file():
            cfg = json.loads(f.read_text(encoding="utf-8"))
            out.append({"slug": d.name, "title": cfg["title"], "key": norm_title(cfg["title"]),
                        "published": parse_date(cfg.get("published")), "price": cfg.get("price_usd")})
    return out


def match_book(title: str, books: list[dict]) -> dict | None:
    t = norm_title(title)
    best = [b for b in books if t.startswith(b["key"]) or b["key"].startswith(t)]
    return max(best, key=lambda b: len(b["key"])) if best else None


def dedupe(rows: list[dict]) -> list[dict]:
    """The same sale can appear in two downloads (month-to-date, then the full month): keep one."""
    seen, out = set(), []
    for r in rows:
        k = (norm_title(r["title"]), r["date"], r["marketplace"], r["currency"], r["units"], r["royalty"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def decide(book: dict, rows: list[dict], today: datetime.date) -> dict:
    units = sum(r["units"] for r in rows)
    usd = sum(r["royalty"] for r in rows if r["currency"].upper() == "USD")
    other = defaultdict(float)
    for r in rows:
        if r["currency"].upper() != "USD":
            other[r["currency"].upper()] += r["royalty"]
    since = lambda n: sum(r["units"] for r in rows if r["date"] and (today - r["date"]).days <= n)
    u30, u60 = since(30), since(WINDOW_DAYS)
    live = (today - book["published"]).days if book["published"] else None
    if live is None:
        action, why = "NOT PUBLISHED", "no `published` date in book.json"
    elif live < EARLY_DAYS:
        action, why = "TOO EARLY", f"live {live} days; decide at day {EARLY_DAYS}"
    elif u60 == 0:
        action, why = "RETIRE NICHE", f"live {live} days and no sale in the last {WINDOW_DAYS}: make no more books like this one"
    elif u30 >= SCALE_UNITS_30:
        action, why = "SCALE", f"{u30:g} copies in 30 days: build a sibling title or volume 2 in this niche"
    else:
        action, why = "HOLD", f"{u60:g} copies in {WINDOW_DAYS} days: one listing fix (keywords, then cover), look again in 30 days"
    return {"slug": book["slug"], "title": book["title"], "published": book["published"], "days_live": live,
            "units_total": units, "units_30": u30, "units_60": u60, "royalty_usd": round(usd, 2),
            "royalty_other": {k: round(v, 2) for k, v in other.items()}, "action": action, "why": why}


def build_report(books: list[dict], rows: list[dict], today: datetime.date) -> tuple[str, list[dict]]:
    rows = dedupe(rows)
    by_book, unmatched = defaultdict(list), defaultdict(float)
    for r in rows:
        b = match_book(r["title"], books)
        if b:
            by_book[b["slug"]].append(r)
        else:
            unmatched[r["title"]] += r["units"]
    decisions = [decide(b, by_book[b["slug"]], today) for b in books]
    months = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        if r["date"] and r["currency"].upper() == "USD":
            m = months[r["date"].strftime("%Y-%m")]
            m[0] += r["units"]
            m[1] += r["royalty"]
    live = [d for d in decisions if d["published"]]
    first = min((d["published"] for d in live), default=None)
    L = [f"# Sales report ({today.isoformat()})", ""]
    if not live:
        L += ["No book has a `published` date yet. After you publish, tell Claude the date for each book.", ""]
    elif (today - first).days >= GATE_DAYS and not any(d["action"] == "SCALE" for d in decisions):
        L += [f"**Portfolio gate: STOP adding money.** {(today - first).days} days since the first book went live and no "
              "book sells 8 or more copies a month. Finish nothing new unless the research gate shows a verified GO niche.", ""]
    elif any(d["action"] == "SCALE" for d in decisions):
        L += ["**Portfolio gate: a book is selling.** Put the next book into that niche.", ""]
    else:
        L += [f"Portfolio gate: undecided ({(today - first).days} of {GATE_DAYS} days since the first book went live).", ""]
    L += ["| Book | Live (days) | Copies: 30 d / 60 d / total | Royalty (USD) | Decision | Why |", "|---|---|---|---|---|---|"]
    for d in decisions:
        extra = "".join(f" + {v:.2f} {k}" for k, v in d["royalty_other"].items())
        L.append(f"| {d['title']} | {d['days_live'] if d['days_live'] is not None else '-'} | {d['units_30']:g} / {d['units_60']:g} / "
                 f"{d['units_total']:g} | ${d['royalty_usd']:.2f}{extra} | **{d['action']}** | {d['why']} |")
    if months:
        L += ["", "| Month | Copies | Royalty (USD) |", "|---|---|---|"]
        L += [f"| {m} | {u:g} | ${r:.2f} |" for m, (u, r) in sorted(months.items())]
    if unmatched:
        L += ["", "Rows that match no book in `books/` (check the titles): " + "; ".join(f"{t} ({u:g})" for t, u in unmatched.items())]
    L += ["", f"Read {len(rows)} report row(s). Rules: decide at day {EARLY_DAYS}; no sale in {WINDOW_DAYS} days = retire the niche; "
          f"{SCALE_UNITS_30}+ copies in 30 days = scale. Royalties in other currencies are listed, not converted."]
    return "\n".join(L) + "\n", decisions


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reports", default=str(ROOT / "tracking" / "kdp_reports"))
    p.add_argument("--books", default=str(ROOT / "books"))
    p.add_argument("-o", "--output", default=str(ROOT / "tracking" / "REPORT.md"))
    p.add_argument("--today", help="YYYY-MM-DD (default: today)")
    a = p.parse_args(argv)
    today = parse_date(a.today) if a.today else datetime.date.today()
    folder = Path(a.reports)
    rows = []
    for f in sorted(folder.glob("*")) if folder.is_dir() else []:
        rows += read_report(f)
    report, _ = build_report(load_books(Path(a.books)), rows, today)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
