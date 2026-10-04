# VLM probe

One section per candidate; peak VRAM is `torch.cuda.max_memory_allocated` during generation.

## Qwen/Qwen3.5-2B (bf16)

`scripts/probe_vlm.py` at 0e42a64; revision unknown; max 1,600,000 pixels per page; load 164 s; weights 4.12 GB VRAM; greedy, max 128 new tokens.

| sample | input tokens | new tokens | seconds | peak VRAM GB | answer | reference |
|---|---:|---:|---:|---:|---|---|
| hr-q163 | 1638 | 5 | 3.5 | 4.51 | NOT_FOUND | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |
| finance_en-q102 | 1659 | 5 | 1.4 | 4.51 | NOT_FOUND | The gross liabilities for securities loaned or sold under agreements to repurchase that faced potential jurisdictional u |
| hr-q107 | 1637 | 5 | 1.3 | 4.51 | NOT_FOUND | Labour market investments in skills lead to long-term economic gains and regional convergence by increasing labour produ |
| 3 pages | 4781 | 90 | 13.8 | 6.26 | Based on the provided document, the answer is NOT_FOUND. The document does not contain information about the rates of part-time workers in Europe for the year 2 | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |

## OpenGVLab/InternVL3_5-2B-HF (bf16)

`scripts/probe_vlm.py` at 0e42a64; revision unknown; max 1,600,000 pixels per page; load 160 s; weights 4.37 GB VRAM; greedy, max 128 new tokens.

| sample | input tokens | new tokens | seconds | peak VRAM GB | answer | reference |
|---|---:|---:|---:|---:|---|---|
| hr-q163 | 1875 | 91 | 11.5 | 5.20 | The countries in Europe that report the highest rates of part-time workers in 2024 are:  - CH (Switzerland): 12 part-time employment for EU movers females and 1 | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |
| finance_en-q102 | 3408 | 34 | 6.0 | 6.60 | The page does not provide information on the amount of liabilities faced potential jurisdictional uncertainties in Citigroup’s securities financing transactions | The gross liabilities for securities loaned or sold under agreements to repurchase that faced potential jurisdictional u |
| hr-q107 | 1874 | 11 | 2.0 | 5.20 | Not found.  Page: [p:1] | Labour market investments in skills lead to long-term economic gains and regional convergence by increasing labour produ |
| 3 pages | 7014 | 67 | 138.1 | 12.43 | Based on the table in page hr-419, the countries with the highest rates of part-time workers in 2024 are:  - EFTA: 11 - CH: 12 - IS: 8  These countries report t | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |

## Qwen/Qwen3.5-4B (4-bit NF4)

`scripts/probe_vlm.py` at 0e42a64; revision unknown; max 1,600,000 pixels per page; load 293 s; weights 3.29 GB VRAM; greedy, max 128 new tokens.

| sample | input tokens | new tokens | seconds | peak VRAM GB | answer | reference |
|---|---:|---:|---:|---:|---|---|
| hr-q163 | 1638 | 128 | 26.4 | 3.99 | Based on the provided page [p:hr-419], we can analyze the table to determine which countries report the highest rates of part-time workers in 2024.  1.  **Ident | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |
| finance_en-q102 | 1659 | 100 | 20.8 | 4.01 | Based on the provided page [p:132], the text states:  "Includes activity where uncertainty exists as to the enforceability of certain master netting agreements  | The gross liabilities for securities loaned or sold under agreements to repurchase that faced potential jurisdictional u |
| hr-q107 | 1637 | 128 | 25.6 | 3.99 | Based on the provided page [p:5], the text does not contain information comparing the long-term effects of labour market investments to housing investments in r | Labour market investments in skills lead to long-term economic gains and regional convergence by increasing labour produ |
| 3 pages | 4781 | 128 | 30.1 | 7.31 | The document contains a table on page 183 (image 0) titled "Annual Report on Intra-EU Labour Mobility – 2024 Edition". This table shows data for "Part-time empl | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |

## Qwen/Qwen3.5-2B (bf16), prompt without the NOT_FOUND sentence

`scripts/probe_vlm.py` at a7cf80e; revision unknown; max 1,600,000 pixels per page; load 12 s; weights 4.12 GB VRAM; greedy, max 128 new tokens.

| sample | input tokens | new tokens | seconds | peak VRAM GB | answer | reference |
|---|---:|---:|---:|---:|---|---|
| hr-q163 | 1623 | 6 | 3.3 | 4.50 | [1] | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |
| finance_en-q102 | 1644 | 11 | 2.1 | 4.51 | [13,784] | The gross liabilities for securities loaned or sold under agreements to repurchase that faced potential jurisdictional u |
| hr-q107 | 1622 | 128 | 16.3 | 4.50 | Based on the provided text, the long-term effects of labour market investments are described as leading to "both long-term economic gains and a catching-up of r | Labour market investments in skills lead to long-term economic gains and regional convergence by increasing labour produ |
| 3 pages | 4766 | 128 | 19.0 | 6.25 | Based on the table in the first image, the countries with the highest rates of part-time workers are:  - **CH (Switzerland)**: 12% (EU movers) and 10% (National | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |

## OpenGVLab/InternVL3_5-2B-HF (bf16), prompt without the NOT_FOUND sentence

`scripts/probe_vlm.py` at a7cf80e; revision unknown; max 1,600,000 pixels per page; load 12 s; weights 4.37 GB VRAM; greedy, max 128 new tokens.

| sample | input tokens | new tokens | seconds | peak VRAM GB | answer | reference |
|---|---:|---:|---:|---:|---|---|
| hr-q163 | 1861 | 77 | 10.7 | 5.20 | [p:4]  The countries in Europe that report the highest rates of part-time workers in 2024 are:  - EFTA: 11 part-time EU movers and 8 part-time nationals - CH: 1 | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |
| finance_en-q102 | 3394 | 128 | 15.4 | 6.59 | [p:3]  The securities financing agreements table presents securities financing agreements included on the Consolidated Balance Sheet in federal funds sold and s | The gross liabilities for securities loaned or sold under agreements to repurchase that faced potential jurisdictional u |
| hr-q107 | 1860 | 128 | 14.5 | 5.20 | [p:81]  The analysis confirms that ESF+ funded investments in skills can lead to both long-term economic gains and a catching-up of regions with initially low l | Labour market investments in skills lead to long-term economic gains and regional convergence by increasing labour produ |
| 3 pages | 7000 | 107 | 145.1 | 12.40 | [p:419]  According to the table on page 419, the countries with the highest rates of part-time workers in 2024 are:  - EFTA: 11 part-time employment for EU move | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |

## Qwen/Qwen3.5-4B (4-bit NF4), prompt without the NOT_FOUND sentence

`scripts/probe_vlm.py` at a7cf80e; revision unknown; max 1,600,000 pixels per page; load 33 s; weights 3.29 GB VRAM; greedy, max 128 new tokens.

| sample | input tokens | new tokens | seconds | peak VRAM GB | answer | reference |
|---|---:|---:|---:|---:|---|---|
| hr-q163 | 1623 | 128 | 25.8 | 3.99 | Based on the table provided in the image [p:183], we can identify the countries with the highest rates of part-time workers by looking at the "Part-time employm | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |
| finance_en-q102 | 1644 | 128 | 25.4 | 4.00 | Based on the provided document, there is no information about Citigroup or its securities financing transactions. The document is from the Bank of America (as i | The gross liabilities for securities loaned or sold under agreements to repurchase that faced potential jurisdictional u |
| hr-q107 | 1622 | 128 | 23.2 | 3.99 | Based on the provided text, here is the comparison of the long-term effects of labour market investments versus housing investments in reducing regional dispari | Labour market investments in skills lead to long-term economic gains and regional convergence by increasing labour produ |
| 3 pages | 4766 | 128 | 29.5 | 7.29 | The table on page 183 (image 0) shows data for "Part-time employment" for various Member States (MS) in 2024. The MS with the highest values for part-time emplo | In 2024, the countries in Europe reporting the highest rates of part-time workers among female EU movers are Switzerland |
