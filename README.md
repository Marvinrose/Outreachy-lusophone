# Outreachy Round 32 - Lusophone Technological Wishlist
**Contributor:** Marvinrose Chibuezem (`Marvinrose_Chibuezem` on Phabricator)
**Project:** [T418284](https://phabricator.wikimedia.org/T418284) - Addressing the Lusophone Technological Wishlist Proposals
**Mentors:** Artur Corrêa Souza · Éder Porto

---

## About the project

The Lusophone technological wishlist is a community survey identifying the most needed technical improvements for Portuguese-speaking Wikimedia editors. This internship implements one of the community wishes:

- **Wish #3** - Detect duplicate references in the Visual Editor so editors
  are warned when they cite a source (by ISBN, DOI, or URL) that already exists
  in the article.
- **Wish #8** - Extend [wikiscore](https://wikiscore.toolforge.org/) to count
  Wikidata edits, enabling contests and edit-a-thons that include Wikidata work.

---

## Files

| File | Task | Description |
|---|---|---|
| `Task 1 - Intern.html` | T418285 | JavaScript - parses article JSON and displays creation dates |
| `Task 2 - Intern.py` | T418286 | Python - reads URLs from CSV and prints HTTP status codes |
| `Task 2 - Intern.csv` | T418286 | Input file provided by the mentors (unmodified) |

---

## Task 1 - JavaScript (T418285)

**How to run:** Open `Task 1 - Intern.html` in any browser. No build step needed.

**Output format:**
```
Article "André Baniwa" (Page ID 6682420) was created at September 13, 2021.
Article "Benki Piyãko" (Page ID 4246775) was created at December 10, 2013.
...
```

**Key decision - timezone-safe date parsing:**
The dates are stored as `"YYYY-MM-DD"` strings. Passing them directly to
`new Date("2021-09-13")` creates a UTC midnight timestamp, which rolls back
one day for users in timezones west of UTC (UTC-3 in Brazil, for example).
Using `new Date(year, month-1, day)` creates a local-midnight date instead,
so the displayed date always matches the stored string regardless of timezone.

---

## Task 2 - Python (T418286)

**Requirements:** `pip install requests` · Python 3.9+

**How to run:**
```bash
# Windows
python "Task 2 - Intern.py" "Task 2 - Intern.csv"

# Mac / Linux
python3 "Task 2 - Intern.py" "Task 2 - Intern.csv"
```

**Output format:**
```
(200) https://www.nytimes.com/1999/07/04/sports/...
(404) https://www.acritica.com/channels/esportes/...
(CONNECTION_ERROR) http://jogandocomelas.com.br/...
```

**Key decisions:**

- **HEAD instead of GET** - only the status code is needed, not the page body.
  HEAD requests are faster, use less bandwidth, and are more respectful to servers.

- **utf-8-sig encoding** - the CSV file contains a UTF-8 Byte Order Mark (BOM)
  at the start. Opening with `utf-8-sig` strips it automatically, preventing the
  header row from reading as `\ufeffurls` and leaking into the output.

- **Threads for concurrency** - the CSV has ~167 URLs. Sequential requests at a
  10-second timeout could take several minutes. Ten concurrent threads finish in
  under 2 minutes. The `requests` library is blocking, so threads are the right
  tool, the bottleneck is network I/O.

- **Wikimedia User-Agent policy** - all requests include a `User-Agent` header
  identifying the script per [Wikimedia's Bot Policy](https://meta.wikimedia.org/wiki/User-Agent_policy).

---

## Connection to the internship

These tasks directly preview the real project work:

- **Task 1** (parse JSON - formatted output) mirrors **Wish #3**: reading
  Wikipedia references from the MediaWiki API and displaying them in the
  Visual Editor.
- **Task 2** (HTTP requests - process responses) mirrors **Wish #8**: calling
  the Wikidata API to fetch edit records and counting them in wikiscore.

---

## References
- [T418285 - Task 1](https://phabricator.wikimedia.org/T418285)
- [T418286 - Task 2](https://phabricator.wikimedia.org/T418286)
- [Wikimedia User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy)
- [Lusophone wishlist 2025](https://meta.wikimedia.org/wiki/Lista_de_desejos_tecnol%C3%B3gicos_da_lusofonia/2025)
- [Wikiscore tool](https://wikiscore.toolforge.org/)
