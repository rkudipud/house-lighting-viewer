"""Record the exact R05 successor delta (room-centre 1050 mm fan, reported band heights, CBR re-analysis).

Writes cbr-r05-revision.json: every changed JSON path with its predecessor and successor value, so
validate_cbr_revision.py can rebuild the verified e7d2 predecessor from the current master and then
apply the original e7d2 checks unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path

from validate_cbr_revision import E7D2_SHA, canonical_sha, load_verified, r05_scope_violations

ABSENT = {"$absent": True}


def walk(a, b, path, out):
    if type(a) is not type(b):
        out.append({"path": path, "before": a, "after": b})
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append({"path": path + [k], "before": a.get(k, ABSENT), "after": b.get(k, ABSENT)})
            else:
                walk(a[k], b[k], path + [k], out)
    elif isinstance(a, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, path + [i], out)
    elif a != b:
        out.append({"path": path, "before": a, "after": b})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predecessor")
    parser.add_argument("successor")
    parser.add_argument("--out", default=str(Path(__file__).with_name("cbr-r05-revision.json")))
    args = parser.parse_args()
    before = load_verified(args.predecessor, E7D2_SHA)
    raw = Path(args.successor).read_bytes()
    after = json.loads(raw)
    ops = []
    walk(before, after, [], ops)
    violations = r05_scope_violations(before, after, ops)
    if violations:
        raise SystemExit(f"Out-of-scope R05 changes: {violations[:5]}")
    record = {
        "schema": "cbr-r05-revision/1",
        "predecessor_master_sha256": E7D2_SHA,
        "predecessor_canonical_sha256": canonical_sha(before),
        "successor_master_sha256": hashlib.sha256(raw).hexdigest(),
        "successor_canonical_sha256": canonical_sha(after),
        "basis": "Homeowner-directed R05 changes: fan at nominal room centre with a 1050 mm planning sweep "
                 "(product not selected), reported 3.048 m band / approx. 3.277 m raised centre (slab unmeasured), "
                 "and the CBR-only solver re-analysis with the retained cove and outward LINE modelled ON. "
                 "H-CBR-CEIL and all site, procurement and construction holds remain.",
        "operations": ops,
    }
    Path(args.out).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"operations": len(ops), "successor": record["successor_master_sha256"]}))


if __name__ == "__main__":
    main()
