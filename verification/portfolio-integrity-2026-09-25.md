# Align discovery metadata with the current repository license

Date: 2026-09-25 UTC

Base commit: `a80840fd84b28a4d3c89edca61ebc53dec56a507`

The current LICENSE and LICENSE_BOUNDARY.md declare MPL-2.0, while package metadata or the public discovery generator still declared Apache-2.0. This repair aligns current metadata and its admission checks with the existing repository declaration, then regenerates the exact discovery receipt.

No LICENSE text, historical snapshot, third-party notice, donor source, runtime capability, execution authority or CANON state is changed. Historical license grants remain historical evidence.

## Verification

`PYTHONPATH=src:. python -m unittest discover -s tests -v`: 129 tests passed. The suite rewrites the tracked example pyramid while running; that test-generated example was restored and is excluded from the change.
