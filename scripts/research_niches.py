#!/usr/bin/env python3
"""Research gate: find and rank coloring-book niches before any money or time goes into a book.

Two data sources, kept separate on purpose:

1. DEMAND PROXY (automatic, free): Amazon's public search-suggestion endpoint. A phrase Amazon suggests
   for a short prefix is something shoppers actually type. It says nothing about competition.
2. COMPETITION (manual or browser-sourced): a worksheet per keyword with the top 10 search results
   (BSR, reviews, price, pages, publication date). Amazon blocks automated page fetches, and this
   project does not work around that, so a person (or a browser session the owner links) fills it in.

Subcommands
-----------
harvest    Query the suggestion endpoint for seeds (and optional a-z expansions); save raw results.
rank       Score harvested phrases, drop banned/off-brand ones, merge any filled worksheets and write
           a ranked markdown report with a GO / MAYBE / NO / UNVERIFIED verdict per niche.
worksheet  Write an empty competitor worksheet (CSV) for a keyword, with the exact columns to fill.

Usage:
  python3 scripts/research_niches.py harvest --seeds research/seeds.txt --expand -o research/autocomplete/2026-11-14.json
  python3 scripts/research_niches.py worksheet "bold and easy coloring book for adults"
  python3 scripts/research_niches.py rank research/autocomplete/2026-11-14.json -o research/niches_2026-11-14.md

The suggestion endpoint is called slowly (one request every --delay seconds) with a plain client: no
spoofed browser headers, no retries on refusals. If Amazon refuses, the run stops and says so.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import statistics
import string
import sys
import time
from pathlib import Path

ENDPOINT = "https://completion.amazon.com/api/2017/suggestions"
MARKETPLACE_US = "ATVPDKIKX0DER"
ROOT = Path(__file__).resolve().parent.parent
BANNED_FILE = ROOT / "prompts" / "banned_terms.txt"
WORKSHEET_DIR = ROOT / "research" / "competitors"

WORKSHEET_COLUMNS = [
    "keyword",          # the exact search phrase
    "position",         # 1-10, organic results only (skip "Sponsored")
    "title",
    "author",
    "asin",
    "bsr",              # Best Sellers Rank in Books (number only, e.g. 45210)
    "reviews",          # number of ratings
    "rating",           # stars, e.g. 4.6
    "price",            # paperback list price in USD
    "pages",            # print length
    "pub_date",         # YYYY-MM-DD (or YYYY-MM)
    "series",           # yes / no
    "notes",            # e.g. "looks AI-made", "big publisher", "50 pictures", "licensed characters"
]

# verdict thresholds (see rank_keyword). Conservative on purpose: a GO needs proof that small,
# recent, low-review books are selling in the niche.
BSR_SELLING = 150_000      # a paperback at or under this rank sells roughly daily [verify]
LOW_REVIEWS = 150          # "a newcomer could plausibly compete with this"
RECENT_DAYS = 548          # published within ~18 months


def slug(s: str, n: int = 60) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n] or "keyword"


def load_banned(path: Path = BANNED_FILE) -> list[str]:
    if not path.is_file():
        return []
    return [ln.strip().lower() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def banned_hit(phrase: str, banned: list[str]) -> str | None:
    p = f" {phrase.lower()} "
    for term in banned:
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", p):
            return term
    return None


# ----------------------------------------------------------------------------- harvest
def parse_suggestions(payload: dict) -> list[str]:
    return [s["value"].strip() for s in payload.get("suggestions", []) if s.get("value")]


def fetch_suggestions(sess, prefix: str, alias: str = "stripbooks") -> list[str]:
    r = sess.get(ENDPOINT, params={"mid": MARKETPLACE_US, "alias": alias, "prefix": prefix}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"suggestion endpoint returned HTTP {r.status_code} for {prefix!r}")
    return parse_suggestions(r.json())


def prefixes_for(seed: str, expand: bool) -> list[str]:
    out = [seed]
    if expand:
        out += [f"{seed} {ch}" for ch in string.ascii_lowercase]
    return out


def harvest(seeds: list[str], expand: bool, delay: float, sess=None, sleep=time.sleep, fetch=fetch_suggestions) -> dict:
    """{'date':..., 'queries': {prefix: [suggestions in rank order]}, 'seeds': [...]}"""
    if sess is None:
        import requests

        sess = requests.Session()
    queries: dict[str, list[str]] = {}
    for seed in seeds:
        for prefix in prefixes_for(seed, expand):
            if prefix in queries:
                continue
            queries[prefix] = fetch(sess, prefix)
            sleep(delay)
    return {"date": datetime.date.today().isoformat(), "seeds": seeds, "expand": expand, "queries": queries}


def read_seeds(path: Path) -> list[str]:
    return [ln.strip().lower() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


# ----------------------------------------------------------------------------- scoring
def demand_scores(data: dict) -> dict[str, dict]:
    """Score each suggested phrase. A phrase earns more when it is suggested for a SHORT prefix and at
    a HIGH position: 'coloring book' -> 'coloring book for adults' beats a phrase that only appears
    after typing most of it. This is a relative proxy for search interest, not a search volume."""
    out: dict[str, dict] = {}
    for prefix, suggestions in data["queries"].items():
        for pos, phrase in enumerate(suggestions, start=1):
            if phrase == prefix:
                continue
            typed = len(prefix) / max(len(phrase), 1)  # share of the phrase the shopper had to type
            pts = (11 - min(pos, 10)) * (1.0 - min(typed, 0.95))
            row = out.setdefault(phrase, {"phrase": phrase, "score": 0.0, "hits": 0, "best_pos": pos, "via": []})
            row["score"] += pts
            row["hits"] += 1
            row["best_pos"] = min(row["best_pos"], pos)
            row["via"].append(prefix)
    for row in out.values():
        row["score"] = round(row["score"], 2)
    return out


# ----------------------------------------------------------------------------- competition
def _num(v: str) -> float | None:
    v = re.sub(r"[^0-9.]", "", v or "")
    try:
        return float(v) if v else None
    except ValueError:
        return None


def _date(v: str) -> datetime.date | None:
    m = re.match(r"\s*(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", v or "")
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
    except ValueError:
        return None


def read_worksheet(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("title") or "").strip()]
    return rows


def rank_keyword(rows: list[dict], today: datetime.date | None = None) -> dict:
    """Competition summary and verdict for one keyword's top-10 worksheet."""
    today = today or datetime.date.today()
    n = len(rows)
    if n < 5:
        return {"verdict": "UNVERIFIED", "why": f"only {n} competitor rows filled in (need at least 5)", "rows": n}
    bsr = [_num(r.get("bsr", "")) for r in rows]
    rev = [_num(r.get("reviews", "")) for r in rows]
    price = [v for v in (_num(r.get("price", "")) for r in rows) if v]
    pages = [v for v in (_num(r.get("pages", "")) for r in rows) if v]
    selling = sum(1 for b in bsr if b is not None and b <= BSR_SELLING)
    # the proof we want: books that sell although they are small (few reviews) or new
    beatable = 0
    for r, b, v in zip(rows, bsr, rev):
        d = _date(r.get("pub_date", ""))
        recent = d is not None and (today - d).days <= RECENT_DAYS
        if b is not None and b <= BSR_SELLING and ((v is not None and v <= LOW_REVIEWS) or recent):
            beatable += 1
    known_rev = [v for v in rev if v is not None]
    summary = {
        "rows": n,
        "selling": selling,
        "beatable": beatable,
        "median_reviews": statistics.median(known_rev) if known_rev else None,
        "median_price": round(statistics.median(price), 2) if price else None,
        "median_pages": int(statistics.median(pages)) if pages else None,
    }
    if selling < 3:
        v, why = "NO", f"only {selling} of the top {n} sell at BSR <= {BSR_SELLING:,}: little demand reaches this keyword"
    elif beatable >= 3:
        v, why = "GO", f"{beatable} of the top {n} sell with <= {LOW_REVIEWS} reviews or a recent publication date"
    elif beatable >= 1:
        v, why = "MAYBE", f"only {beatable} small or recent book(s) sell here; the rest are entrenched"
    else:
        v, why = "NO", "every selling book is entrenched (many reviews, older titles)"
    return {"verdict": v, "why": why, **summary}


def worksheet_path(keyword: str, folder: Path = WORKSHEET_DIR) -> Path:
    return folder / f"{slug(keyword)}.csv"


def write_worksheet(keyword: str, folder: Path = WORKSHEET_DIR) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = worksheet_path(keyword, folder)
    if path.exists():
        return path
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(WORKSHEET_COLUMNS)
        for i in range(1, 11):
            w.writerow([keyword, i] + [""] * (len(WORKSHEET_COLUMNS) - 2))
    return path


# ----------------------------------------------------------------------------- report
def build_report(data: dict, banned: list[str], top: int, folder: Path = WORKSHEET_DIR,
                 today: datetime.date | None = None) -> tuple[str, list[dict]]:
    scores = demand_scores(data)
    kept, dropped = [], []
    for row in scores.values():
        hit = banned_hit(row["phrase"], banned)
        (dropped if hit else kept).append({**row, "banned": hit})
    kept.sort(key=lambda r: (-r["score"], r["phrase"]))
    kept = kept[:top]
    order = {"GO": 0, "MAYBE": 1, "UNVERIFIED": 2, "NO": 3}
    for row in kept:
        ws = worksheet_path(row["phrase"], folder)
        row["competition"] = rank_keyword(read_worksheet(ws), today) if ws.is_file() else {
            "verdict": "UNVERIFIED", "why": "no competitor worksheet yet"}
    kept.sort(key=lambda r: (order[r["competition"]["verdict"]], -r["score"]))
    lines = [
        f"# Niche research report ({data.get('date', 'undated')})",
        "",
        f"Source: Amazon search suggestions (Books) for {len(data['queries'])} prefixes from {len(data.get('seeds', []))} seeds."
        " The demand score is a relative proxy (suggested early for a short prefix = typed often), **not** a search volume.",
        "Competition comes only from filled worksheets in `research/competitors/`. **UNVERIFIED = do not build a book yet.**",
        "",
        "| # | Verdict | Keyword | Demand score | Suggested for | Competition (top 10) |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(kept, start=1):
        c = r["competition"]
        comp = c["why"]
        if "median_reviews" in c:
            comp += (f"; median reviews {c['median_reviews']:g}" if c["median_reviews"] is not None else "") + \
                    (f", median price ${c['median_price']:.2f}" if c.get("median_price") else "") + \
                    (f", median pages {c['median_pages']}" if c.get("median_pages") else "")
        lines.append(f"| {i} | **{c['verdict']}** | {r['phrase']} | {r['score']:g} | {r['hits']} prefix(es), best position {r['best_pos']} | {comp} |")
    lines += ["", f"Dropped {len(dropped)} phrase(s) for banned or off-brand terms (brands, characters, educational positioning)."]
    if dropped:
        lines.append("Examples: " + "; ".join(f"{d['phrase']} ({d['banned']})" for d in sorted(dropped, key=lambda d: -d['score'])[:8]))
    lines += [
        "",
        "## How to verify a niche (about 10 minutes each)",
        "1. `python3 scripts/research_niches.py worksheet \"<keyword>\"` creates `research/competitors/<keyword>.csv`.",
        "2. Search the keyword on amazon.com (Books). For the first 10 organic results fill: title, author, ASIN, "
        "Best Sellers Rank, number of ratings, stars, paperback price, pages, publication date, series yes/no, notes.",
        "3. Re-run `rank`. GO = at least 3 of the top 10 sell (BSR <= 150,000) with <= 150 reviews or published in the last 18 months.",
        "",
        f"Worksheet columns: `{', '.join(WORKSHEET_COLUMNS)}`",
    ]
    return "\n".join(lines) + "\n", kept


# ----------------------------------------------------------------------------- cli
def cmd_harvest(a) -> int:
    seeds = read_seeds(Path(a.seeds)) if a.seeds else []
    seeds += [s.lower() for s in a.seed or []]
    if not seeds:
        print("no seeds: pass --seeds FILE or --seed 'phrase'", file=sys.stderr)
        return 2
    try:
        data = harvest(seeds, a.expand, a.delay)
    except Exception as e:  # network refusal: stop, do not work around it
        print(f"stopped: {e}", file=sys.stderr)
        return 1
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    n = len({s for v in data["queries"].values() for s in v})
    print(f"{len(data['queries'])} prefixes, {n} distinct suggestions -> {out}")
    return 0


def cmd_rank(a) -> int:
    data = json.loads(Path(a.harvest).read_text(encoding="utf-8"))
    report, kept = build_report(data, load_banned(), a.top, Path(a.worksheets))
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(report, encoding="utf-8")
        print(f"wrote {a.output} ({len(kept)} keywords)")
    else:
        print(report)
    return 0


def cmd_worksheet(a) -> int:
    for kw in a.keyword:
        print(write_worksheet(kw.lower(), Path(a.worksheets)))
    return 0


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harvest", help="collect search suggestions for seed phrases")
    h.add_argument("--seeds", help="file with one seed phrase per line")
    h.add_argument("--seed", action="append", help="a seed phrase (repeatable)")
    h.add_argument("--expand", action="store_true", help="also query '<seed> a' ... '<seed> z'")
    h.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1)")
    h.add_argument("-o", "--output", required=True)
    h.set_defaults(func=cmd_harvest)
    r = sub.add_parser("rank", help="rank harvested phrases and merge competitor worksheets")
    r.add_argument("harvest")
    r.add_argument("--top", type=int, default=40)
    r.add_argument("--worksheets", default=str(WORKSHEET_DIR))
    r.add_argument("-o", "--output")
    r.set_defaults(func=cmd_rank)
    w = sub.add_parser("worksheet", help="create an empty competitor worksheet for a keyword")
    w.add_argument("keyword", nargs="+")
    w.add_argument("--worksheets", default=str(WORKSHEET_DIR))
    w.set_defaults(func=cmd_worksheet)
    return p


def main(argv=None) -> int:
    a = make_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
