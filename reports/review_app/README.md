# Strata material review application

## Purpose

The application connects saved OCR material mentions and synthetic
product queries to a manufacturer-reference matching workflow.

## Implemented workflow

1. Select a real drawing annotation or a clearly labelled synthetic query.
2. Inspect the original text, drawing location and saved decision.
3. Enter reviewed product details with a reviewer name and evidence note.
4. Run reference matching on the submitted details.
5. Save the submission and inspect or download its history.

## Evidence preservation

Reviews preserve the original record alongside the submitted query.
Each submission includes a unique review ID, UTC timestamp, reviewer
name, evidence note, matching result and reference catalogue fingerprint.

Original OCR reports are not overwritten.

## Verified example

A synthetic query using モエンサイディング-M, manufacturer Nichiha,
and manufacture month 1995-08 matched nichiha-moen-m and returned
non_asbestos_containing.

The original saved decision remained unchanged, and one review
submission was recorded.

## Storage and limitations

Review history uses a SQLite database in data/reviews/.
It persists across app restarts in the same Codespace and can be
exported as JSON.

Reviewer names are self-reported. The prototype does not yet provide
authentication or tamper-proof audit records.

Results describe manufacturer-reference matching for supplied details.
They do not establish the asbestos content of a physical building.

The catalogue currently contains two curated manufacturer records.