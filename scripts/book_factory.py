#!/usr/bin/env python3
"""Book factory: one config file per book, two commands from page ideas to an upload-ready folder.

Everything about a book lives in books/NNN-slug/book.json (title, audience, cover options, listing
text, price, budget). The factory runs the existing scripts in order, so a book is rebuilt the same
way every time and a new session needs no memory of earlier command lines.

  python3 scripts/book_factory.py check  books/NNN-slug     # config, banned terms, repeats, pricing (free)
  python3 scripts/book_factory.py pages  books/NNN-slug     # restore or generate pages, QA, contact sheets
  ... look at every contact sheet (books/NNN-slug/review/), reroll bad pages, run `pages` again ...
  python3 scripts/book_factory.py finish books/NNN-slug --reviewed
        # interior PDF, cover, listing.md (the owner's upload kit), archive into final/

Human checkpoints that stay on purpose:
  * `pages` spends money only when images are missing, and only inside the book's `budget_usd`.
  * `finish` refuses to run without --reviewed: someone must have looked at every page (the QA script
    only catches mechanical problems), and it refuses while mechanical QA still flags pages unless
    --accept-flags lists why.
  * The owner uploads and publishes. Nothing here logs in to KDP.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bi = _load("build_interior")
gi = _load("generate_images")
mc = _load("make_cover")
ab = _load("archive_book")
kp = _load("kdp_pricing")
rn = _load("research_niches")

TOTAL_CAP_USD = 25.0  # owner's total for image generation + proof copies (raised from $20 on 2026-11-14)
DEFAULT_BOOK_CAP_USD = 4.0
PLACEHOLDER = "PLACEHOLDER"
REQUIRED = ["title", "subtitle", "author", "imprint", "audience", "theme", "description", "keywords",
            "categories", "price_usd", "blurb", "badge", "cover_art", "stickers"]
STOPWORDS = set("a an the and or of in on with to for by at from its his her their two three four little big small "
                "cute happy smiling friendly cozy pretty tiny".split())


class FactoryError(Exception):
    pass


# ----------------------------------------------------------------------------- config
def load_config(book: Path) -> dict:
    path = book / "book.json"
    if not path.is_file():
        raise FactoryError(f"{path} not found (copy books/book.template.json and fill it in)")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in cfg]
    if missing:
        raise FactoryError(f"{path}: missing field(s): {', '.join(missing)}")
    if cfg["audience"] not in ("kids", "adult"):
        raise FactoryError("audience must be 'kids' or 'adult'")
    cfg.setdefault("budget_usd", DEFAULT_BOOK_CAP_USD)
    cfg.setdefault("model", "openai/gpt-image-2")
    cfg.setdefault("quality", "low")
    cfg.setdefault("trim", "8.5x11")
    cfg.setdefault("seed", 3)
    return cfg


def is_placeholder(cfg: dict) -> bool:
    return bool(cfg.get("author_is_placeholder")) or PLACEHOLDER in cfg["author"].upper()


def page_files(folder: Path) -> list[Path]:
    return [p for p in bi.list_images(folder)] if folder.is_dir() else []


def page_by_number(pages: list[Path], n: int) -> Path:
    for p in pages:
        if p.name.startswith(f"{n:02d}_"):
            return p
    if 1 <= n <= len(pages):
        return pages[n - 1]
    raise FactoryError(f"page {n} not found")


def content_words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOPWORDS and len(w) > 2}


def repeated_subjects(subjects: list[str], others: dict[str, list[str]], threshold: float = 0.6) -> list[str]:
    """Page ideas that repeat an idea from another book (word overlap), so the catalog has no near-duplicates."""
    out = []
    for s in subjects:
        a = content_words(s)
        for name, lines in others.items():
            for o in lines:
                b = content_words(o)
                if a and b and len(a & b) / min(len(a), len(b)) >= threshold:
                    out.append(f"'{s}' repeats {name}: '{o}'")
    return out


def catalog_subjects(book: Path) -> dict[str, list[str]]:
    out = {}
    for other in sorted(book.parent.iterdir()):
        f = other / "subjects.txt"
        if other.is_dir() and other.resolve() != book.resolve() and f.is_file():
            out[other.name] = gi.read_subjects(f)
    return out


def other_page_dirs(book: Path) -> list[Path]:
    return [d / "final" / "pages" for d in sorted(book.parent.iterdir())
            if d.is_dir() and d.resolve() != book.resolve() and (d / "final" / "pages").is_dir()]


def total_spend(books_dir: Path) -> float:
    """All image spending recorded in the repo's book ledgers (working copy if present, else archived)."""
    total = 0.0
    for d in sorted(books_dir.iterdir()):
        if d.is_dir():
            work, final = d / "pages" / "ledger.jsonl", d / "final" / "ledger.jsonl"
            total += gi.ledger_spend(work if work.is_file() else final)
    extra = books_dir.parent / "tracking" / "other_spend.json"  # bake-offs, tests, proof copies
    if extra.is_file():
        total += sum(float(r.get("usd", 0)) for r in json.loads(extra.read_text()))
    return round(total, 4)


def interior_pages(cfg: dict, n_art: int) -> int:
    n = 4 + 2 * n_art + 2  # title, copyright, belongs-to, blank; art + blank backs; test page leaf
    return n + (n % 2)


def check(book: Path, cfg: dict) -> tuple[list[str], list[str]]:
    """(problems that block the build, warnings)."""
    problems, warnings = [], []
    banned = rn.load_banned()
    subjects = gi.read_subjects(book / "subjects.txt") if (book / "subjects.txt").is_file() else []
    if not subjects:
        problems.append("subjects.txt is missing or empty")
    texts = {"title": cfg["title"], "subtitle": cfg["subtitle"], "description": cfg["description"],
             **{f"keyword {i + 1}": k for i, k in enumerate(cfg["keywords"])},
             **{f"page idea {i + 1}": s for i, s in enumerate(subjects)}}
    for where, text in texts.items():
        hit = rn.banned_hit(re.sub(r"<[^>]+>", " ", text), banned)
        if hit:
            problems.append(f"banned term '{hit}' in {where}")
    if len(cfg["keywords"]) != 7:
        problems.append(f"need exactly 7 keywords, have {len(cfg['keywords'])}")
    for i, k in enumerate(cfg["keywords"], start=1):
        if len(k) > 50:
            problems.append(f"keyword {i} is {len(k)} characters (KDP limit 50)")
    if len(cfg["description"]) > 4000:
        problems.append("description is over 4000 characters")
    if re.search(r"(?i)\blittle fox\b(?! paper co)", " ".join(texts.values()) + " " + cfg["imprint"]):
        problems.append("'Little Fox' used without the full name 'Little Fox Paper Co'")
    if "little fox" in cfg["author"].lower():
        problems.append("the brand must not be in the Author field")
    if is_placeholder(cfg):
        warnings.append(f"author is still a placeholder ({cfg['author']}): the owner must pick the pen name before upload")
    if "black and white" not in " ".join(cfg["blurb"]).lower():
        problems.append("back-cover blurb must say the inside pages are black and white")
    if "black and white" not in cfg["description"].lower():
        problems.append("description must say the inside pages are black and white")
    badge_n = re.match(r"\s*(\d+)", cfg["badge"])
    if subjects and badge_n and int(badge_n.group(1)) != len(subjects):
        problems.append(f"badge says {badge_n.group(1)} pictures but there are {len(subjects)} page ideas")
    m = re.search(r"\b(\d+)\b", cfg["subtitle"])
    if subjects and m and int(m.group(1)) != len(subjects) and "ages" not in cfg["subtitle"][max(0, m.start() - 6):m.start()].lower():
        problems.append(f"subtitle says {m.group(1)} but there are {len(subjects)} page ideas")
    warnings += repeated_subjects(subjects, catalog_subjects(book))
    if subjects:
        pages = interior_pages(cfg, len(subjects))
        r = kp.royalty(cfg["price_usd"], pages, bi.parse_trim(cfg["trim"]))
        if r <= 0:
            problems.append(f"royalty at ${cfg['price_usd']:.2f} is ${r:.2f}: below KDP's minimum list price")
        elif r < 1.5:
            warnings.append(f"royalty at ${cfg['price_usd']:.2f} is only ${r:.2f} per copy "
                            f"(50% rate below $9.99; at $9.99 it is ${kp.royalty(9.99, pages):.2f})")
        if len(subjects) < 40:
            warnings.append(f"{len(subjects)} pictures is thin for the price; 50 pictures cost the same to print (up to 110 pages)")
    return problems, warnings


# ----------------------------------------------------------------------------- pages
def contact_sheets(pages: list[Path], out_dir: Path, per: int = 10, cols: int = 5, thumb: int = 400) -> list[Path]:
    from PIL import Image, ImageDraw

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet_*.png"):
        old.unlink()
    th = int(thumb * 4 / 3)
    sheets = []
    for k in range(0, len(pages), per):
        chunk = pages[k:k + per]
        rows = -(-len(chunk) // cols)
        sheet = Image.new("L", (cols * thumb, rows * (th + 26)), 255)
        d = ImageDraw.Draw(sheet)
        for i, p in enumerate(chunk):
            im = Image.open(p).convert("L")
            im.thumbnail((thumb - 8, th - 8))
            x, y = (i % cols) * thumb, (i // cols) * (th + 26)
            sheet.paste(im, (x + 4, y + 24))
            d.text((x + 6, y + 4), p.name[:44], fill=0)
        path = out_dir / f"sheet_{k // per + 1:02d}.png"
        sheet.save(path)
        sheets.append(path)
    return sheets


def cmd_pages(book: Path, cfg: dict, generate: bool, log=print) -> int:
    pages_dir = book / "pages"
    if not page_files(pages_dir) and (book / "final" / "pages").is_dir():
        info = ab.restore(book)
        log(f"restored {info['copied']} page(s) from final/")
    subjects = gi.read_subjects(book / "subjects.txt")
    have = page_files(pages_dir)
    missing = len(subjects) - len(have)
    if missing > 0:
        if not generate:
            log(f"{missing} page(s) missing. Re-run with --generate to create them (cap ${cfg['budget_usd']:.2f} for this book).")
            return 3
        spent_all = total_spend(book.parent)
        if spent_all >= TOTAL_CAP_USD:
            log(f"total spend ${spent_all:.2f} has reached the ${TOTAL_CAP_USD:.0f} cap: not generating")
            return 3
        budget = min(cfg["budget_usd"], gi.ledger_spend(pages_dir / "ledger.jsonl") + (TOTAL_CAP_USD - spent_all))
        argv = ["generate", str(book / "subjects.txt"), "-o", str(pages_dir), "--model", cfg["model"],
                "--quality", cfg["quality"], "--budget", f"{budget:.2f}"]
        if cfg.get("style_file"):
            argv += ["--style-file", str(ROOT / cfg["style_file"])]
        else:
            argv += ["--style", cfg["audience"]]
        if cfg.get("extra"):
            argv += ["--extra", cfg["extra"]]
        code = gi.main(argv)
        if code:
            return code
        have = page_files(pages_dir)
    results = bi.run_qa(have, cfg["audience"], [p for d in other_page_dirs(book) for p in bi.list_images(d)])
    flagged = [r for r in results if r["flags"]]
    review = book / "review"
    sheets = contact_sheets(have, review)
    (review / "qa.json").write_text(json.dumps(results, indent=1))
    log(f"{len(have)} page(s); mechanical QA flagged {len(flagged)}; spend this book ${gi.ledger_spend(pages_dir / 'ledger.jsonl'):.2f}")
    for r in flagged:
        log(f"  {r['file']}: " + "; ".join(r["flags"]))
    log(f"contact sheets to look at: {', '.join(str(s) for s in sheets)}")
    log("Next: open every sheet. To redo a page, delete its file in pages/ and run `pages --generate` again. "
        "Then: finish --reviewed")
    return 0


# ----------------------------------------------------------------------------- finish
def cover_argv(book: Path, cfg: dict, pages: list[Path], n_pages: int) -> list[str]:
    argv = [str(page_by_number(pages, cfg["cover_art"])), "-o", str(book / "cover.pdf"),
            "--title", cfg["title"], "--subtitle", cfg["subtitle"], "--author", cfg["author"],
            "--imprint", cfg["imprint"], "--pages", str(n_pages), "--trim", cfg["trim"],
            "--theme", cfg["theme"], "--badge", cfg["badge"], "--seed", str(cfg["seed"]),
            "--blurb", "|".join(cfg["blurb"]), "--colored-half",
            "--stickers", *[str(page_by_number(pages, n)) for n in cfg["stickers"]]]
    return argv


def cmd_finish(book: Path, cfg: dict, reviewed: bool, accept_flags: str = "", log=print) -> int:
    if not reviewed:
        log("refusing: pass --reviewed once every page on the contact sheets has been looked at")
        return 3
    problems, warnings = check(book, cfg)
    for w in warnings:
        log(f"warning: {w}")
    if problems:
        for p in problems:
            log(f"problem: {p}")
        return 2
    pages = page_files(book / "pages")
    subjects = gi.read_subjects(book / "subjects.txt")
    if len(pages) != len(subjects):
        log(f"problem: {len(pages)} page images for {len(subjects)} page ideas (run `pages` first)")
        return 2
    results = bi.run_qa(pages, cfg["audience"], [p for d in other_page_dirs(book) for p in bi.list_images(d)])
    flagged = [r for r in results if r["flags"]]
    if flagged and not accept_flags:
        for r in flagged:
            log(f"  {r['file']}: " + "; ".join(r["flags"]))
        log("problem: mechanical QA still flags pages. Fix them, or pass --accept-flags \"reason\" after looking at each.")
        return 2
    interior = book / "interior.pdf"
    argv = ["build", str(book / "pages"), "-o", str(interior), "--title", cfg["title"], "--subtitle", cfg["subtitle"],
            "--author", cfg["author"], "--imprint", cfg["imprint"], "--trim", cfg["trim"],
            "--title-art", str(cfg.get("title_art", cfg["cover_art"])),
            "--display-font", "none" if cfg["audience"] == "adult" else "auto"]
    if cfg.get("threshold"):
        argv += ["--threshold", str(cfg["threshold"])]
    code = bi.main(argv)
    if code:
        return code
    from pypdf import PdfReader

    n_pages = len(PdfReader(str(interior)).pages)
    code = mc.main(cover_argv(book, cfg, pages, n_pages))
    if code:
        return code
    kit = upload_kit(book, cfg, n_pages, len(pages), accept_flags, [r for r in flagged])
    (book / "listing.md").write_text(kit, encoding="utf-8")
    info = ab.archive(book)
    (book / "final" / "UPLOAD_KIT.md").write_text(kit, encoding="utf-8")
    log(f"finished: {n_pages} pages, final/ {info['bytes'] / 1e6:.1f} MB, spend ${info['spend_usd']:.2f}. "
        f"Owner kit: {book / 'listing.md'}")
    return 0


# ----------------------------------------------------------------------------- upload kit
def upload_kit(book: Path, cfg: dict, n_pages: int, n_art: int, accept_flags: str = "", flagged=()) -> str:
    trim = bi.parse_trim(cfg["trim"])
    price = cfg["price_usd"]
    g = mc.cover_geometry(n_pages, trim)
    adult = cfg["audience"] == "adult"
    placeholder = is_placeholder(cfg)
    age = cfg.get("reading_age")
    L = [
        f"# Upload kit: {cfg['title']}",
        "",
        f"Generated {datetime.date.today().isoformat()} by `scripts/book_factory.py` from `book.json`. "
        "Do not edit by hand: change `book.json` and run `finish` again. About 10 minutes in KDP. "
        "You upload and publish; Claude never logs in to KDP.",
        "",
        "## Before you start (one time per pen name)",
        f"- [ ] Search Amazon Books for the author name **\"{cfg['author']}\"** (in quotes). If an author with that exact name already has books, stop and tell Claude: the name cannot be changed after publishing.",
    ]
    if placeholder:
        L.append("- [ ] **The author name on this book is a placeholder.** Pick the adult pen name (see `research/pen_names.md`), tell Claude, and the files are rebuilt in a few minutes.")
    L += [
        "",
        "## 1. Files (in this folder's `final/`)",
        f"- Manuscript: `interior.pdf` ({n_pages} pages, {trim[0]:g} x {trim[1]:g} in, no bleed, {n_art} pictures)",
        f"- Cover: `cover.pdf` ({g['total_w']:.4f} x {g['total_h']:.4f} in, spine {g['spine']:.4f} in for white paper)",
        "",
        "## 2. Paperback details (paste each field)",
        "| Field | Value |",
        "|---|---|",
        "| Language | English |",
        f"| Book title | {cfg['title']} |",
        f"| Subtitle | {cfg['subtitle']} |",
        f"| Series | {cfg.get('series') or 'leave blank'} |",
        "| Edition number | leave blank |",
        f"| Author (first / last name) | {cfg['author']} |",
        "| Contributors | leave blank (never put Little Fox Paper Co here) |",
        "| Publishing rights | I own the copyright and I hold the necessary publishing rights (see note A) |",
        "| Sexually explicit images or title | No |",
        f"| Reading age | {'leave blank (adult audience, not adult content)' if adult or not age else f'minimum {age[0]}, maximum {age[1]}'} |",
        "| Primary marketplace | Amazon.com |",
        "| Low-content book box | leave unticked: KDP's help says coloring books are generally not low-content **[verify in the form]** |",
        "| Large-print box | leave unticked |",
        "",
        "**Description** (paste as is; the box accepts this formatting):",
        "```",
        cfg["description"],
        "```",
        "",
        "**Categories** (choose up to three; pick the closest entries the menu offers **[verify]**):",
        *[f"{i}. {c}" for i, c in enumerate(cfg["categories"], start=1)],
        "",
        "**Keywords** (one per box):",
        *[f"{i}. {k}" for i, k in enumerate(cfg["keywords"], start=1)],
        "",
        "## 3. Paperback content",
        "| Field | Value |",
        "|---|---|",
        "| ISBN | Get a free KDP ISBN |",
        "| Publication date | leave blank |",
        "| Ink and paper | Black & white interior with **white** paper |",
        f"| Trim size | {trim[0]:g} x {trim[1]:g} in |",
        "| Bleed | No bleed |",
        "| Cover finish | Matte (your choice; no effect on cost) |",
        "| Manuscript | upload `interior.pdf` |",
        "| Cover | \"Upload a cover you already have\": `cover.pdf`. Do not add your own barcode. |",
        "| AI-generated content | **Yes** |",
        "| AI: texts | None (title, copyright and \"belongs to\" lines were written by us). If you count the store description, which Claude drafted, answer \"Some sections, with extensive editing\" **[verify the options the form shows]** |",
        f"| AI: images | Many AI-generated images, with minimal or no editing. Tool: {cfg.get('ai_tool', 'GPT Image 2 (OpenAI) via OpenRouter')} |",
        "| AI: translations | None |",
        "",
        "Then open the **previewer** and page through the whole book: no picture may touch a page edge, and the cover text must sit inside the dotted lines.",
        "",
        "## 4. Rights and pricing",
        "- Territories: all territories (worldwide rights).",
        f"- **List price on Amazon.com: ${price:.2f}** (royalty about ${kp.royalty(price, n_pages, trim):.2f} per copy). Let KDP convert the other marketplaces.",
        "- Expanded Distribution: leave off.",
        "",
        kp.markdown_table(n_pages, trim),
        "",
        f"Amazon.com pays 50% of list price up to $9.98 and 60% from $9.99, minus the ${kp.printing_cost(n_pages, trim):.2f} printing cost (KDP help, checked 2026-11-14). The form shows the real figure: use it if it differs.",
        "",
        "## 5. Before you press Publish",
        "- [ ] Author name searched on Amazon (top of this page)",
        "- [ ] Every page looked at in the previewer",
        "- [ ] AI-generated content answered **Yes**",
        "- [ ] Order a **proof copy** first if this is the first book in this style (KDP: \"Request printed proofs\"); check line quality, margins and cover colors",
        f"- [ ] After it goes live: tell Claude the publication date (it is recorded in `book.json` as `published`) so the sales tracker starts counting",
        "",
        "## Notes",
        "- **A. Copyright.** The pictures were generated with AI image tools. In the US, purely AI-generated images may not be protected by copyright (US Copyright Office guidance; not legal advice **[verify]**). The book's copyright page therefore claims only the selection, arrangement and design. KDP's rights question has only two options; \"I own the copyright\" refers to your right to publish this book, and the other option (public domain) does not fit.",
        "- **B. AI disclosure.** KDP requires it for AI-generated images and says so in its Content Guidelines (checked 2026-11-14). The copyright page and the description also say it. Never remove it.",
        "- **C. Brand.** The imprint is always written in full: Little Fox Paper Co. It appears on the cover, title page and copyright page only.",
    ]
    if accept_flags:
        L.append(f"- **D. QA note.** Mechanical QA flagged {len(flagged)} page(s); accepted after a look because: {accept_flags}")
    for n in cfg.get("notes", []):
        L.append(f"- {n}")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- cli
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["check", "pages", "finish", "kit", "spend"])
    p.add_argument("book", type=Path, help="books/NNN-slug")
    p.add_argument("--generate", action="store_true", help="pages: create missing images (paid, inside the book's budget)")
    p.add_argument("--reviewed", action="store_true", help="finish: confirm every page was looked at")
    p.add_argument("--accept-flags", default="", help="finish: reason for accepting pages that mechanical QA flags")
    a = p.parse_args(argv)
    try:
        if a.command == "spend":
            print(f"total recorded spend: ${total_spend(a.book if a.book.name == 'books' else a.book.parent):.2f} of ${TOTAL_CAP_USD:.0f}")
            return 0
        cfg = load_config(a.book)
        if a.command == "check":
            problems, warnings = check(a.book, cfg)
            for w in warnings:
                print(f"warning: {w}")
            for pr in problems:
                print(f"problem: {pr}")
            print("ok" if not problems else f"{len(problems)} problem(s)")
            return 2 if problems else 0
        if a.command == "pages":
            return cmd_pages(a.book, cfg, a.generate)
        if a.command == "kit":
            from pypdf import PdfReader

            n = len(PdfReader(str(a.book / "final" / "interior.pdf")).pages)
            kit = upload_kit(a.book, cfg, n, len(page_files(a.book / "final" / "pages")))
            (a.book / "listing.md").write_text(kit, encoding="utf-8")
            (a.book / "final" / "UPLOAD_KIT.md").write_text(kit, encoding="utf-8")
            print(f"wrote {a.book / 'listing.md'}")
            return 0
        return cmd_finish(a.book, cfg, a.reviewed, a.accept_flags)
    except FactoryError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
