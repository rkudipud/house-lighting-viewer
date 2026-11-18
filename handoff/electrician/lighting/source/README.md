# Lighting exporter source snapshots

These are the current export script, verification script and workbench template,
not a repository-portable build or a new photometric solver. Master integration
and cleanup tools are intentionally excluded. The runnable review workbench and
editable lighting data are in the parent directory.

The original producer reran this exporter in a new session-local directory and
verified 45 artifact hashes and 65 review checks. That evidence does not establish
portability of these public copies. Session-specific default paths are replaced
by repository-relative references or `not-distributed/` source labels; original
and delivered hashes are in `repository-copy-receipt.json`.

The scripts use Python, Matplotlib, NumPy, PyMuPDF and Playwright with a supported
Chromium/Edge installation. They also depend on original optical-input and
verification packs, a prior K2 source image, criteria evidence, guarded canonical
bytes and session layout that are not reproduced here. Redacting the public
canonical copy changes its byte hash, so it cannot satisfy the unmodified
canonical-byte guard. Default paths must not be interpreted as a working build
configuration. Review and explicitly adapt the dependencies in an isolated copy
before execution; repository-portable export/verification has not been tested.

The HTML file here is an input template, not an independently runnable page.
Use `../lighting-workbench.html` for the offline viewer. Heatmap data are inherited
analytic estimates; no measured or physically validated simulation, new optical
run, selected-curtain lux credit or construction approval is claimed.
