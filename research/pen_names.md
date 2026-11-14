# Pen names (2026-11-14)

Rules: the KDP Author field holds a pen name, never the brand. The author name cannot be changed after a
book is published, so each name is checked **before** its first upload. Bios stay honest: no invented
credentials, no AI headshot presented as a real person. The safest bio is none at all.

| Use | Name | Status |
|---|---|---|
| Kids' books | **Wren Ashby** (fallback: Hazel Larkin) | Chosen. A web search on 2026-11-14 found no author of that name; Amazon itself has not been checked **[verify]**. |
| Adult books | **Clara Whitcombe** (placeholder on book 2) | Proposal 1. Web search found no author of that name **[verify]**. |
| Adult books | **Marian Thistlewood** | Proposal 2. Web search found no author of that name **[verify]**. |
| Adult books | **Nell Hartwell** | Proposal 3. Web search found no author of that name **[verify]**. |

Not proposed: Edith Fenwick (an "E. Fenwick" is credited on an 1898 children's book, and the name is close
to Edith Holden, whose nature diary has an official coloring book).

The web search is weak evidence (one query, general web). The Amazon check below is the one that counts.

## The check (owner, about 2 minutes per name)

1. Open amazon.com, choose the **Books** department in the search bar.
2. Search each name **in double quotes**, exactly:
   - `"Wren Ashby"`  (if taken: `"Hazel Larkin"`)
   - `"Clara Whitcombe"`
   - `"Marian Thistlewood"`
   - `"Nell Hartwell"`
3. Look at the **author line** under each result (not the title). The name fails if an author with that
   exact name has any book, in any genre. A different spelling or a character's name inside a book is fine.
4. Repeat once with the department set to **Kindle Store**.
5. Tell Claude: "Wren Ashby is free / taken" and which adult name you choose.

After you choose the adult name, Claude changes `author` in `books/002-cozy-cottage-adult/book.json`,
removes `author_is_placeholder`, and runs `python3 scripts/book_factory.py finish books/002-cozy-cottage-adult --reviewed`
(a few minutes, no cost). The name is on the cover, the title page and the upload kit.
