# Strata — Material Reference Matching

## Objective

Connect extracted text to traceable manufacturer reference records and explain each decision.

## Reference data

The prototype uses two manually curated Nichiha product-family records. Each contains product names, manufacturer aliases, a supported manufacturing period, a reference status and source URLs.

## Matching workflow

1. Normalize Unicode character width, letter case and whitespace.
2. Find an exact product name or known alias.
3. Check the manufacturer.
4. Validate the manufacturing month against the reference period and review date.
5. Return the matched reference status and evidence links, or an unresolved result with a reason.

For unmatched product names, character similarity can retrieve review candidates. Suggestions preserve the original query and unresolved decision.

The initial suggestion threshold is 0.85. Similarity scores are not probabilities of product identity.

## Validation

Five automated test methods passed. They cover supported matches, character normalization, date boundaries, missing information, manufacturer mismatches, conflicting records and suggestion safeguards.

Four synthetic queries produced:

- One asbestos-containing reference match.
- One non-asbestos-containing reference match.
- Two unresolved results, including one with a review suggestion.

Five OCR-derived generic material mentions from the historical drawing all remained unresolved.

## Traceability

Batch reports retain input provenance, original query fields, decision reasons, candidate identifiers and evidence links. A SHA-256 fingerprint identifies the reference catalogue used.

## Limitations

These results validate prototype behaviour, not real-world classification accuracy. The catalogue contains only two product families. The current drawing extraction supplies generic material words rather than specific product identities.

## What I learned

OCR confidence, product-name similarity and reference evidence describe different things. Missing product information must remain visible. Tests should check ambiguous and incomplete inputs as well as successful matches.

## Next step

Build a review interface for inspecting OCR context, entering verified product details, viewing suggestions and rerunning reference matching with an edit history.