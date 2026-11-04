#!/usr/bin/env python3
"""Generate coloring-page art through OpenRouter's Image API (POST /api/v1/images).

Subcommands
-----------
models    Show image models and their per-image price (public endpoint, no key needed).
generate  Turn a subjects file (one page idea per line) into images, with a hard spending cap.
bakeoff   Run the same few subjects through several models, then compare cost and line quality.

The API key is read from the OPENROUTER_API_KEY environment variable only. It is never printed,
logged or written to disk.

Billing (per OpenRouter docs): a generation is billed in full or not at all; failed or cancelled
generations return an error and are not billed. Some models are priced per image, others per
megapixel or per token, so the cost of a request is read from the response's usage.cost and
tracked in <out>/ledger.jsonl. --budget stops the run before it can overspend.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BASE_DEFAULT = "https://openrouter.ai/api/v1"
DEFAULT_ASSUMED_COST = 0.05  # reservation for the first call when the price is not known
CANDIDATE_MODELS = [
    "recraft/recraft-v4.1",
    "recraft/recraft-v4.1-vector",
    "qwen/qwen-image-3",
    "krea/krea-2-medium",
    "bytedance-seed/seedream-5-0-lite",
    "black-forest-labs/flux-3-image",
    "black-forest-labs/flux.2-pro",
    "openai/gpt-image-2",
    "google/gemini-3.1-flash-image",
]

STYLES = {
    "kids": (
        "Black and white coloring book page for young children. {subject}. "
        "Very bold, thick, uniform black outlines. Large simple shapes with big open areas that are "
        "easy to color. Cute, friendly style. Pure white background. No shading, no gray, no filled "
        "black areas, no text, no letters, no border. Every shape fully closed. Subject centered "
        "with a generous white margin."
    ),
    "adult": (
        "Black and white adult coloring book page. {subject}. Clean black line art with detailed "
        "patterns, uniform medium line weight, intricate but with clearly separated areas to color. "
        "Pure white background. No shading, no gray, no solid black fills, no text, no border. "
        "Every shape fully closed. Composition fills the page with a small white margin."
    ),
}


class GenError(Exception):
    pass


# ----------------------------------------------------------------------------- helpers
def base_url() -> str:
    return os.environ.get("OPENROUTER_BASE_URL", BASE_DEFAULT).rstrip("/")


def get_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit(
            "OPENROUTER_API_KEY is not set. Add it as an environment variable in the cloud "
            "environment's settings (never paste it into chat or commit it), then start a new session."
        )
    return key


def scrub(text: str, key: str | None) -> str:
    text = text[:300]
    return text.replace(key, "***") if key else text


def slugify(s: str, n: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n] or "page"


def read_subjects(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def build_prompt(subject: str, style: str, style_file: str | None, extra: str) -> str:
    template = Path(style_file).read_text(encoding="utf-8").strip() if style_file else STYLES[style]
    if "{subject}" not in template:
        raise SystemExit("style template must contain {subject}")
    prompt = template.replace("{subject}", subject)
    return f"{prompt} {extra}".strip() if extra else prompt


def ext_for(media_type: str | None, data: bytes) -> str:
    if media_type:
        mt = media_type.lower()
        if "svg" in mt:
            return ".svg"
        if "jpeg" in mt or "jpg" in mt:
            return ".jpg"
        if "webp" in mt:
            return ".webp"
        if "png" in mt:
            return ".png"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"RIFF":
        return ".webp"
    if data.lstrip()[:5] in (b"<?xml", b"<svg "):
        return ".svg"
    return ".png"


# ----------------------------------------------------------------------------- API
def post_image(sess, base, key, payload, retries=4, sleep=time.sleep) -> dict:
    """POST /images with retry on 429/5xx. Failed generations are not billed, so retrying is safe."""
    url = f"{base}/images"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(retries + 1):
        try:
            r = sess.post(url, headers=headers, json=payload, timeout=300)
        except requests.RequestException as e:
            if attempt == retries:
                raise GenError(f"network error: {e.__class__.__name__}") from None
            sleep(2 * 2**attempt)
            continue
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                raise GenError("response was not valid JSON") from None
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            ra = r.headers.get("Retry-After", "")
            delay = float(ra) if re.fullmatch(r"\d+(\.\d+)?", ra) else 2 * 2**attempt
            sleep(min(delay, 60))
            continue
        raise GenError(f"HTTP {r.status_code}: {scrub(r.text, key)}")
    raise GenError("retries exhausted")


def parse_result(resp: dict) -> tuple[bytes, str | None, float | None]:
    try:
        item = resp["data"][0]
        data = base64.b64decode(item["b64_json"])
    except (KeyError, IndexError, TypeError, ValueError):
        raise GenError("response had no image data") from None
    cost = (resp.get("usage") or {}).get("cost")
    return data, item.get("media_type"), float(cost) if cost is not None else None


def price_hint(pricing: list[dict]) -> str:
    out = []
    for p in pricing or []:
        if p.get("billable") != "output_image":
            continue
        unit, cost, var = p.get("unit"), p.get("cost_usd"), p.get("variant")
        label = {"image": "/image", "megapixel": "/megapixel", "token": "/token"}.get(unit, f"/{unit}")
        out.append(f"${cost:g}{label}" + (f" ({var})" if var else ""))
    return ", ".join(out) or "unknown"


def per_image_floor(pricing: list[dict]) -> float | None:
    vals = [p["cost_usd"] for p in pricing or [] if p.get("billable") == "output_image" and p.get("unit") == "image"]
    return min(vals) if vals else None


# ----------------------------------------------------------------------------- generate
class Budget:
    def __init__(self, budget: float | None, assumed: float, hint: float | None):
        self.budget = budget
        self.spent = 0.0
        self.inflight = 0
        self.reserve = hint or assumed
        self.lock = threading.Lock()

    def acquire(self) -> bool:
        with self.lock:
            if self.budget is not None and self.spent + (self.inflight + 1) * self.reserve > self.budget + 1e-9:
                return False
            self.inflight += 1
            return True

    def release(self, cost: float | None):
        with self.lock:
            self.inflight -= 1
            if cost is not None:
                self.spent += cost
                self.reserve = max(self.reserve, cost)


def run_generation(model, subjects, out_dir: Path, *, style, style_file, extra, aspect, quality,
                   resolution, variants, workers, budget, assumed_cost, max_images, hint,
                   dry_run, sess=None, key=None, base=None, sleep=time.sleep) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "ledger.jsonl"
    jobs = []
    for i, subj in enumerate(subjects, start=1):
        for v in range(1, variants + 1):
            stem = f"{i:02d}_{slugify(subj)}" + (f"_v{v}" if variants > 1 else "")
            if any((out_dir / f"{stem}{e}").exists() for e in (".png", ".jpg", ".webp", ".svg")):
                continue  # resume: already generated
            jobs.append((stem, subj))
    if max_images is not None:
        jobs = jobs[:max_images]

    summary = {"model": model, "planned": len(jobs), "done": 0, "failed": 0, "skipped_for_budget": 0,
               "spent_usd": 0.0, "files": [], "errors": []}
    if dry_run:
        est = f"~${hint * len(jobs):.2f}" if hint else "unknown (price is not per image)"
        print(f"[dry run] {len(jobs)} images with {model}; estimated cost {est}")
        for stem, subj in jobs[:3]:
            print(f"  e.g. {stem}: {build_prompt(subj, style, style_file, extra)[:110]}...")
        return summary

    bud = Budget(budget, assumed_cost, hint)
    lock = threading.Lock()

    def work(job):
        stem, subj = job
        if not bud.acquire():
            with lock:
                summary["skipped_for_budget"] += 1
            return
        cost = None
        try:
            payload = {"model": model, "prompt": build_prompt(subj, style, style_file, extra), "n": 1}
            if aspect:
                payload["aspect_ratio"] = aspect
            if quality:
                payload["quality"] = quality
            if resolution:
                payload["resolution"] = resolution
            resp = post_image(sess, base, key, payload, sleep=sleep)
            data, media_type, cost = parse_result(resp)
            path = out_dir / f"{stem}{ext_for(media_type, data)}"
            path.write_bytes(data)
            with lock:
                summary["done"] += 1
                summary["files"].append(path.name)
                with ledger_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": int(time.time()), "model": model, "file": path.name,
                                        "cost_usd": cost, "aspect_ratio": aspect, "quality": quality}) + "\n")
        except GenError as e:
            with lock:
                summary["failed"] += 1
                summary["errors"].append(f"{stem}: {e}")
        finally:
            bud.release(cost)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        list(ex.map(work, jobs))
    summary["spent_usd"] = round(bud.spent, 5)
    return summary


def print_summary(s: dict):
    print(f"{s['model']}: {s['done']} generated, {s['failed']} failed, "
          f"{s['skipped_for_budget']} not run (budget), spent ${s['spent_usd']:.3f}")
    for e in s["errors"][:5]:
        print(f"  ! {e}")
    if s["skipped_for_budget"]:
        print("  Budget reached. Re-run the same command to resume; finished images are skipped.")


# ----------------------------------------------------------------------------- bakeoff
def contact_sheet(files: list[Path], out: Path, cols=5, thumb=260):
    from PIL import Image

    ims = []
    for f in files:
        try:
            im = Image.open(f).convert("L")
            im.thumbnail((thumb, int(thumb * 1.3)))
            ims.append(im)
        except Exception:
            continue
    if not ims:
        return
    rows = -(-len(ims) // cols)
    cw, ch = thumb + 8, int(thumb * 1.3) + 8
    sheet = Image.new("L", (cols * cw, rows * ch), 200)
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * cw + 4, (i // cols) * ch + 4))
    sheet.save(out)


def analyse_dir(folder: Path) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_interior as bi

    files = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    rows = []
    for p in files:
        try:
            rows.append(bi.analyse_image(p))
        except Exception:
            continue
    n = len(rows)
    return {
        "images": n,
        "avg_gray_ratio": round(sum(r["gray_ratio"] for r in rows) / n, 4) if n else None,
        "avg_ink_ratio": round(sum(r["ink_ratio"] for r in rows) / n, 4) if n else None,
        "flagged": sum(1 for r in rows if [f for f in r["flags"] if "low resolution" not in f]),
        "files": files,
    }


def cmd_bakeoff(args) -> int:
    key = get_key()
    base = base_url()
    subjects = read_subjects(args.subjects)[: args.count]
    if not subjects:
        sys.exit("subjects file is empty")
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    sess = requests.Session()
    rows = []
    per_model_budget = args.budget / len(models) if args.budget else None
    for m in models:
        hint = None
        try:
            ep = sess.get(f"{base}/images/models/{m}/endpoints", timeout=30).json().get("endpoints", [])
            floors = [per_image_floor(e.get("pricing")) for e in ep]
            floors = [f for f in floors if f]
            hint = min(floors) if floors else None
        except Exception:
            pass
        out = args.out / m.replace("/", "_")
        s = run_generation(m, subjects, out, style=args.style, style_file=None, extra="", aspect=args.aspect,
                           quality=args.quality, resolution=None, variants=1, workers=args.workers,
                           budget=per_model_budget, assumed_cost=DEFAULT_ASSUMED_COST, max_images=None,
                           hint=hint, dry_run=False, sess=sess, key=key, base=base)
        print_summary(s)
        a = analyse_dir(out)
        contact_sheet(a.pop("files"), args.out / f"contact_{m.replace('/', '_')}.png")
        rows.append({"model": m, **s, **a})
    lines = ["| model | images | spent | $/image | avg gray | avg ink | flagged |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        per = f"${r['spent_usd'] / r['done']:.3f}" if r["done"] else "-"
        lines.append(f"| {r['model']} | {r['done']}/{len(subjects)} | ${r['spent_usd']:.3f} | {per} | "
                     f"{r['avg_gray_ratio']} | {r['avg_ink_ratio']} | {r['flagged']} |")
    report = "\n".join(lines)
    (args.out / "bakeoff_report.md").write_text(report + "\n")
    print("\n" + report)
    print(f"\nContact sheets: {args.out}/contact_*.png. Open them and judge line quality yourself; "
          "gray/ink numbers only catch mechanical problems.")
    return 0


# ----------------------------------------------------------------------------- commands
def cmd_models(args) -> int:
    base = base_url()
    sess = requests.Session()
    ids = args.ids or CANDIDATE_MODELS
    print(f"{'model':40s} price (output image)")
    for m in ids:
        try:
            r = sess.get(f"{base}/images/models/{m}/endpoints", timeout=30)
            if r.status_code != 200:
                print(f"{m:40s} HTTP {r.status_code}")
                continue
            eps = r.json().get("endpoints", [])
            print(f"{m:40s} " + " | ".join(price_hint(e.get("pricing")) for e in eps[:2]))
        except requests.RequestException as e:
            print(f"{m:40s} error: {e.__class__.__name__}")
    print("\nPer-token and per-megapixel prices vary with image size/quality; real cost is recorded per request.")
    return 0


def cmd_generate(args) -> int:
    subjects = read_subjects(args.subjects)
    if not subjects:
        sys.exit("subjects file is empty")
    key = None if args.dry_run else get_key()
    base = base_url()
    sess = requests.Session()
    hint = None
    if not args.dry_run or args.hint_price:
        try:
            ep = sess.get(f"{base}/images/models/{args.model}/endpoints", timeout=30).json().get("endpoints", [])
            floors = [f for f in (per_image_floor(e.get("pricing")) for e in ep) if f]
            hint = min(floors) if floors else None
        except Exception:
            pass
    s = run_generation(args.model, subjects, args.out, style=args.style, style_file=args.style_file,
                       extra=args.extra, aspect=args.aspect, quality=args.quality, resolution=args.resolution,
                       variants=args.variants, workers=args.workers, budget=args.budget,
                       assumed_cost=args.assumed_cost, max_images=args.max_images, hint=hint,
                       dry_run=args.dry_run, sess=sess, key=key, base=base)
    if not args.dry_run:
        print_summary(s)
        print(f"Next: python3 scripts/build_interior.py qa {args.out}")
    return 1 if s["failed"] and not s["done"] else 0


def make_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("models", help="show per-image prices")
    m.add_argument("ids", nargs="*", help="model slugs (default: shortlist)")
    m.set_defaults(func=cmd_models)

    g = sub.add_parser("generate", help="generate images from a subjects file")
    g.add_argument("subjects", type=Path)
    g.add_argument("-o", "--out", type=Path, required=True)
    g.add_argument("--model", required=True)
    g.add_argument("--style", choices=sorted(STYLES), default="kids")
    g.add_argument("--style-file", help="custom prompt template containing {subject}")
    g.add_argument("--extra", default="", help="text appended to every prompt")
    g.add_argument("--aspect", default="3:4", help="aspect ratio (default 3:4, closest to 8.5x11)")
    g.add_argument("--quality", choices=["auto", "low", "medium", "high"])
    g.add_argument("--resolution")
    g.add_argument("--variants", type=int, default=1, help="images per subject, to pick the best")
    g.add_argument("--workers", type=int, default=3)
    g.add_argument("--budget", type=float, help="stop before spending more than this many USD")
    g.add_argument("--assumed-cost", type=float, default=DEFAULT_ASSUMED_COST,
                   help="per-image reservation until the real cost is known")
    g.add_argument("--max-images", type=int)
    g.add_argument("--dry-run", action="store_true", help="show the plan; no key, no spending")
    g.add_argument("--hint-price", action="store_true", help="with --dry-run, look up the model price")
    g.set_defaults(func=cmd_generate)

    b = sub.add_parser("bakeoff", help="compare models on the same subjects")
    b.add_argument("subjects", type=Path)
    b.add_argument("--models", required=True, help="comma-separated slugs")
    b.add_argument("-o", "--out", type=Path, required=True)
    b.add_argument("--count", type=int, default=5)
    b.add_argument("--style", choices=sorted(STYLES), default="kids")
    b.add_argument("--aspect", default="3:4")
    b.add_argument("--quality", choices=["auto", "low", "medium", "high"])
    b.add_argument("--workers", type=int, default=3)
    b.add_argument("--budget", type=float, default=3.0, help="total USD across all models (default 3)")
    b.set_defaults(func=cmd_bakeoff)
    return p


def main(argv=None) -> int:
    args = make_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
