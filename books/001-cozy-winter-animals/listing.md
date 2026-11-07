# Book 1 listing: Cozy Winter Animals Coloring Book

Status: **FINAL DRAFT for owner review** (pages, interior, cover and page count exist). Fields follow the order of the KDP "Create paperback" form. Items marked **[verify]** are things I could not confirm from KDP's public help pages; check them in the form. You paste and publish; Claude never logs in to KDP.

## Files to upload (local, not in git)
- Interior: `books/001-cozy-winter-animals/interior.pdf`: 64 pages, 8.5 x 11 in, no bleed, fonts embedded, 2.7 MB
- Cover: `books/001-cozy-winter-animals/cover.pdf`: 17.3941 x 11.25 in (back + 0.1441 in spine + front, 0.125 in bleed), 5218 x 3375 px at 300 DPI. Previews: `cover.png`, `cover_guides.png` (guides show trim, spine and safe lines)
- The front shows the owl page half colored in, as an example of coloring, with a bouncy rainbow title, a "30 big pictures to color" badge and small fully colored stickers of other pages (polar bear, puppy, kitten on the front; hare and fox on the back). The interior is black and white only, and the back cover and the description both say so. Regenerate with: `python3 scripts/make_cover.py books/001-cozy-winter-animals/pages/01_*.png -o books/001-cozy-winter-animals/cover.pdf --title "Cozy Winter Animals Coloring Book" --subtitle "30 Bold and Easy Pictures for Kids Ages 4-8" --author "Wren Ashby" --imprint "Little Fox Paper Co" --pages 64 --colored-half --badge "30|BIG PICTURES|TO COLOR!" --stickers <pages 02, 10, 24, 21, 30> --blurb "..."` (`--style plain` gives the simple blue cover).
- Verify the cover in KDP's cover previewer; if KDP reports a different spine width, tell Claude and the cover is regenerated in seconds.

## Step 1: Paperback details
- **Language:** English
- **Book title:** Cozy Winter Animals Coloring Book
- **Subtitle:** 30 Bold and Easy Pictures for Kids Ages 4-8
- **Series:** none
- **Edition number:** leave blank
- **Author (First / Last):** Wren Ashby. Pen name only. If you tell me this name is taken, the fallback is Hazel Larkin and the interior and cover are rebuilt.
- **Contributors:** none. Do **not** put "Little Fox Paper Co" in the Author field.
- **Imprint** (printed on the cover, title page and copyright page only): Little Fox Paper Co. With KDP's free ISBN the book shows "Independently published" as publisher; a visible Publisher name reportedly needs your own ISBN **[verify]**.

### Description (paste into the description box; HTML is accepted)
```
Snuggle up with 30 cozy winter animals ready to be colored! Each page has one big, bold, simple picture, from a sleepy owl in a striped scarf and a polar bear cub with a snowman to penguins, bunnies, a puppy with a sled and a fox curled up in the snow. Everything is drawn with thick clean lines that are easy for little hands to color.<br><br>
<b>What's inside</b><br>
&bull; 30 one-sided coloring pages, with a blank page behind each picture<br>
&bull; Large, simple shapes with plenty of room to color<br>
&bull; Friendly winter animals, snowmen, cozy cabins and snowflakes<br>
&bull; A "This book belongs to" page<br>
&bull; Large 8.5 x 11 inch pages<br><br>
Great for crayons, colored pencils and washable markers. A fun quiet-time activity and an easy gift for kids who love animals and snowy days.<br><br>
The inside pages are printed in black and white, ready for you to color. The colors on the cover are just an example.<br><br>
The illustrations in this book were created with AI image tools and were selected and arranged by the publisher, Little Fox Paper Co.
```
(about 1,100 characters; KDP's limit is 4,000 **[verify]**)

- **Publishing rights:** "I own the copyright and I hold necessary publishing rights." See owner decision 2 below before ticking this.
- **Primary audience, sexually explicit content:** No
- **Reading age:** minimum 4, maximum 8 **[verify field names and whether the range is optional]**

### Keywords (7 slots)
1. big simple pictures for preschool kids
2. thick outline animal pages for children
3. quiet time activity for ages 4 to 8
4. easy coloring pages for little hands
5. winter holiday gift for kids who love animals
6. snowman penguin owl bear pictures to color
7. stocking stuffer activity book for children

Slot limits (about 50 characters each) **[verify]**. No brand names, no famous names, no "best" or "#1" claims. The title words are already indexed by the title, so the slots add different phrases.

### Categories (up to three)
KDP lets you pick **up to 3 categories**, from a list based on your primary audience and primary marketplace, and says wrong categories can be changed by KDP. Closest fit: a children's coloring-book category (for example Children's Books > Activities, Crafts & Games > Coloring Books) and an animals-for-kids category. **[verify]** The category menu paths change; pick the nearest children's options in the form and do not pick adult coloring.

## Step 2: Paperback content
- **Print ISBN:** use the free KDP ISBN. KDP's help says coloring books are *not generally* "low-content", so the free ISBN should be offered **[verify in form]**.
- **Publication date:** leave blank (publish now).
- **Manuscript:** upload `interior.pdf`. **Bleed setting: No bleed.** Trim size: 8.5 x 11 in.
- **Interior and paper:** Black & white interior, **white** paper (the spine width in the cover assumes white paper; if you pick cream, tell Claude and the cover is rebuilt with the cream spine width).
- **Cover finish:** matte or glossy is your choice; matte is a common pick for kids' coloring books (opinion, not a KDP rule).
- **Cover:** "Upload a cover you already have (print-ready PDF)" and upload `cover.pdf`. The back cover has a blank white area where KDP can place its barcode (do not upload your own barcode).
- **Generative AI content question:** answer **Yes**. The images are **AI-generated** (not just AI-assisted): generated with OpenAI's GPT Image 2 through OpenRouter, then selected, cropped and converted to black and white by us. Describe the tool as "GPT Image 2 (OpenAI) via OpenRouter" if the form asks **[verify what the form asks]**. The book contains no AI-generated text other than the title, copyright and "belongs to" pages that we wrote. If you are unsure about the listing text, which was drafted with Claude's help, disclose rather than skip **[verify whether KDP's question covers store-page text]**.
- **Also disclose the text.** KDP defines AI-generated as content an AI tool created, even if you edit it afterwards; AI-assisted (no disclosure needed) means you wrote it yourself and only used AI to polish. The title, subtitle, description, back-cover blurb and the title/copyright-page wording were drafted with Claude's help, so the conservative, honest answer is to tick **text** as AI-generated too. Under-disclosing is the risk KDP warns about; over-disclosing has no stated penalty. (KDP Content Guidelines, fetched 2026-11-07; **[verify]** the exact wording in the form.)
- **Previewer:** open KDP's online previewer and page through the whole book. Check margins and that no picture touches the page edge.

## Step 3: Pricing
- **Printing cost (Amazon.com, B&W, 8.5 x 11, 24-110 pages):** a flat **$2.84 per book** (KDP "Paperback Printing Cost" page, fetched 2026-11-07; the calculator in the form is the final word).
- **Royalty rate depends on the list price (Amazon.com):** **50% up to $9.98, 60% from $9.99** (KDP "Paperback Royalty" page, fetched 2026-11-07). Royalty = rate x list price - $2.84.
- **Minimum list price:** $2.84 / 0.50 = **$5.68** (KDP will not accept less).

  | List price | Rate | Royalty per sale (about) |
  |---|---|---|
  | $6.99 | 50% | $0.66 |
  | $7.99 | 50% | $1.16 |
  | $8.99 | 50% | $1.66 |
  | $9.98 | 50% | $2.15 |
  | **$9.99** | **60%** | **$3.15** |
  | $10.99 | 60% | $3.75 |
  | $11.99 | 60% | $4.35 |
  | $12.99 | 60% | $4.95 |

  The jump between $9.98 and $9.99 is worth a full **$1.00** per copy. (Earlier drafts of this listing wrongly assumed the 60% rate applied at $7.99; that was my error.)
- **Expanded Distribution:** leave it **off**. KDP's own page lists coloring books as content its distributors do not accept, and it pays only 40% of list price.
- **Marketplace and territories:** primary marketplace Amazon.com; all territories.
- **Suggested starting price:** **$9.99** if it is competitive with similar kids' coloring books (royalty $3.15), otherwise no lower than $8.99. At $7.99 the royalty is only about $1.16. I cannot see competitor prices from this environment: look at 5-10 similar titles on Amazon yourself before choosing.

## Owner decisions and honest caveats
1. **AI disclosure** is Yes in the form, and the copyright page also says the art was created with AI image tools. Do not remove either.
2. **Copyright on AI images is uncertain.** In the US, purely AI-generated images may not qualify for copyright protection (as I understand the Copyright Office's guidance; **[verify]**, not legal advice). The form's "I own the copyright" option is your call. This also means competitors could copy the pages without legal consequence; it does not affect whether KDP accepts the book.
3. **Pen name vs brand:** the Author field holds the pen name, not "Little Fox Paper Co". The author name cannot be changed after publishing, so settle it before you press Publish (see TODO A1/A2).
4. **Trademark risk** from the research folder applies to the imprint line only: it appears on the cover and in the book, never alone as "Little Fox".
5. **Timing:** winter-themed, so holiday demand falls off after late December; KDP's review can take days **[verify]**.
6. **Sales are unproven.** This is the pilot for the pipeline, not a forecast.

## QA record
- 30 pages generated with `openai/gpt-image-2` (30 first-pass images; 3 rerolled for quality, with 2 replaced by chosen variants, one at medium quality). Every page was checked by eye for closed outlines, stray text, shading, anatomy and look-alike characters.
- Known cosmetic points: pages are 1152 x 1536 px, upscaled to 300 DPI, so line edges are slightly soft up close; thin wood-grain lines on the fence (page 23); the page 16 reindeer is drawn with a small spotted fawn-style coat, no red nose.

## Checklist before you press Publish
- [ ] Wren Ashby checked on Amazon Books / Kindle (TODO A1)
- [ ] Interior and cover uploaded; every page looked at in the KDP previewer, cover looked at in the cover previewer
- [ ] AI-generated images answered **Yes**; description and copyright page agree
- [ ] Price chosen after seeing KDP's minimum and royalty figures
- [ ] Optional: order one proof copy (a few dollars plus shipping) before launching
