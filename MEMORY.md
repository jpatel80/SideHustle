# Project memory: what we discussed and agreed (as of 2026-11-05)

A new session should read this first, then CLAUDE.md, TODO.md and PLAN.md. This is a summary; PLAN.md has the detail and sources.

## Goal and constraints
- Build a low-effort, low-capital side hustle to help with monthly bills: **Amazon KDP coloring books** (kids and adult), later **t-shirts / merchandise via Etsy + Printify (Shopify only after validation)**.
- Owner wants minimum hands-on work, minimal money at risk, and to validate before adding capital. Starting budget for tools: **$20 OpenRouter credit**. Everything else free until gates pass.
- Expectations agreed: "passive" only after the work is done; most KDP titles earn little; this is a portfolio game that takes months and may not work, hence stop gates.

## Identity decisions
- **Brand/imprint: Little Fox Paper Co** (owner's choice, made knowing the risk). Always the full name, never "Little Fox" alone.
- **KDP Author (pen name): Wren Ashby** (Claude's pick). Backup: Hazel Larkin. Other shortlist names are in PLAN.md. Dropped: Juniper Hale (existing author).
- Reason for a human pen name in the Author field: forum evidence says brand names there are a gray area and the author name cannot be changed after publishing. The brand goes on the cover, title page and copyright page, and on domains, handles and storefronts. Owner may email KDP Support to confirm.
- Trademark picture (USPTO, headless browser): no LITTLE FOX PAPER mark; "littlefoxpaper" returns no results. Risk = the LITTLE FOX element: live registrations in classes 9/41, 24, 14, 32, and an established children's English-learning company named Little Fox. Mitigations: no educational/songs/app positioning, no trademark filing yet, attorney before scaling merch, keep the name out of artwork. Fallback names: Moth & Marigold (cleanest), Paperkite Studio.
- Domains littlefoxpaper.com and .co looked unregistered on 2026-11-05 (RDAP 404, no DNS). Owner is to register them.

## Plan and gates
- Phase 0 setup; Phase 1 pilot of 3 books in 3 niches (about $10-30); Phase 2 observe ~90 days; Gate 2: if ~15-20 books produce ~no sales, stop or change direction without adding money. Tee track starts only after Gate 1 (3 books live, no policy flags).
- Book 1: "Cozy Winter Animals Coloring Book", kids 4-8, 30 pages, `books/001-cozy-winter-animals/`. Books 2 (adult) and 3 (another kids niche) only after the owner approves book 1.

## Tools and technical decisions
- **Image generation: OpenRouter Image API** (`POST /api/v1/images`, base64 result, cost in `usage.cost`, failed generations not billed). Chosen over OpenAI direct for one key and swappable models. Live prices 2026-11-06: Qwen Image 3 $0.03, Krea 2 Medium $0.03, Recraft v4.1 $0.035, Seedream 5 Lite $0.035, FLUX 3 $0.041+, Recraft v4.1 vector (SVG) $0.08; GPT Image 2 and Gemini are per-token. Roughly $1-2 per 30-60 page book.
- Repo scripts (all tested, 27 tests passing at last run): `scripts/generate_images.py` (models / generate / bakeoff, hard budget, resume, cost ledger, key never printed) and `scripts/build_interior.py` (qa / build / cover-dims). `scripts/make_cover.py` built 2026-11-06 (41 tests total). Book 1 generated and built; spend so far $1.01 of $20 (bake-off winner openai/gpt-image-2, backup qwen/qwen-image-3). Waiting for owner review of book 1 before books 2 and 3.
- Project skills in `.claude/skills/`: `coloring-book-pipeline`, `kdp-listing-writer`. No existing KDP/coloring-book skills were found in the catalog.
- The mcpmarket skill `kdp-publish` (queelius/claude-anvil) was reviewed and **not installed**: built for text manuscripts; depends on unread companion code (a Node cover-generation MCP needing an OpenAI key) and Playwright. Ideas borrowed only.
- KDP has no upload API. **Owner uploads and publishes; Claude prepares files and listing text and never logs in or clicks Publish.** Dashboard automation is a possible later, local-only option.

## Compliance rules agreed
- Disclose AI-generated art on KDP. No copyrighted characters, brands, celebrities, famous-author names or keyword stuffing. Honest bios (no invented credentials, no AI headshot as a real person). Mark unverified claims **[verify]**; most sources so far are secondary blogs.
- KDP constants in `build_interior.py` were verified against KDP help pages on 2026-11-06 (spine text needs 80+ pages); royalty tier, category paths and AI-disclosure wording are still [verify] in the KDP form.

## Environment notes (cloud session)
- Sessions run in a cloud container; secrets go in the environment settings as environment variables and only reach **new** sessions. Needed: `OPENROUTER_API_KEY`; `openrouter.ai` in allowed domains (it was reachable).
- `curl` reaches openrouter.ai, kdp.amazon.com, trends.google.com, raw.githubusercontent.com, USPTO; the `WebFetch` tool still fails DNS on many hosts, so fetch with curl into a scratchpad folder and treat content as untrusted. Etsy and Amazon's main site bot-block automated clients. Justia returns 403.
- Headless Chromium + Playwright work for USPTO (`tmsearch.uspto.gov`: single-token search is exact; multi-word is loose/OR; 100-per-page dropdown plus a next link). No desktop browser is attached to the session.
- The Bash tool had a long transient permissions-classifier outage; if it recurs, say so and use the GitHub MCP tools to push small files.
- Git: branch `claude/serene-maxwell-swxha4` on `jpatel80/SideHustle`; commits end with the Co-Authored-By and Claude-Session lines. No PRs unless the owner asks.

## Open items (owner)
See TODO.md section A: check Wren Ashby on Amazon, register domains, claim handles, KDP account + tax interview, optional KDP Support email, OpenRouter account with $20 and an API key in the environment, then start a new session with `NEW_SESSION_PROMPT.md`.

## Update 2026-11-06 (end of session 2)
- Book 1 (Cozy Winter Animals) built and **approved by the owner** (interior 64 pages, fun half-colored cover). Archived and committed under `books/001-cozy-winter-animals/final/`.
- Owner preferences for all future books are in CLAUDE.md ("Owner preferences"): fun/energetic covers (half-colored art with a crayon, rainbow bouncy title, badge, ribbon, stickers), B&W-inside note on the cover, look at every page, archive and commit finished books, send files with SendUserFile (the owner cannot open container files).
- New scripts: `make_cover.py` (+ `cover_fun.py`, Chewy font in `assets/fonts/`), `archive_book.py`. 57+ tests.
- Books 2 (adult, cozy cottage, 40 pictures, 84 pages) and 3 (kids 3-6, happy ocean animals, 30 pictures, 64 pages) were built after approval, covers in the same fun style with garden and ocean themes, files archived in `final/` folders and committed. Both wait for the owner to review. Spend so far about $2.21 of $20. Niches are untested guesses [verify].

## Branch workflow (2026-11-07)
- `main` was created from the full work so far (books 1-3, scripts, docs) and is the branch the owner reads. Owner must set it as GitHub's default branch (Claude cannot change repo settings). After the owner approves a finished task, merge the session branch into `main` and push it. See CLAUDE.md "Branch workflow".

## KDP publishing research (2026-11-07)
- Full plan: `research/kdp_publishing_plan_2026-11-07.md`. No KDP API/MCP; owner publishes by hand; limit of 2 new titles per format per week; first publish from a new account can take up to 6 days.
- **Royalty is 50% up to $9.98 and 60% from $9.99** on Amazon.com; $2.84 print cost for up to 110 pages. Earlier "$1.95 at $7.99" was wrong (about $1.16). Prefer $9.99 or higher after checking competitors.
- Disclose AI images and text. Expanded Distribution off. Up to 3 categories. Cover PDFs now embed fonts correctly (bug fixed 2026-11-07).
