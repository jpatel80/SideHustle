# Book 1 listing: Cozy Winter Animals Coloring Book

Status: **FINAL DRAFT for owner review** (pages, interior, cover and page count exist). Fields follow the order of the KDP "Create paperback" form. Items marked **[verify]** are things I could not confirm from KDP's public help pages; check them in the form. You paste and publish; Claude never logs in to KDP.

## Files to upload (local, not in git)
- Interior: `books/001-cozy-winter-animals/interior.pdf`: 64 pages, 8.5 x 11 in, no bleed, fonts embedded, 2.7 MB
- Cover: `books/001-cozy-winter-animals/cover.pdf`: 17.3941 x 11.25 in (back + 0.1441 in spine + front, 0.125 in bleed), 5218 x 3375 px at 300 DPI. Previews: `cover.png`, `cover_guides.png` (guides show trim, spine and safe lines)
- The front shows the owl page half colored in, as an example of coloring; the interior is black and white only, and the back cover and the description both say so. Command used: `make_cover.py ... --colored-half` (drop the flag for an all-line-art cover).
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

### Categories (choose two)
Closest fit: a children's coloring-book category (for example Children's Books > Activities, Crafts & Games > Coloring Books) and an animals-for-kids category. **[verify]** The category menu paths change; pick the nearest children's options in the form and do not pick adult coloring.

## Step 2: Paperback content
- **Print ISBN:** use the free KDP ISBN. KDP's help says coloring books are *not generally* "low-content", so the free ISBN should be offered **[verify in form]**.
- **Publication date:** leave blank (publish now).
- **Manuscript:** upload `interior.pdf`. **Bleed setting: No bleed.** Trim size: 8.5 x 11 in.
- **Interior and paper:** Black & white interior, **white** paper (the spine width in the cover assumes white paper; if you pick cream, tell Claude and the cover is rebuilt with the cream spine width).
- **Cover finish:** matte or glossy is your choice; matte is a common pick for kids' coloring books (opinion, not a KDP rule).
- **Cover:** "Upload a cover you already have (print-ready PDF)" and upload `cover.pdf`. The back cover has a blank white area where KDP can place its barcode (do not upload your own barcode).
- **Generative AI content question:** answer **Yes**. The images are **AI-generated** (not just AI-assisted): generated with OpenAI's GPT Image 2 through OpenRouter, then selected, cropped and converted to black and white by us. Describe the tool as "GPT Image 2 (OpenAI) via OpenRouter" if the form asks **[verify what the form asks]**. The book contains no AI-generated text other than the title, copyright and "belongs to" pages that we wrote. If you are unsure about the listing text, which was drafted with Claude's help, disclose rather than skip **[verify whether KDP's question covers store-page text]**.
- **Previewer:** open KDP's online previewer and page through the whole book. Check margins and that no picture touches the page edge.

## Step 3: Pricing
- **Marketplaces:** Amazon.com list price in USD; other marketplaces follow KDP's auto-conversion unless you set them.
- **Printing cost (Amazon.com, B&W, 8.5 x 11, 24-110 pages):** a flat **$2.84 per book**, from KDP's Paperback Printing Cost page (fetched 2026-11-06; check the calculator in the form).
- **Minimum list price:** printing cost / royalty rate = $2.84 / 0.60 = **about $4.73** if the 60% rate applies, or about $5.68 at 50% (my arithmetic; KDP's form shows the real minimum). **[verify which royalty rate applies at your price]**
- **Royalty examples (my estimates):** at $7.99 and 60%: 0.60 x 7.99 - 2.84 = **$1.95** per sale. At $9.99 and 60%: **$3.15**. At 50% the same prices give $1.15 and $2.15. The royalty is **per book sold**, so this is a thin-margin product until it earns reviews.
- **Suggested starting price:** $7.99-$9.99. I can't confirm what competitors charge from this environment, so compare with a few similar kids' coloring books on Amazon yourself before choosing. Do not start below $6.99.
- Enroll in KDP Select / expanded distribution: not applicable to this decision; use KDP defaults **[verify]**.

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
