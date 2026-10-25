# Synthetic scan stress evaluation

Scope: four item scenarios, each rendered clean, with 1.5-degree skew and with 0.8-pixel Gaussian blur. Variants share source content. Results describe this small synthetic suite; independent real-document evaluation remains separate.

OCR receives only PDF bytes and a page number. Expected text, fields and decisions are used afterwards for scoring. One item is expected per page; zero or multiple extracted items cannot count as a correct unresolved decision. OCR item IDs are scored separately and remain unchanged.

CER uses NFKC, casefolding and collapsed whitespace while preserving Japanese and punctuation. Field comparison ignores whitespace after NFKC and casefolding. CER covers completed OCR runs; decision agreement includes every case, including execution failures.

| Condition | Completed | Decision agreement | Reason agreement | Incorrect resolved | CER |
|---|---:|---:|---:|---:|---:|
| clean | 4/4 | 3/4 | 3/4 | 0 | 5.7% |
| skew_1_5 | 4/4 | 3/4 | 1/4 | 0 | 5.5% |
| blur_0_8 | 4/4 | 4/4 | 4/4 | 0 | 5.0% |
| Overall | 12/12 | 10/12 | 8/12 | 0 | 5.4% |
