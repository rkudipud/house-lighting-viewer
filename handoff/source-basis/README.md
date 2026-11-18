# Coordinated review source basis

This is editable review data, not a construction release. The source canonical
master SHA-256 is `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`.
The provisional wardrobe reference is registered for coordination, not fabrication.

The public-safe master copy redacts local absolute source paths. It therefore
has a different byte hash from the canonical original; both hashes are recorded
in `repository-copy-receipt.json`. Geometry, dimensions, decisions and holds are
not changed by this path-only transformation. `public-file-hashes.json` verifies
the delivered data; the selected-source manifest records original source hashes.

Repository-relative source references identify the intended handoff locations.
Not every historical source/audit attachment is distributed. In particular,
retired plans, prior geometry, unlicensed third-party renders and manufacturer
catalogue files are not included. `not-distributed/` values are source labels,
not downloadable files. Use the trade navigation for the active reading set.

`generated/wardrobe-interiors-provenance-correction.json` accompanies the original
reference receipt. An intermediate lighting manifest was overwritten and its
original bytes are unavailable. Independent rollback/current-master comparison
supports compatibility, not recovery or verification of that missing manifest.

Pack generators that accept a file hash must be given the delivered file's hash
when run against this path-redacted copy. Do not claim that regenerating against
the public copy reproduces the original canonical byte hash or grants approval.
