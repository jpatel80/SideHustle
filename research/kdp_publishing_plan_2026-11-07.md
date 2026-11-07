# How to publish our books on Amazon KDP: researched plan (2026-11-07)

Method: I read about 60 official KDP help pages (fetched with curl on 2026-11-06/07 and treated as untrusted text), Amazon's Conditions of Use, and searched the web for how authors work in practice. **Official** = a KDP/Amazon page. **Secondary** = blogs, vendor sites and forum summaries (useful, not authoritative). Anything I could not confirm is marked **[verify]**. Sources are listed at the end.

## 0. Bottom line

1. **There is no KDP API, and no MCP server or CLI that publishes to KDP.** The only "Kindle" MCP servers I found send personal documents to a Kindle device. The only automation route is a bot or browser script driving the KDP website.
2. **I recommend against bots, including browser agents.** Amazon's Conditions of Use (which KDP's terms incorporate) say the license "does not include ... any use of data mining, robots, or similar data gathering and extraction tools", KDP can suspend or terminate an account "at any time if we have concerns with your account, or activity relating to your account", and you may hold only one KDP account. The time saved is about 10 minutes per book, against an account that holds your royalties. So: **you do the uploads by hand (about 15 minutes per book); Claude automates everything around that** (files, checks, listing text, tracking).
3. **KDP limits new titles to 2 per format per week** (official). Three paperbacks therefore take two weeks.
4. **A price correction that matters:** on Amazon.com the royalty is **50% up to $9.98 and 60% from $9.99**. My earlier listings assumed 60% at $7.99. Real royalty at $7.99 is about **$1.16**, at $9.99 about **$3.15**. I have fixed the three listings (see section 6).
5. **Disclose AI honestly, including text.** KDP's rule covers AI-generated images (cover and interior) and text, even if you edited the output afterwards.
6. **Cost to publish: $0** (free KDP ISBN). Optional: a proof copy costs the print cost ($2.84) plus shipping.
7. **First publish from a new account may take up to 6 days** (official), then 3 business days for later titles.

## 1. What is automated, and what only you can do

| Step | Who | How |
|---|---|---|
| Artwork, interior PDF, cover PDF, listing text, archive in git | Claude | Done (repo scripts) |
| Checking files against KDP's rules before upload | Claude | Done by hand for this plan (section 5); a one-command check can be built |
| A paste-ready "upload sheet" with a Copy button per field | Claude | **Offer:** I can build it as a page you open next to the KDP tab (no bot, no automation of Amazon) |
| Watching for KDP review emails (accepted, rejected, "In Review") | Claude, **only if you allow it** | Your Gmail is connected to this environment; I would only search for KDP/Amazon mails you approve |
| Weekly reminders (title-limit reset, "check your bookshelf") | Claude | Scheduled tasks from this session |
| Sales tracking and the Gate 2 decision | Claude | You download the report from kdpreports.amazon.com and give it to me (no API exists) |
| Create/sign in to KDP, identity check, tax interview, bank details | **You** | Needs your ID, tax number, bank |
| Creating titles, uploading files, answering the AI question, accepting terms, **Publish** | **You** | Browser, logged in as you |
| Ordering a proof copy, Author Central, ads account | **You** | Browser |

Claude does not log in to KDP and never presses Publish (project rule).

## 2. The calendar

KDP counts new titles per format, creation and submission separately, resetting **Sunday 00:00 UTC** (that is Saturday 7 pm US Eastern / 4 pm Pacific in winter time). Official.

| When | What |
|---|---|
| **Day 0** (about 1 hour) | Part A below: account, identity, tax, bank |
| **Week 1** | Create **book 1** and **book 2** (uses the 2 slots). Order a proof of book 2 (the weakest on fine detail) and optionally book 1. Submit **book 1**. |
| **Week 1-2** | Proofs arrive (secondary: roughly 1-2 weeks including the review wait). Check print quality of book 2. |
| **Week 2** | Fix and submit **book 2** after its proof. Create and submit **book 3** (after you have reviewed it). |
| **Within 72 hours of each book going live** | Last chance to fix title, subtitle or author name (official). Check the live page. |
| **Days 7-14 after launch** | Back cover shows on the page after 7-10 business days; "Look Inside" after 9-10 business days (official). |
| **About day 90** | Gate 2 review (see PLAN.md) |

If you skip proofs, submit books 1 and 3 in week 1 and book 2 in week 2.

## 3. Step by step

### Part A. One-time account setup (you, about 1 hour)

1. **Amazon login.** Go to kdp.amazon.com and sign in with an Amazon account, or create one ("Sign up", "Create your KDP account"). Use a strong password.
2. **Two-step verification.** Turn it on (required later for bank changes).
3. **Account details.** Business type: *Individual*. Enter your **legal first and last name, not the pen name** ("Don't enter your pen name"), and a valid mailing address (tax and royalties). KDP issues payments and tax forms under this name.
4. **Identity verification, if the banner appears.** A passport or driver's license; the name and country must match the account. Use a phone for the photos.
5. **Tax interview** (KDP "Tax Information"). *US person:* W-9 with your SSN or EIN. *Non-US person:* W-8BEN; without a US tax number and a treaty claim, **30% withholding** applies to US-source royalties. **I need to know your country of residence to be more specific.**
6. **Bank account.** "Getting Paid" > add a bank account (direct deposit; the account holder name must match your bank records). Direct deposit has no minimum; wires and checks need $100. Royalties arrive about **60 days after the end of the month of sale**.
7. **Pen name.** Nothing to do in the account. The pen name goes in each book's Author field (official: "You can use a pen name or pseudonym"; KDP may later ask for proof of rights, and your real name stays out of public pages).
8. **Optional now:** Author Central can only be set up once a book is live (Part C).

### Part B. For each book (you, about 15 minutes; values come from `books/NNN-slug/listing.md`)

1. **Bookshelf > + Create > Paperback.**
2. **Details page:** language English; title and subtitle exactly as on the cover (no HTML, nothing promotional, 200 characters max together); author **Wren Ashby** as first name / last name; no contributors; description (HTML allowed, no URLs, no review requests); publishing rights "I own the copyright..."; **Sexually explicit images or title: No**; **reading age** (kids' books: 4-8 and 3-6; needed for children's categories); **primary marketplace Amazon.com**; **up to 3 categories**; **up to 7 keywords**. Save and continue.
3. **Content page:** *Print ISBN:* get the **free KDP ISBN** (imprint then shows as "Independently published"); leave publication date blank; *Print options:* **Black & white interior, white paper, 8.5 x 11 in, No bleed**, cover finish matte or glossy; upload `interior.pdf`, then upload `cover.pdf` ("Upload a cover you already have"); **answer the AI question** (images: yes; text: yes, see section 6); click **Launch Previewer** and page through the whole book; fix anything it flags.
4. **Rights & pricing page:** territories "All territories"; price (section 4); **leave Expanded Distribution off**; optionally **order a proof copy** here; accept the terms.
5. **Press "Publish Your Paperback Book"** (you only). Status goes Draft > In Review > Publishing > Live. You cannot edit while In Review; reviews cannot be rushed.
6. **After Live:** check the page; within the 72-hour window fix any title/subtitle/author typo. After that those fields and trim size, ISBN and imprint are locked; description, keywords, categories, reading age and price stay editable.

### Part C. After a book is live (you, small tasks)

- **Author Central** (KDP "Marketing" > Author Central > Manage author page): claim the "Wren Ashby" page with one live book; add an honest bio (no invented credentials, no AI headshot passed off as a real person).
- **Reports:** kdpreports.amazon.com for orders and royalties. Download the monthly file and give it to me for tracking.
- **Do not run ads yet.** See section 4.

## 4. Money, with corrected numbers (Amazon.com, 24-110 pages, black ink)

Print cost is a flat **$2.84**. Royalty = rate x list price - $2.84; minimum list price **$5.68**.

| List price | Rate | Royalty | Break-even ad cost of sale (royalty / price) |
|---|---|---|---|
| $7.99 | 50% | $1.16 | about 14% |
| $9.98 | 50% | $2.15 | about 22% |
| **$9.99** | **60%** | **$3.15** | **about 32%** |
| $10.99 | 60% | $3.75 | about 34% |
| $12.99 | 60% | $4.95 | about 38% |

(Table is my arithmetic from official KDP numbers.) What this means:

- **$9.99 earns $1.00 more per copy than $9.98**, and 2.7 times what $7.99 earns. Unless competitors are much cheaper, $9.99 or above is the better starting price. I cannot see Amazon prices from here: look at 5-10 similar titles in your browser.
- **Ads are probably not worth it at first.** Secondary sources suggest $5-10 a day and $0.30-0.80 per click, with beginners often above break-even cost. At $7.99 an ad is profitable only if under about 14% of sales go to ad cost. Wait for Gate 2 data before spending.
- **Scale check:** 100 copies a month at $3.15 is $315 a month. Reaching that needs real ranking and reviews, and many coloring titles sell far less. The stop gates stand.

## 5. Our files against KDP's rules (inspected 2026-11-07)

| KDP requirement (official) | Status |
|---|---|
| Interior PDF, uniform page size, even page count, at least 24 pages | **OK:** 64 / 84 / 64 pages, all 8.5 x 11 in |
| Fonts embedded | Interiors **OK**. **Covers were not:** an unused, unembedded Helvetica was declared. **Fixed today**; all three covers rebuilt (images identical) |
| Images at least 300 DPI, flattened, no transparency | **OK** technically (embedded at 300 ppi, grayscale). Source art is 1152 x 1536 px upscaled, so lines are slightly soft; see book 2 caveat |
| Margins: outer at least 0.25 in, inside at least 0.375 in for up to 150 pages | **OK** (builder keeps art inside the safe box) |
| Cover = bleed + back + spine + front + bleed; content at least 0.25 in from the edge; title on the front; barcode area clear | **OK**; text kept 0.4 in in; barcode box left blank white (KDP places the barcode) |
| No crop marks, comments, annotations, watermarks | **OK** |
| Title/subtitle/author on the cover and in the interior must match what you enter in the form | **OK** (copy exactly from `listing.md`) |
| Spine text only above 79 pages | Book 2 (84 pages) qualifies but its 0.19 in spine would carry about 4 pt type, so the spine is **left blank** |
| "Excessive blank pages" is a listed cause of file trouble (no number given) | **Risk, low-moderate.** About 53% of each interior is blank (blank backs). Single-sided with blank backs is the standard way to make coloring books (secondary), and I found no report of rejection for it. If KDP flags it, fallback: put a light test-color page or simple decoration on the backs |

Book 2 caveat: busy textures (cushions, bushes, fabric) turn crackly up close. Order a proof before relying on it.

## 6. Corrections I made to earlier documents

- **Royalty rate** (listings, README): fixed to 50% up to $9.98, 60% from $9.99. Earlier text said $1.95 at $7.99; correct is about $1.16.
- **Categories:** KDP allows **3**, not 2.
- **Expanded Distribution:** off (coloring books are on KDP's list of content distributors do not accept).
- **AI disclosure:** text must be disclosed too. The titles, descriptions and cover blurbs were drafted with Claude's help, so the honest answer is "AI-generated" for text as well as images. Your decision, but under-disclosing is the stated risk.
- **Pen name:** KDP's own page confirms pen names are allowed. Your earlier optional step "email KDP Support about brand names" is not needed: official text says anything in the Author field that is not part of an author name may be rejected, which is why the brand stays on the cover and copyright page only.
- **Keywords:** KDP recommends **2-3 word phrases**, no repeats of title or category words, no "book"-type generic words. Several of my keywords are longer; I propose a trimmed set (below) but have not applied it.

Proposed keywords (not applied yet): *book 1:* "preschool animal pictures", "thick outline coloring", "quiet time activity", "stocking stuffer", "polar bear snowman", "easy coloring pages", "kids gift". *Book 3:* "toddler sea animals", "thick line pictures", "easy coloring pages", "quiet time activity", "beach gift", "whale octopus turtle", "crayon friendly". *Book 2:* "cottagecore", "garden flowers", "tea time", "gel pen friendly", "cat and rabbit", "quiet evening hobby", "gift for gardeners".

## 7. Risks and how we handle them

| Risk | Handling |
|---|---|
| **Account suspension** (KDP can act on "concerns with your account"; secondary reports of automated terminations in 2026, mostly unverified) | One account only; no bots or scrapers; real accurate details; steady pace (2 new titles a week at most); distinct books, no near-duplicates; honest AI disclosure |
| **Content review** | Full AI disclosure; no brands or characters; description matches the book (B&W inside is stated); cover is original |
| **Print quality** | Proof copy for book 2 first |
| **Copyright of AI art** (purely AI-generated images may not be protected in the US; **[verify]**; and KDP may ask for proof of rights) | Keep `final/ledger.jsonl`, the prompts in `subjects.txt` and the model name; your call on the rights tick. I did **not** research OpenAI's output terms: **[verify]** commercial use before publishing |
| **Taxes** | Depends on your country; see A5 |
| **Weak sales** | Stop gates in PLAN.md; no ad spend until data |

## 8. Decisions I need from you

1. **Country of residence** (tax form and withholding).
2. **Pen name:** keep *Wren Ashby* for all three, or a second name for the adult book? (Check it on Amazon first; web search found no existing author by that name or by "Hazel Larkin", which is not conclusive.)
3. **Which books go first.** I suggest: book 1 plus a proof of book 2 in week 1; book 3 after your review in week 2.
4. **AI text disclosure:** accept my conservative recommendation (disclose text too)?
5. **Prices:** $9.99 or higher, after you check competitors?
6. **Optional helpers to build:** the copy-button upload sheet, a one-command file check, Gmail watching, weekly reminders. Tell me which.

## 9. Not verified

- Exact wording and layout of the current KDP form (screens change); the form's AI question wording; exact category paths (the lists are inside the logged-in form and Amazon blocks my automated access).
- Competitor prices and demand for the three niches.
- Real review times for a first-ever publish: official page says up to 6 days; I have no first-hand data.
- OpenAI/OpenRouter terms for commercial use of generated images.
- Whether Amazon enforces its "robots" clause against assisted form-filling; I did not find a statement either way, which is why I recommend not doing it.

## Sources

**Official (fetched 2026-11-06/07):** [Create a Book](https://kdp.amazon.com/en_US/help/topic/G202172740) (weekly limits) · [Timelines](https://kdp.amazon.com/en_US/help/topic/G202173620) · [Book Status](https://kdp.amazon.com/en_US/help/topic/G200627450) · [Update book details](https://kdp.amazon.com/en_US/help/topic/G200736410) · [Titles & Editions](https://kdp.amazon.com/en_US/help/topic/GW7J4WEKBVU25YEC) · [Authors & Contributors](https://kdp.amazon.com/en_US/help/topic/G2BWJN2BY98T5PV2) · [Keywords](https://kdp.amazon.com/en_US/help/topic/G201298500) · [Metadata Guidelines](https://kdp.amazon.com/en_US/help/topic/G201097560) · [KDP Categories](https://kdp.amazon.com/en_US/help/topic/G200652170) · [Content Guidelines (AI)](https://kdp.amazon.com/en_US/help/topic/G200672390) · [ISBN and Imprint](https://kdp.amazon.com/en_US/help/topic/G201834170) · [Print options](https://kdp.amazon.com/en_US/help/topic/G201834180) · [Upload and Preview](https://kdp.amazon.com/en_US/help/topic/G200641240) · [Paperback Submission Guidelines](https://kdp.amazon.com/en_US/help/topic/G201857950) · [Create a Paperback Cover](https://kdp.amazon.com/en_US/help/topic/G201953020) · [Format Images](https://kdp.amazon.com/en_US/help/topic/G202169030) · [Trim, bleed, margins](https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6) · [Barcodes](https://kdp.amazon.com/en_US/help/topic/G5HDYGP4BXLX4RUW) · [Paperback Printing Cost](https://kdp.amazon.com/en_US/help/topic/G201834340) · [Paperback Royalty](https://kdp.amazon.com/en_US/help/topic/G201834330) · [When will I get paid](https://kdp.amazon.com/en_US/help/topic/GK2MKZUL6U3SFBPZ) · [Expanded Distribution](https://kdp.amazon.com/en_US/help/topic/GQTT4W3T5AYK7L45) · [Low-content books](https://kdp.amazon.com/en_US/help/topic/GGE5T76TWKA85DJM) · [Proof and author copies](https://kdp.amazon.com/en_US/help/topic/G7BBN68RYX5UMDZF) · [Create a KDP account](https://kdp.amazon.com/en_US/help/topic/G200620010) · [Verify your identity](https://kdp.amazon.com/en_US/help/topic/GH7TYHP6FR9QAUM9) · [Tax information](https://kdp.amazon.com/en_US/help/topic/G201723290) · [Author Central](https://kdp.amazon.com/en_US/help/topic/G200644310) · [Advertising for KDP books](https://kdp.amazon.com/en_US/help/topic/G201499010) · [KDP Reports](https://kdp.amazon.com/en_US/help/topic/GVTTXHKHVPAPBEDQ) · [KDP Terms and Conditions](https://kdp.amazon.com/en_US/terms-and-conditions) · [Amazon Conditions of Use (Amazon-hosted copy, updated Aug 14 2026)](https://digprjsurvey.amazon.com/csad/help/node/GLSBYFE9MGKKQXXM)

**Secondary (not authoritative):** web searches on KDP automation and terminations ([Kindlepreneur](https://kindlepreneur.com/amazon-account-suspension/), [Amz Sellers Attorney](https://www.amazonsellers.attorney/blog/increase-in-kdp-account-terminations-over-ai-assisted-books-and-poor-customer-experience-concerns)), AI-coloring-book rules ([Inkfluence](https://www.inkfluenceai.com/blog/sell-ai-coloring-books-on-kdp-2026), [KDP Builder](https://kdpbuilder.com/blog/kdp-ai-disclosure-rules)), blank backs ([BookCoversLab](https://bookcoverslab.com/de/blog/do-coloring-books-need-blank-backs)), review timing and title limits ([Vappingo](https://www.vappingo.com/word-blog/how-long-does-kdp-publishing-take/), [ebookpbook](https://ebookpbook.com/2026/10/09/kdp-weekly-title-limits)), Amazon Ads for authors ([Vappingo](https://www.vappingo.com/word-blog/amazon-ads-for-authors-beginners-guide/)).
