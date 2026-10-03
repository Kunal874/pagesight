# Data — ViDoRe V3

Facts about the ViDoRe V3 benchmark on Hugging Face, collected on 2026-10-03 from the Hub API, the dataset-viewer
API (`datasets-server.huggingface.co`), the dataset cards, the ViDoRe V3 blog post and the arXiv paper. No dataset
files or images were downloaded; only JSON responses, cards and web pages were read. Each number below comes from one
of those responses. Tags: **[API]** Hub or dataset-viewer response, **[card]** dataset card, **[blog]** blog post,
**[paper]** arXiv paper. "Unverified" means it could not be checked.

## Chosen subsets (DECISIONS.md D-012 to D-014)

- **Used:** `vidore/vidore_v3_hr` (1,110 pages, 318 English queries) and `vidore/vidore_v3_finance_en` (2,942 pages,
  309 English queries): 4,052 pages and 627 English queries in total.
- **Queries:** English rows only (`language == "english"`), split 30% dev / 70% test per subset with a fixed seed.
- **Relevance:** graded qrels (2 = fully relevant, 1 = critically relevant); nDCG uses the grades.
- **Page text for text baselines:** the `markdown` field (OCR text of the page image).
- The rest of this file is the survey of all candidates that led to this choice.

## Overall totals

| Claim (brief, card, blog, paper abstract) | What was checked | Status |
| --- | --- | --- |
| 10 datasets | 8 public repos in the `vidore` org and in the "ViDoRe Benchmark V3" collection [API]; blog and paper name 2 private ones | 8 verified; 2 private ones unverified |
| ~26,000 pages | Public corpora: 19,252 page rows [API /size]; the 8 cards add up to 19,256 (energy card says 2,229, the data has 2,225) | Public part verified; the private part (26,000 − 19,256 = 6,744, if the rounded 26,000 were exact) unverified |
| 3,099 queries | Public: 2,419 English query rows [API /statistics, /filter], equal to the card sum of queries without translations; 14,514 query rows in all = 6 × 2,419 [API /size] | Public part verified; the private part (3,099 − 2,419 = 680) unverified |
| 6 query languages | `language` has 6 values: english, french, spanish, italian, german, portuguese [API /statistics] | Verified |
| Relevance labels, bounding boxes, reference answers | Present as `qrels.score`, `qrels.bounding_boxes`, `queries.answer` / `queries.raw_answers` [API /info] | Verified |
| "Human-verified" queries | `query_generator` is `human` or `sdg` (synthetic); e.g. finance_en 1,290 human vs 564 sdg rows [API /statistics] | Queries are not all human-written; the blog says relevance labels and answers were made or checked by human annotators |

## Candidate subsets (public)

All 8 public subsets are listed. The first 5 have English documents and are the candidates; the last 3 have French
documents (their English queries are translations). Page and query counts are [API]; "#queries (EN)" counts rows with
`language == "english"`. Parquet size is `num_bytes_parquet_files` for all 4 configs [API /size], in MB (10^6 bytes).

| HF id | domain | doc language | #pages | #queries (EN) | qrels grades | answers? | page text? | parquet size | gated | licence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `vidore/vidore_v3_finance_en` | Finance: 6 U.S. bank 10-K reports, FY2024 | English | 2,942 | 309 | 1, 2 (graded) | yes | yes, `markdown` | 1,266.0 MB | no | CC BY 4.0; documents: SEC public domain |
| `vidore/vidore_v3_hr` | HR: 14 EU reports | English | 1,110 | 318 | 1, 2 (graded) | yes | yes, `markdown` | 442.7 MB | no | CC BY 4.0; documents: CC BY 4.0 |
| `vidore/vidore_v3_industrial` | Industrial maintenance: 27 USAF technical orders | English | 5,244 | 283 | 1, 2 (graded) | yes | yes, `markdown` | 2,052.2 MB | no | CC BY 4.0; documents: USAF Distribution Statement A |
| `vidore/vidore_v3_pharmaceuticals` | Pharmaceuticals: 50 FDA slide decks + 2 books | English | 2,313 | 364 | 1, 2 (graded) | yes | yes, `markdown` | 752.3 MB | no | CC BY 4.0; documents: FDA public domain (see licence notes) |
| `vidore/vidore_v3_computer_science` | Computer science: 2 OpenStax textbooks | English | 1,360 | 215 | 1, 2 (graded) | yes | yes, `markdown` | 513.4 MB | no | CC BY 4.0; documents: CC BY 4.0 |
| `vidore/vidore_v3_energy` | Energy: 41 French public-agency reports | French | 2,225 (card: 2,229) | 308 (translated) | 1, 2 (graded) | yes | yes, `markdown` | 1,127.8 MB | no | CC BY 4.0; documents: mixed (see notes) |
| `vidore/vidore_v3_physics` | Physics: 42 lecture slide decks | French | 1,674 | 302 (translated) | 1, 2 (graded) | yes | yes, `markdown` | 1,216.3 MB | no | CC BY 4.0; documents: CC BY 4.0 |
| `vidore/vidore_v3_finance_fr` | Finance: 5 French luxury-company annual reports | French | 2,384 | 320 (translated) | 1, 2 (graded) | yes | yes, `markdown` | 990.9 MB | no | CC BY 4.0; documents: INPI reuse licence |

- **qrels grades:** 2 = "Fully Relevant" (the page has the complete answer), 1 = "Critically Relevant" (the page has
  required facts, but more information is needed) [card]. /filter finds 0 qrels rows with any other score in all 8
  subsets, so qrels list relevant pages only (no score-0 rows) [API]. Rows with score 2 (all languages): finance_en
  2,400 of 8,766; hr 1,686 of 10,386; industrial 2,244 of 9,684; pharmaceuticals 1,578 of 10,392; computer_science
  1,032 of 6,294 [API].
- **answers:** `answer` (string, merged from the human annotations with an LLM [card]) and `raw_answers` (list of
  answers written by human annotators [card]; 1–3 per query where /statistics ran [API]).
- **page text:** `markdown` is text extracted from the page image by an OCR pipeline [card]; the paper says textual
  retrievers were given Markdown from the NVIDIA NeMo Retriever extraction service [paper].
- **#queries (EN):** finance_en, industrial and the 3 French subsets from /statistics `language` frequencies; hr,
  pharmaceuticals and computer_science from /filter (`language = 'english'`). The 8 English counts add up to 2,419,
  the same as the cards' "queries without counting translations" [API, card].
- **Reported retrieval scores** (English queries, NDCG@10) [blog]: colsmol256 — computer_science 0.574,
  pharmaceuticals 0.514, finance_en 0.477, hr 0.460, industrial 0.385; best model in that table (nemo-colembed-3b) —
  0.778, 0.669, 0.695, 0.649, 0.570.
- **gated:** `gated: false` and `private: false` for all 8 [API]. No token or login is needed.
- **Size limit note:** finance_en (1,266.0 MB) and industrial (2,052.2 MB) are over 1 GB of parquet; hr, pharmaceuticals
  and computer_science are under 1 GB [API /size].

## Per-subset notes

### Common to all 8 subsets

- **Configs and splits:** 4 configs — `corpus`, `queries`, `qrels`, `documents_metadata` — each with one split, `test`
  [API /splits]. There is no train or dev split.
- **Columns and types** [API /info]:

| config | columns (type) |
| --- | --- |
| `corpus` | `corpus_id` int64, `image` Image, `doc_id` string, `markdown` string, `page_number_in_doc` int64 |
| `queries` | `query_id` int64, `query` string, `language` string, `query_types` list[string], `query_format` string, `content_type` list[string], `raw_answers` list[string], `query_generator` string, `query_generation_pipeline` string, `source_type` string, `query_type_for_generation` string, `answer` string |
| `qrels` | `query_id` int64, `corpus_id` int64, `score` int64, `content_type` list[string], `bounding_boxes` list[{`annotator` int64, `x1` int64, `x2` int64, `y1` int64, `y2` int64}] |
| `documents_metadata` | `file_name` string, `doc_id` string, `url` string, `doc_type` string, `doc_language` string, `doc_year` int64 (string in industrial, pharmaceuticals, physics), `visual_types` list[string], `page_number` int64, `license` string |

- **Card vs schema:** the cards describe `content_type` as a string and `bounding_boxes` as a list of int tuples; the
  API schema has a list of strings and a list of structs (above).
- **Queries and languages:** each query is given in 6 languages, as separate rows with their own `query_id` [card,
  API]. Where /statistics ran (5 subsets), each language has exactly 1/6 of the rows; in hr, pharmaceuticals and
  computer_science the English rows are exactly 1/6 (/filter) [API]. qrels cover the translated copies too: the last
  qrels row has the highest query_id (hr 1907, finance_en 1853, industrial 1697) [API /rows].
- **Row order quirk:** the English rows are not simply the first N rows. finance_en has 309 English rows, but row 308
  is French; hr has 318 English rows, but row 317 is French [API /rows]. The first 100 rows are English in every
  English-document subset [API /first-rows]. Select English queries with `language == "english"`, not by `query_id`
  range.
- **Query fields** (values seen in /statistics and /first-rows) [API]: `query_format` ∈ {question, instruction, keyword};
  `query_types` and `query_type_for_generation` use 7 labels: extractive, open-ended, boolean, compare-contrast,
  numerical, enumerative, multi-hop; `query_generator` ∈ {human, sdg}; `query_generation_pipeline` ∈ {gretel,
  custom_pipeline}, null for human-written queries (its null count equals the `human` count); `source_type` ∈
  {summary, image}.
- **content_type values** seen in the first-rows samples of queries and qrels [API]: Text, Table, Chart, Infographic,
  Image, Mixed, Other, and `N/A (If relevance score=0)`. The last one appears in query rows of finance_en, industrial
  and pharmaceuticals, although no qrels row has score 0.
- **qrels format:** one row per (query_id, corpus_id) pair with `score`, `content_type` and `bounding_boxes`. In the
  first-rows samples every qrel has 1–16 boxes and annotator ids 0–2 [API]. The blog's plotting example draws
  `(x1, y1)`–`(x2, y2)` directly on the page image, so boxes are in image pixels [blog].
- **qrels ÷ queries:** qrels rows divided by query rows is 4.73 (finance_en), 5.44 (hr), 5.70 (industrial), 4.76
  (pharmaceuticals), 4.88 (computer_science), 3.58 (energy), 7.21 (physics), 4.59 (finance_fr) [API]. The cards'
  "average number of pages per query" agrees only for finance_en (4.7); hr says 9.4 and industrial 1.8 [card].
- **Page numbers:** `page_number_in_doc` starts at 0 in every subset (/statistics min = 0) [API].
  `documents_metadata.page_number` is the page count of each document; it matches the corpus rows per `doc_id`
  in every subset except energy (one document: 104 in metadata, 102 corpus rows) [API].
- **Empty page text:** `markdown` has minimum length 0 in 6 of 8 subsets (pharmaceuticals min 10, physics min 55)
  [API /statistics]. Pages with empty `markdown`: hr 12 of 1,110 (/filter); pharmaceuticals and physics 0 (minimum
  length above 0); the other subsets: count not obtained (unverified) [API]. In the first-rows samples of the 5
  English-document subsets, tables appear as pipe-delimited rows; no HTML tables or image links were seen
  [API /first-rows].
- **Original PDFs** are in each repo under `pdfs/` with a `pdfs/metadata.csv` [API file list]. They are not part of the
  parquet sizes.
- **Revisions:** each card names a "commit used for end-to-end evaluation". For the 5 English-document subsets that
  commit resolves on the Hub and has the same configs, row counts and file list as the current revision [API].
- **Dataset viewer:** preview, viewer, search, filter and statistics are enabled for all 8 [API /is-valid]. /statistics
  failed for `qrels` in all 8 subsets and for `queries` in hr, pharmaceuticals and computer_science (a histogram
  error) [API]. For the `image` column, /statistics reports widths: its values match the first-rows widths (finance_en:
  min = max = 1,700, and its pages are 1700 × 2200) [API].

### Sizes [API /size, Hub API]

| subset | corpus parquet | queries | qrels | documents_metadata | total parquet | in memory | repo storage (incl. PDFs) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| finance_en | 1,265.3 MB (3 files) | 0.51 MB | 0.15 MB | 0.01 MB | 1,266.0 MB | 1,288.9 MB | 1,293.5 MB |
| hr | 442.1 MB (1 file) | 0.56 MB | 0.08 MB | 0.01 MB | 442.7 MB | 450.2 MB | 495.5 MB |
| industrial | 2,051.5 MB (5 files) | 0.55 MB | 0.13 MB | 0.01 MB | 2,052.2 MB | 2,085.3 MB | 2,680.8 MB |
| pharmaceuticals | 751.5 MB (2 files) | 0.75 MB | 0.08 MB | 0.01 MB | 752.3 MB | 762.3 MB | 823.5 MB |
| computer_science | 512.9 MB (2 files) | 0.42 MB | 0.06 MB | 0.01 MB | 513.4 MB | 523.5 MB | 578.3 MB |
| energy | 1,127.2 MB (3 files) | 0.53 MB | 0.12 MB | 0.01 MB | 1,127.8 MB | 1,139.8 MB | 1,288.1 MB |
| physics | 1,215.3 MB (3 files) | 0.89 MB | 0.16 MB | 0.01 MB | 1,216.3 MB | 1,218.4 MB | 1,328.8 MB |
| finance_fr | 990.3 MB (3 files) | 0.50 MB | 0.13 MB | 0.01 MB | 990.9 MB | 1,004.1 MB | 1,041.9 MB |
| **all 8** | | | | | **8,361.6 MB** | **8,472.5 MB** | |

"In memory" is `num_bytes_memory`. "Repo storage" is the Hub `usedStorage` value, which covers the whole repo
(parquet, PDFs, and possibly older revisions).

### `vidore/vidore_v3_finance_en`

- Revision `7f432c176d82e27546501ad8064a713ac3071809`, last modified 2026-01-15 [API]. Evaluation commit in card:
  `0fe6508053e8aa31b1f1eaec4553f79e3974f59a` [card].
- Six 10-K annual reports from major U.S. financial institutions, fiscal year ended 2024-12-31 [card]. Pages per
  document: citigroup_2024 963, goldman_sachs_2024 614, jpmorgan_chase_2024 437, wells_fargo_2024 355,
  bank_of_america_2024 305, morgan_stanley_2024 268 [API /statistics].
- Rows: corpus 2,942; queries 1,854 (309 per language); qrels 8,766; documents_metadata 6 [API].
- Query rows by source: human 1,290, sdg 564. Format: question 1,146, instruction 462, keyword 246 (all languages)
  [API /statistics].
- Page images: 1700 × 2200 (all 43 first-rows rows); every one of the 2,942 pages is 1,700 px wide [API].
- `markdown` sample: row 0 has 634 characters, row 1 has 7,523. Whole corpus: min 0, median 3,809, mean 3,857, max
  9,835 characters [API].
- Content: main modalities Text, Table [blog]. `visual_types` is table, text, chart for all 6 documents [API]. In the
  first 100 English query rows, `content_type` includes Table 71 times and Chart 12 times (sample only) [API].
- Document licence field: "Public Domain (Website section of https://www.sec.gov/about/privacy-information)" for all 6
  [API].

### `vidore/vidore_v3_hr`

- Revision `0cdf0979f2c5a0fd3e335e6373b9da48a9fe3bc3`, last modified 2026-01-15 [API]. Evaluation commit in card:
  `95f2f83a5a09590a89e34960479f9438e48bca77` [card].
- 14 reports from the European administration [card] on EU labour markets, social development and employment policy
  [paper]; all `doc_year` 2024, 20–202 pages per document [API].
- Rows: corpus 1,110; queries 1,908 (318 English via /filter); qrels 10,386; documents_metadata 14 [API].
- The card metadata has no `language` field and no `language:en` tag (the other 7 have one); the card text says en
  [API, card].
- Page images: 1654 × 2339 (66 of 67 first-rows rows; one is 1653 × 2339); widths 1,386–2,339 px, median 1,654 [API].
- `markdown` sample: row 0 has 246 characters, row 1 has 308. Whole corpus: min 0, median 3,127, mean 3,103, max 10,042
  [API].
- Content: Text, Table, Charts [blog]. `visual_types` over 14 documents: text 14, chart 13, table 10, image 8 [API]. In
  the first 100 English query rows, `content_type` includes Chart 39, Table 33, Infographic 11 times (sample only)
  [API].
- Document licence field: `cc-by-4.0` for all 14 [API].

### `vidore/vidore_v3_industrial`

- Revision `e26c864724f5dd71a3d7d739272d95637764cee9`, last modified 2026-01-15 [API]. Evaluation commit in card:
  `233d20721f4deb392a09a86cca01761adbc91157` [card].
- 27 USAF technical orders on military aircraft maintenance (fueling, mechanics) [card, paper]; `doc_year` 1999–2025;
  2–892 pages per document [API]. Largest public corpus.
- Rows: corpus 5,244; queries 1,698 (283 per language); qrels 9,684; documents_metadata 27 [API].
- Query rows by source: human 1,062, sdg 636. Format: question 966, instruction 504, keyword 228 [API /statistics].
- Page images in the first 100 rows: 1700 × 2200 (82) and 1000 × 1600 (18); widths 1,000–2,200 px, median 1,700 [API].
- `markdown` sample: row 0 has 602 characters, row 1 has 605. Whole corpus: min 0, median 1,688.5, mean 1,928, max
  6,852 [API].
- Content: Text, Tables, Infographics, Images [blog]. `visual_types` over 27 documents: text 27, table 23, infographic 22,
  image 10, chart 6 [API]. First 100 English query rows: Table 29, Infographic 20, Image 6, Chart 2 (sample only)
  [API].
- Document licence field: USAF "DISTRIBUTION STATEMENT A" text (approved for public release, distribution unlimited)
  for all 27 [API].

### `vidore/vidore_v3_pharmaceuticals`

- Revision `3abd4aa8a9445fb5538a78a19ba50bd57bd22b5c`, last modified 2026-01-15 [API]. Evaluation commit in card:
  `262e203d7c59c55947f7042812e0bcc1eee190b1` [card].
- The card describes slide decks from the FDA website [card]; the paper says FDA presentations and Springer books
  [paper]. `documents_metadata`: 50 `slides` and 2 `book` rows; the books are `drug_resistance_book` (452 pages) and
  `medicine_vaccine_book` (373 pages), with link.springer.com URLs, so 825 of 2,313 pages come from books [API].
- Rows: corpus 2,313; queries 2,184 (364 English via /filter); qrels 10,392; documents_metadata 52 [API].
- Page images in the first 100 rows: 2000 × 1125 (64) and 2000 × 1500 (36); widths 1,221–4,000 px, median 2,000 [API].
- `markdown` sample: row 0 has 369 characters, row 1 has 394. Whole corpus: min 10, median 695, mean 1,436, max 15,465
  [API].
- Content: Text, Charts, Images, Infographic, Tables [blog]. `visual_types` over 52 documents: text 52, infographic 38,
  chart 35, image 34, table 25 [API]. First 100 English query rows: Infographic 31, Chart 20, Table 16, Image 15
  (sample only) [API].
- Document licence field: the FDA website notice (contents not copyrighted, public domain) for all 52, including the
  2 Springer books (see licence notes) [API].

### `vidore/vidore_v3_computer_science`

- Revision `d5cc75883d92e294f0c0fc2662551c9708a06ebc`, last modified 2026-01-15 [API]. Evaluation commit in card:
  `7b91f10e18b72a763dd17a0c05d66bf985b98f1d` [card].
- Two OpenStax textbooks: Introduction_to_Computer_Science (945 pages) and Introduction_to_Python_Programming (415
  pages) [card, API].
- Rows: corpus 1,360; queries 1,290 (215 English via /filter); qrels 6,294; documents_metadata 2 [API].
- Page images: 1700 × 2200 (all 100 first-rows rows); every one of the 1,360 pages is 1,700 px wide [API].
- `markdown` sample: row 0 has 36 characters, row 1 is empty. Whole corpus: min 0, median 2,393, mean 2,375, max 4,992
  [API]. Samples include Markdown headings.
- Content: Text, Infographic, Tables [blog]. `visual_types` lists image, table, infographic, text, chart for both books
  [API]. First 100 English query rows: Table 35, Infographic 21, Other 8, Chart 6 (sample only) [API].
- Document licence field: OpenStax content under CC BY 4.0, for both books [API].
- Retrieval scores in the blog's English results table are highest on this subset [blog].

### French-document subsets (not candidates)

- **`vidore/vidore_v3_energy`** — revision `caec06d3c73434d635f710f93bcd898331c59f20`. The card and the paper give 42
  documents and 2,229 pages (the blog also gives 2,229 pages); the data has 41 `documents_metadata` rows, 41 distinct
  `doc_id`s, 41 PDFs and 2,225 corpus rows [API]. Queries 1,848 (308 per language), qrels 6,618. Mostly landscape
  pages (2341 × 1655 in 52 of 56 first-rows rows). `markdown` median 2,822 characters. Document licences are mixed:
  an insee.fr information-page URL (18), Etalab 2.0 (13), the legal-notice page of
  statistiques.developpement-durable.gouv.fr (9), CC BY-SA 3.0 (1) [API].
- **`vidore/vidore_v3_physics`** — revision `a0de276f515acc044b72cae8de53a44bb5a8f1f5`. 42 slide decks from a
  bachelor-level French physics course [card]; 1,674 pages, all 2667 × 1500 in the first rows and 2,667 px wide in
  /statistics. Queries 1,812 (302 per language), qrels 13,068. `markdown` median 584.5 characters. Document licence
  CC-BY-4.0 for all 42 [API].
- **`vidore/vidore_v3_finance_fr`** — revision `1d808daa08032ffecdf62da151a7f7a8fe2bd0c9`. Annual reports of 5 French
  luxury companies [card]: `doc_id`s kering_2023, christian_dior_2023, hermes_2023, loreal_2023, lvmh_2023 [API].
  2,384 pages, mostly 1733 × 2402 (38 of 39 first-rows rows). Queries 1,920 (320 per language), qrels 8,808.
  `markdown` median 3,977 characters. Document licence: INPI data-reuse licence URL for all 5. The repo also contains
  a stray `pdfs/.DS_Store` [API].

### Related repos (not inspected in detail)

- `vidore/vidore_v3_<name>_mteb_format` (8 repos, not gated) [API]. The finance_en one (CC BY 4.0) has per-language
  configs such as `english-corpus` (`id`, `image`), `english-queries` (`id`, `text`, `language`; 309 rows) and
  `english-qrels` (`query-id`, `corpus-id`, `score`; 8,766 rows) [API]. No page text column in this format.
- `mteb/Vidore3<Name>OCRRetrieval` (8 repos) exist in the `mteb` org [API search].

## Not available

- The benchmark has 10 datasets; 8 are public and 2 are kept private as a hold-out set to limit overfitting
  [blog, paper]. The blog says the MTEB team manages them and discloses only domain and document language:
  - nuclear energy regulatory documents (English);
  - telecom-related technical standard documents (English).
- Neither is on the Hub publicly: the `vidore` org listing (92 public datasets) and the V3 collection (8 items) do not
  contain them, and Hub searches for `vidore_v3_nuclear` and `vidore_v3_telecom` return 0 results [API].
- Their page counts, query counts and licences are unverified. The paper's corpus table (Table 6) lists only the 8
  public corpora; its result tables include Nuclear and Telecom scores [paper].

## Licence and citation

- **Dataset licence:** `cardData.license` is `cc-by-4.0` for all 8 subsets [API]. The card licence section says CC BY
  4.0 covers the annotations, qrels and metadata made for the benchmark, while the source documents and the parsed
  `markdown` text keep their publishers' licences, recorded per document in `documents_metadata.license` [card]. The
  paper calls the release "commercially permissive" [paper].
- **Source-document licences** (all `documents_metadata` rows read) [API]:

| subset | `license` values |
| --- | --- |
| finance_en | SEC website "Public Domain" (6/6) |
| hr | `cc-by-4.0` (14/14) |
| industrial | USAF Distribution Statement A: public release, distribution unlimited (27/27) |
| pharmaceuticals | FDA website public-domain notice (52/52) |
| computer_science | OpenStax CC BY 4.0 (2/2) |
| energy | insee.fr information-page URL (18), Etalab 2.0 (13), statistiques.developpement-durable.gouv.fr legal-notice URL (9), `cc-by-sa 3.0` (1) |
| physics | `CC-BY-4.0` (42/42) |
| finance_fr | data.inpi.fr data-reuse licence page URL (5/5) |

- **Pharmaceuticals caveat:** the 2 Springer books carry the FDA notice in their `license` field, which does not
  describe a Springer book. Their Springer pages say "Open Access", but the specific licence was not shown in the
  fetched pages: unverified. Together they are 825 of the 2,313 pages.
- **Paper licence:** the arXiv record links CC BY 4.0 [paper].
- **Gating:** none; all 8 are public and not gated [API].
- **Citation:** the 8 dataset cards contain no BibTeX; they link the arXiv preprint 2601.08620 [card]. The arXiv BibTeX
  export gives:

```bibtex
@misc{loison2026vidorev3comprehensiveevaluation,
      title={ViDoRe V3: A Comprehensive Evaluation of Retrieval Augmented Generation in Complex Real-World Scenarios},
      author={António Loison and Quentin Macé and Antoine Edy and Victor Xing and Tom Balough and Gabriel Moreira and Bo Liu and Manuel Faysse and Céline Hudelot and Gautier Viaud},
      year={2026},
      eprint={2601.08620},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2601.08620},
}
```

The card of `vidore/vidore_v3_finance_en_mteb_format` cites the blog post:

```bibtex
@misc{mace2025vidorev3,
  author    = {Macé, Quentin and Loison, Antonio and EDY, Antoine and Xing, Victor and Viaud, Gautier},
  title     = {ViDoRe V3: a comprehensive evaluation of retrieval for enterprise use-cases},
  year      = {2025},
  month     = {November},
  day       = {5},
  publisher = {Hugging Face},
  journal   = {Hugging Face Blog},
  howpublished = {\url{https://huggingface.co/blog/QuentinJG/introducing-vidore-v3}}
}
```

## Sources

All fetched 2026-10-03. `<name>` is one of hr, finance_en, industrial, pharmaceuticals, computer_science, energy,
physics, finance_fr; `<config>` is one of corpus, queries, qrels, documents_metadata.

- https://huggingface.co/api/datasets?author=vidore&limit=200
- https://huggingface.co/api/collections?owner=vidore&limit=100
- https://huggingface.co/api/collections/vidore/vidore-benchmark-v3-690b14a55d13035cef73e680
- https://huggingface.co/api/datasets/vidore/vidore_v3_<name>
- https://huggingface.co/datasets/vidore/vidore_v3_<name>/raw/main/README.md
- https://huggingface.co/api/datasets/vidore/vidore_v3_<name>/revision/<evaluation commit> (the 5 English-document
  subsets)
- https://datasets-server.huggingface.co/splits?dataset=vidore/vidore_v3_<name>
- https://datasets-server.huggingface.co/info?dataset=vidore/vidore_v3_<name>
- https://datasets-server.huggingface.co/size?dataset=vidore/vidore_v3_<name>
- https://datasets-server.huggingface.co/is-valid?dataset=vidore/vidore_v3_<name>
- https://datasets-server.huggingface.co/statistics?dataset=vidore/vidore_v3_<name>&config=<config>&split=test
- https://datasets-server.huggingface.co/first-rows?dataset=vidore/vidore_v3_<name>&config=<config>&split=test
- https://datasets-server.huggingface.co/rows?dataset=vidore/vidore_v3_<name>&config=<config>&split=test&offset=<n>&length=1
  (queries and qrels of hr, finance_en, industrial)
- https://datasets-server.huggingface.co/filter?dataset=vidore/vidore_v3_<name>&config=<config>&split=test&where=<condition>&length=1
  (conditions: `"language"='english'` on queries of hr, pharmaceuticals, computer_science; `"score" <> 1 AND
  "score" <> 2` on qrels of all 8; `"score" = 2` on qrels of the 5 English-document subsets; `"markdown" = ''` on
  the hr corpus)
- https://huggingface.co/api/datasets?search=vidore_v3&limit=200
- https://huggingface.co/api/datasets?search=vidore_v3_nuclear&limit=50
- https://huggingface.co/api/datasets?search=vidore_v3_telecom&limit=50
- https://huggingface.co/api/datasets?author=mteb&search=vidore&limit=100
- https://huggingface.co/api/datasets/vidore/vidore_v3_finance_en_mteb_format
- https://huggingface.co/datasets/vidore/vidore_v3_finance_en_mteb_format/raw/main/README.md
- https://huggingface.co/blog/QuentinJG/introducing-vidore-v3
- https://huggingface.co/api/papers/2601.08620
- https://arxiv.org/abs/2601.08620
- https://arxiv.org/bibtex/2601.08620
- https://arxiv.org/html/2601.08620v2
- https://link.springer.com/book/10.1007/978-3-030-27874-8
- https://link.springer.com/book/10.1007/978-3-030-83114-1
