# SideHustle: Low-Capital Plan (KDP Coloring Books first, Print-on-Demand Tees second)

Written 2026-11-03. Goal: a low-effort income stream toward monthly bills, started with as little cash as possible and validated before any real money or time goes in.

**Evidence quality:** Most of the research below comes from SEO and vendor blogs, not Amazon, Etsy or Printify documentation. Anything marked **[verify]** needs checking on the official page before you rely on it. Figures labelled "my estimate" are my own arithmetic, not sourced.

---

## 1. Honest expectations (read first)

- **"Passive" is only true after the work is done.** Each book needs research, generation, quality checks, a cover and a listing. Claude can do most of it, but you stay in the loop for account setup, the final publish click and quality review.
- **Most titles earn close to nothing.** The category has 100,000+ active coloring titles. One source estimates $50-300/month per book for the ones that do sell. Top sellers are outliers.
- **Royalty per sale is small.** A source works out ~$2.32 on a $7.70 100-page kids' book. At that rate, $500/month is ~215 sales/month, about 7 a day (my estimate). So this is a portfolio game: many books in underserved sub-niches, not one hit.
- **Compounding is slow.** New listings have no reviews and no ranking. Expect months, not weeks, before you can tell whether a niche works.
- **Rough bills target (my estimate):** $300/month probably needs a portfolio of dozens of books, plus 6-12 months. It could take longer, and it may not work. That's why the plan has kill gates.

---

## 2. Skills and MCPs: what exists

**There are no ready-made skills for KDP, coloring books, Printify or Etsy** in the skill catalog (searches returned nothing). We build our own project skills (section 5). They're the best "skills" for this, because they encode your niche rules and QA standards.

### Already available to you
| What | Use |
|---|---|
| Claude's built-in `pdf`, `xlsx`, `docx` skills | Build/inspect interior PDFs, tracking spreadsheets |
| Connected: Gmail, Context7 | Gmail for KDP/Etsy notifications |

### Connectors in the registry (not installed yet)
| Connector | Use | Cost |
|---|---|---|
| **Shopify** (official) | Create/update products, read orders | Needs a Shopify plan, so defer |
| **Canva** | Covers, tee mockups, template autofill | Free tier exists **[verify limits]** |
| **Google Sheets / Drive** | Niche research log, sales tracker | Free |

### MCP servers found on the web (community-built, unaudited)
| Need | Option | Notes |
|---|---|---|
| Browser automation (KDP has **no upload API**) | **Playwright MCP** (Microsoft, official): `claude mcp add playwright npx @playwright/mcp@latest` | Fill KDP forms, read Amazon search pages. UI changes will break selectors |
| Trend research | Google Trends MCPs: `purahmanian/google-trends-mcp` (no key), `jain-eshan/google-trends-mcp` (Python/uv, has a `/trends` skill) | Google may rate-limit |
| Image generation | `merlinrabens/image-gen-mcp-server` (OpenAI, Stability, Leonardo, Ideogram) or `mcpimg` (Replicate, fal.ai, OpenRouter) | **Claude cannot natively produce raster images**, so we need an image model API |
| Printify | `TSavo/printify_mcp`, `kaylaeastman86-cyber/printify-mcp`, `Tunbi313/printify_mcp` | Printify only publishes through a connected store |
| Shopify (community) | `GeLi2001/shopify-mcp` | Alternative to the official connector |

**Security note:** a third-party MCP server receives your API keys. Before installing one, have Claude read its source, or skip the MCP and write a small script against the provider's REST API, which we control. For image generation I'd do the latter.

### Things we should not expect to automate
- **KDP upload.** No public API, so it's a browser-automation workaround. Plan on Claude pre-filling everything and you reviewing and clicking Publish. Automating logins also risks tripping Amazon's bot detection, so we keep a human in the loop.
- **Raw trend data.** There's no clean Amazon sales-data feed. BSR-based estimates are rough.

---

## 3. Pipeline design

```
1 Research -> 2 Niche brief -> 3 Generate art -> 4 QA + clean -> 5 Assemble PDF -> 6 Cover -> 7 Listing -> 8 Upload (human final click) -> 9 Track
```

1. **Research.** Google Trends MCP, Amazon search autocomplete and top-result pages via Playwright, and Pinterest/Etsy trend pages. Output: 10 candidate niches scored on demand, competition, and "can we make it distinctive". Log in a sheet.
2. **Niche brief.** One page: audience, theme, 30-40 page ideas, style rules, a list of banned things (trademarked characters, celebrity likenesses, brand names).
3. **Generate art.** Batch via an image API with a fixed style prompt. Roughly $0.04/image on OpenAI's API per one comparison, so a 40-page book is ~$1.60-$4 with rerolls **[verify current pricing]**.
4. **QA and clean.** Claude reviews every image for broken lines, stray text, shading, anatomy errors and near-duplicates. Pillow/OpenCV then thresholds to pure black-and-white and upscales to 300 DPI (8.5x11 = 2550x3300 px).
5. **Assemble PDF.** Python script (img2pdf or reportlab). KDP's bleed rule: full-bleed PDF = trim + 0.125" wide and 0.25" tall. The no-bleed option, which is common for line art, uses exact trim size. Add a title page and "this book belongs to" page. Margins depend on page count, so check the table. **[verify]**
6. **Cover.** Canva or a generated image composited with the KDP cover calculator template. Needs spine width from the page count.
7. **Listing.** Title, subtitle, 7 keyword slots, 2 categories, description, price. Claude drafts, you approve.
8. **Upload.** Playwright pre-fills; you review in KDP's previewer and press Publish. KDP review typically takes up to ~72 hours **[verify]**.
9. **Track.** Weekly sheet: impressions, units, royalties, BSR, and the kill/scale decision per niche.

### Compliance rules baked into every step
- **Disclose AI-generated art** in the KDP upload form. Secondary sources say disclosure doesn't hurt visibility or royalties, but that isn't confirmed by Amazon **[verify in KDP content guidelines]**. Not disclosing is the actual violation.
- **No copyrighted characters, celebrity likenesses or brand names.** Applies to prompts, titles and keywords.
- **No near-duplicate books.** Each title needs distinct art and distinct metadata. Reported to be policed more tightly **[verify]**.
- **Reported cap on new titles per week** (one source says two per format) **[verify]**. This also forces a sensible pace.

---

## 4. Plan, phases and gates

### Phase 0: Setup (week 1, ~$0)
**You (human-only steps):**
- [ ] Create a KDP account; complete the tax interview and bank details. Free.
- [ ] Create an image-gen account with a **spending cap** (~$10 prepaid) and give me the API key as an environment variable, never in the repo.
- [ ] Free accounts: Google Trends (no login), Canva free, Google Sheets.
- [ ] Decide: is this under your name, or do you want a pen name? (KDP lets you publish under a pen name.)

**Claude:**
- [ ] Install Playwright MCP + one Google Trends MCP (after reading source).
- [ ] Build the first project skills: `kdp-niche-research`, `coloring-book-builder`, `kdp-listing-writer`.
- [ ] Write the PDF assembly script and test it against KDP's previewer.

### Phase 1: Pilot, 3 books (weeks 2-4, target <$20)
- 3 books in 3 different sub-niches (e.g., one kids, one adult, one seasonal). Keep the mix wide so you learn which direction works.
- 30-40 interior pages each, simple designs that survive imperfect generation.
- **Optional:** order 1 proof copy (~a few dollars plus shipping) of the best book to check print quality. KDP's online previewer is free.
- No ads. No paid tools.
- **Gate 1:** all 3 books approved and live, no policy flags, you find the workflow tolerable. If KDP rejects for quality, fix the pipeline before scaling.

### Phase 2: Observe (weeks 4-12, ~$0)
- Publish ~1-2 new books/week in the best-looking niches, within KDP's caps.
- Track impressions, units, BSR weekly.
- **Gate 2 (~day 90):** do **any** of the books sell consistently? Suggested bar: at least one niche with repeat sales and a rising trend. If after ~15-20 books you have effectively zero sales, stop or change direction, and don't add money.

### Phase 3: Scale only if Gate 2 passes
- Double down on winning sub-niches: series, volume 2/3, variations.
- Consider ads on proven books only, small daily budget.
- Add puzzle/activity books generated by code, with no image-gen cost. (Secondary sources say non-AI algorithmic puzzles generally don't count as AI-generated content **[verify]**, but that market is also very crowded.)

### T-shirt track (start only after Gate 1, runs in parallel at small scale)
**Order of platforms (cheapest first):**
1. **Etsy + Printify free plan.** No monthly subscription; $0.20/listing + ~6.5% transaction + ~3% processing **[verify]**. Printify's free plan is fine for this; the sources say its Premium plan is ~$25/month, which we skip. Etsy has built-in search traffic, which a fresh Shopify store lacks.
2. **Amazon Merch on Demand.** Free, no inventory. Reported approval is only ~30-40%, new accounts start at 10 live designs, and AI-design scrutiny is reported but unconfirmed **[verify all]**. Worth applying for, with low odds.
3. **Shopify (+ Printify):** recommended **only after** a design has proven itself on Etsy. A Shopify plan is a monthly fee and you'd have to drive your own traffic.

**Claude's role:** trend research (Google Trends, Etsy/Pinterest trend pages), 15-20 text-based or simple-graphic designs, mockups, listing titles/tags/descriptions. Run text-heavy designs first, because image models are unreliable at lettering and text-based designs are cheaper to get right.

**Risks specific to tees:**
- **Trademark/IP is the biggest risk.** Trending phrases are often trademarked. Check USPTO TESS for every phrase before listing, and avoid brand, sports team and character references.
- Margins are thin (a base tee is reported at ~$7-9 plus ~$5.50 shipping). Price against that.
- **Gate T1 (~day 60):** 15 listings live, any sale at all? If none, learn from impressions/favorites; don't spend on ads.

---

## 5. Repository layout to build next

```
SideHustle/
  PLAN.md                  <- this file
  CLAUDE.md                <- project rules: compliance list, banned terms, spending caps
  .claude/skills/
    kdp-niche-research/
    coloring-book-builder/
    kdp-listing-writer/
    pod-design-brief/      <- tee track
  scripts/
    build_interior.py      <- images -> B&W 300dpi -> KDP-spec PDF
    qa_images.py
  books/<slug>/            <- brief.md, pages/, interior.pdf, cover, listing.md
  tracking/                <- sales + niche logs
```

---

## 6. Cost summary

| Item | Phase | Cost |
|---|---|---|
| KDP account, publishing, KDP ISBN | 0-1 | $0 (free KDP ISBN **[verify]**) |
| Image generation, 3 pilot books | 1 | ~$5-15 |
| Optional proof copy | 1 | a few dollars + shipping |
| Etsy (new shop) | T-track | $0.20 per listing; **a one-time new-seller setup fee (~$15) may apply [verify]** |
| Printify free plan | T-track | $0 |
| Ads, Shopify, Printify Premium | After gates only | $0 until validated |
| **Total to reach Gate 1** | | **roughly $10-30** (KDP track only; add Etsy fees if you start tees) |

Your Claude subscription is the main ongoing cost and is not counted above.

---

## 7. Sources (all secondary unless noted; verify against official pages)

- KDP help, trim size/bleed: <https://kdp.amazon.com/en_US/help/topic/G201857950> (official)
- AI disclosure and coloring-book rules: <https://kdpbuilder.com/blog/kdp-ai-disclosure-rules>, <https://www.inkfluenceai.com/blog/sell-ai-coloring-books-on-kdp-2026>
- Saturation and income: <https://www.inkfluenceai.com/blog/low-content-book-income-2026>
- KDP has no upload API: <https://theopsdesk.pages.dev/blog/kdp-publishing-automation-manuscript-to-listing.html>
- Etsy vs Shopify for POD: <https://printify.com/blog/shopify-vs-etsy/>
- Amazon Merch on Demand: <https://amzprep.com/amazon-merch-on-demand/>
- Printify MCP servers: <https://github.com/TSavo/printify_mcp>, <https://github.com/Tunbi313/printify_mcp>
- Shopify MCP: <https://github.com/geli2001/shopify-mcp>
- Google Trends MCP: <https://glama.ai/mcp/servers/jain-eshan/google-trends-mcp>
- Image-gen MCP: <https://lobehub.com/mcp/merlinrabens-image-gen-mcp>

---

## 8. Decisions log (2026-11-04)

- **GitHub access:** fixed; branch `claude/serene-maxwell-swxha4` is pushed.
- **Image generator (recommended, pending your account):** OpenAI API (`gpt-image-2`), $20 prepaid, auto-recharge off, monthly limit set. Alternative for lettering-heavy art (covers, tees): Ideogram API. Run a ~$1 bake-off on 20 prompts before the pilot. **[verify]** current pricing, commercial-use terms, and whether the account needs identity verification.
- **Pen name:** KDP account and tax info use the legal name; the pen name goes in each book's Author field. Choose it before the first publish, since changing it later is reportedly restricted **[verify]**. Name shortlist is in the chat thread; clear any final pick on Amazon, Etsy, USPTO and domains before publishing.
- **Network:** this cloud session cannot reach `kdp.amazon.com`, so Claude cannot pre-fill KDP forms from here. Plan for you to do the upload (about 10-15 min/book from files Claude prepares), or later run Claude Code locally with Playwright.
- **Secrets:** API keys go in the environment's settings as an environment variable (e.g. `OPENAI_API_KEY`), never in chat or the repo.

### Update 2026-11-05

- **Image generator: OpenRouter instead of OpenAI direct.** One key, one prepaid balance, swap models by changing a slug. Reported options: GPT Image 2 (token-priced; $0.006-$0.211 per image depending on quality), FLUX 3 Image (from ~$0.041), Meta Muse Image (~$0.01), Recraft v4.1 vector (SVG output, ~$0.08). **[verify]** live prices at openrouter.ai. Needs `openrouter.ai` in the environment's allowed domains and the key stored as `OPENROUTER_API_KEY`. The generator script is not written yet: I could not read OpenRouter's docs from this session and will not code against an unverified API shape.
- **PDF toolkit built:** `scripts/build_interior.py` (qa / build / cover-dims) with 13 passing tests. It caught and fixed one real bug: un-embedded Helvetica, which KDP rejects.
- **Top-3 names re-checked** (web search only; the trademark database was unreachable): Little Fox Paper Co (no direct conflicts found), Moth & Marigold (old MARIGOLD AND MOTH mark for jewelry/textiles, status unknown), Paperkite Studio (crowded "Paper Kite(s)" paper/stationery brands, Etsy shops and a band). All need a manual USPTO check.
- **mcpmarket skill:** page unreachable from this session; not installed. Do not install any third-party skill without reviewing its SKILL.md and scripts.

### Update 2026-11-06: network opened, generator built, skill reviewed

- **Network:** `curl` now reaches openrouter.ai, kdp.amazon.com, trends.google.com, raw.githubusercontent.com. The `WebFetch` tool still fails DNS on these hosts, so I fetch with `curl` into the scratchpad and read the result as untrusted data. Etsy and Amazon's main site block automated clients (403/202).
- **OPENROUTER_API_KEY is not yet visible to the session** (env changes apply to new sessions). Nothing has been spent.
- **OpenRouter Image API (verified from its docs):** `POST /api/v1/images` with `model`, `prompt`, `aspect_ratio`, `quality`, `n`; image returned as `data[0].b64_json`; cost in `usage.cost`; failed generations are not billed. Per-image prices (live, 2026-11-06): Recraft v4.1 $0.035, Qwen Image 3 $0.03, Krea 2 Medium $0.03, Seedream 5 Lite $0.035, FLUX 3 Image $0.041-0.048, Recraft v4.1 vector (SVG) $0.08; FLUX.2 Pro $0.03/megapixel; GPT Image 2 and Gemini image are per-token. A 60-image book is roughly $2 on a $0.03-0.035 model.
- **`scripts/generate_images.py`** (models / generate / bakeoff): hard `--budget`, resume, retries, per-request cost ledger, key never printed. 14 tests against a local fake server; 27 tests total pass. The real model list/price lookup was run against the live API. A paid generation has not been run yet.
- **mcpmarket skill `kdp-publish` (queelius/claude-anvil, 1 star): reviewed SKILL.md only, NOT installed.** It is a benign orchestration prompt, but built for text manuscripts (LaTeX/Markdown/Word/EPUB): manuscript audit, EPUB conversion, pre-orders, KDP Select and eBook royalty tiers, none of which apply to coloring books. It depends on companion commands and a `kdp-cover` MCP server (Node + OPENAI_API_KEY) that I did not read, plus Playwright to drive the KDP dashboard. Good ideas to copy: gated phases, a per-book config file, a pre-submission completeness check, filling forms but never clicking Publish. Decision: build our own `kdp-listing-writer` skill (blurb, 7 keywords, categories, age range) and a per-book `listing.md`, and treat dashboard automation as a later, local-only option.
- **Trademark check:** Justia returns 403 to automated clients; USPTO search still has to be done by you.

### Update 2026-11-05: USPTO check done (details in research/name_clearance_2026-11-05.md)

- I drove headless Chromium against tmsearch.uspto.gov from the cloud container (no desktop browser is attached to this session).
- **Ranking changed.** Moth & Marigold is now the cleanest (only dead MARIGOLD AND MOTH marks). Paperkite Studio is medium risk (live PAPER KITE marks in media/photography). Little Fox Paper Co dropped to last: live LITTLE FOX registrations in kids-adjacent classes (9/41, 24, 14) and an established kids English-learning brand of that name.

### Decision 2026-11-05: pen name / brand = **Little Fox Paper Co**

- Chosen by the owner after being shown the USPTO findings and the risk. Domains littlefoxpaper.com and littlefoxpaper.co reported available by the owner (not independently verified by me).
- **What the USPTO check showed:** no mark containing LITTLE FOX PAPER (nothing identical). The risk is the LITTLE FOX element: live registrations in classes 9/41, 24, 14, 32 and an established children's English-learning company called Little Fox. Clothing (class 25), games (28) and books (16) LITTLE FOX filings found were all dead.
- **Mitigations we adopt:**
  - Always use the full name "Little Fox Paper Co", never "Little Fox" alone, in titles, listings, store names and handles.
  - Avoid fox-only branding that imitates the Little Fox learning brand: no animated-story or English-learning/educational positioning, no songs/audio, no app-style content.
  - Do not file a trademark on the name until we have traction; revisit with an attorney before scaling merchandise (tees, class 25) or if any takedown or cease-and-desist arrives.
  - If a conflict ever appears, the fallback names are Moth & Marigold and Paperkite Studio. Keep books free of the brand name inside the artwork so a rename is cheap (author name is in the KDP Author field, copyright page and cover only).
- **Do now (owner):** register both domains, claim handles (Instagram, Pinterest, TikTok, Etsy shop name), and use `Little Fox Paper Co` as the KDP Author name for every book. Choose it before the first publish; changing the author name later is reportedly restricted.

### Update 2026-11-05: author-name rules and pen-name shortlist

- **Correction to earlier advice:** I said KDP seemed to accept a brand-style Author field. Evidence conflicts (a KDP community answer says brand/domain names are not allowed as author names, others point to brand-style bylines that exist; coloring books are reported to get blocked for author-name and title violations). Official KDP text could not be read from this environment. Treat a brand in the Author field as risky: the author name cannot be changed after publishing (per KDP help as quoted by guides).
- **Plan:** Author field = a human-sounding pen name. "Little Fox Paper Co" appears as the imprint on the cover, title page and copyright page, and as the domain, social handles and Etsy/tee storefront. A visible Publisher name reportedly needs your own ISBN (cost); with KDP's free ISBN the book shows "Independently published". Verify.
- **Free authoritative check:** ask KDP Support "Can I use a brand name as the author name?" before the first publish.
- **Pen-name shortlist (no existing author found by web search; verify on Amazon):** Wren Ashby, Hazel Larkin, Rowan Whitlow, Nora Brindle, Fern Calloway, Willa Fennimore, Maisie Thornwood, Odette Finch, Clover Hastings, Finley Penrose, Elsie Pemberton. Dropped: Juniper Hale (existing children's author). Top picks: Wren Ashby, Hazel Larkin.
- **Bio rule:** keep it honest; no invented credentials, no AI headshot presented as a real person.
- **Open:** one pen name or two (kids vs adult); owner to search the chosen name in Amazon Books/Kindle; dedicated exact-match USPTO search and domain lookup still to run.
