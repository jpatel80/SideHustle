# Book 3 listing: Happy Ocean Animals Coloring Book

Status: **FINAL DRAFT for owner review** (pages, interior, cover and page count exist; QA record at the bottom). Fields follow the order of the KDP "Create paperback" form. Items marked **[verify]** could not be confirmed from KDP's public help pages. You paste and publish; Claude never logs in to KDP.

## Files to upload (committed in `final/`)
- Interior: `books/003-happy-ocean-animals/final/interior.pdf`: 64 pages, 8.5 x 11 in, no bleed, fonts embedded
- Cover: `books/003-happy-ocean-animals/final/cover.pdf`: 17.3941 x 11.25 in (5218 x 3375 px at 300 DPI), spine 0.1441 in (back + spine + front, 0.125 in bleed). The spine is blank (under KDP's 80-page spine-text rule).
- Verify the cover in KDP's cover previewer; if KDP reports a different spine width, tell Claude and the cover is regenerated.

## Step 1: Paperback details
- **Language:** English
- **Book title:** Happy Ocean Animals Coloring Book
- **Subtitle:** 30 Big, Simple Pictures for Kids Ages 3-6
- **Author:** Wren Ashby. Do **not** put "Little Fox Paper Co" in the Author field.
- **Imprint** (cover, title page, copyright page only): Little Fox Paper Co

### Description (paste into the description box; HTML is accepted)
```
Dive into a sea of smiles! This coloring book has 30 big, simple pictures of friendly ocean animals, from a happy whale and a waving octopus to a sea turtle, a crab, a jellyfish and a dolphin leaping over a wave. Every picture has extra-thick lines and large open spaces, so it is easy for little hands to color inside the lines.<br><br>
<b>What's inside</b><br>
&bull; 30 one-sided coloring pages, with a blank page behind each picture<br>
&bull; One big, simple subject on every page, with very few small details<br>
&bull; Extra-thick lines and large spaces for crayons and chunky markers<br>
&bull; A "This book belongs to" page<br>
&bull; Large 8.5 x 11 inch pages<br><br>
A fun quiet-time activity for young children and an easy gift for kids who love the sea.<br><br>
The inside pages are printed in black and white, ready for you to color. The colors on the cover are just an example.<br><br>
The illustrations in this book were created with AI image tools and were selected and arranged by the publisher, Little Fox Paper Co.
```
(about 1,000 characters; KDP's limit is 4,000 **[verify]**)

- **Publishing rights:** "I own the copyright and I hold necessary publishing rights." See owner decision 2.
- **Primary audience, sexually explicit content:** No
- **Reading age:** minimum 3, maximum 6 **[verify field names and the allowed range]**

### Keywords (7 slots)
1. big simple pictures for toddlers and preschool kids
2. thick line sea animal coloring pages
3. easy coloring for little hands
4. quiet time activity for ages 3 to 6
5. gift for kids who love the beach
6. whale octopus turtle and dolphin pictures to color
7. single sided coloring pages for crayons

Slot limits (about 50 characters each) **[verify]**. No brand names. Note: nothing is described as educational.

### Categories (choose two)
Closest fit: a children's coloring-book category and a children's animals / ocean category. **[verify]** menu paths.

## Step 2: Paperback content
- **Print ISBN:** use the free KDP ISBN **[verify it is offered]**.
- **Manuscript:** upload `interior.pdf`. **Bleed: No bleed.** Trim size 8.5 x 11 in. Black & white interior, **white** paper.
- **Cover:** upload `cover.pdf`. Do not upload your own barcode.
- **Generative AI content question:** answer **Yes**: **AI-generated** images made with OpenAI's GPT Image 2 through OpenRouter, selected, cropped and converted to black and white by us. If unsure about the store-page text (drafted with Claude's help), disclose rather than skip **[verify]**.
- **Previewer:** page through the whole book in KDP's previewer.

## Step 3: Pricing
- **Printing cost (Amazon.com, B&W, 8.5 x 11, 24-110 pages):** flat **$2.84 per book** (KDP's Paperback Printing Cost page, fetched 2026-11-06).
- **Minimum list price:** about **$4.73** at the 60% rate (about $5.68 at 50%) **[verify which rate applies]**.
- **Royalty examples (my estimates):** $7.99 at 60% = **$1.95** per sale; $6.99 = **$1.35**; $9.99 = **$3.15**.
- **Suggested starting price:** $6.99-$8.99. Compare a few similar kids' coloring books on Amazon yourself; I could not check competitor prices from this environment.

## Owner decisions and honest caveats
1. **AI disclosure** is Yes in the form and on the copyright page. Do not remove either.
2. **Copyright on AI images is uncertain** in the US **[verify]**; the "I own the copyright" tick is your call.
3. **Pen name:** same as books 1 and 2. The author name cannot be changed after publishing.
4. **Niche is untested and crowded:** ocean animals is a broad evergreen topic, but I could not measure demand or competition **[verify]**. Book 3 is deliberately simpler than book 1 so the two titles do not compete.
5. Sales are unproven; this is a test.

## QA record
- 30 pages generated with `openai/gpt-image-2` at low quality plus an "extra simple for ages 3 to 6" instruction. Every page was checked by eye for closed outlines, stray text, fills, anatomy and look-alike characters.
- Page 11 (shark) was regenerated: the first version had a big toothy grin and eyebrows that looked too close to a well-known cartoon shark. The replacement has a calm closed smile and no teeth.
- Known overlaps with book 1 (different pictures, same ideas): a seal with a ball, a penguin, a whale. Acceptable, but if you would rather avoid repeats across the catalog, tell Claude and those pages can be swapped.
- Page 14 (manta ray) is the least polished: the face sits oddly on a very simple shape. Page 28 (eel in a rock) reads a little like a snake. Both are closed, colorable drawings; tell Claude if you want them redone.
- Spend for this book: see `final/MANIFEST.md`.

## Checklist before you press Publish
- [ ] Wren Ashby checked on Amazon Books / Kindle
- [ ] Interior and cover uploaded; every page looked at in the previewer; cover looked at in the cover previewer
- [ ] AI-generated images answered **Yes**; description and copyright page agree
- [ ] Price chosen after seeing KDP's minimum and royalty figures
