"""Create a path-redacted public copy of the current canonical master."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "electrician" / "lighting" / "source"))
from validate_cbr_revision import PRIOR_SHA, CURRENT_SHA, load_verified, verify


ABS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
EMBEDDED_PATH = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_replacement(value):
    if "attachments" in value.lower() or "whatsapp" in value.lower():
        return "[private source file, not published]"
    return re.split(r"[\\/]", value.rstrip("\\/"))[-1]


def collect_path_map(source, public, path="", mapping=None):
    mapping = {} if mapping is None else mapping
    if isinstance(source, dict) and isinstance(public, dict):
        if set(source) != set(public):
            raise ValueError(f"Prior public-copy fields differ at {path}")
        for key in source:
            collect_path_map(source[key], public[key], f"{path}/{key}", mapping)
    elif isinstance(source, list) and isinstance(public, list):
        if len(source) != len(public):
            raise ValueError(f"Prior public-copy arrays differ at {path}")
        for i, (a, b) in enumerate(zip(source, public)):
            collect_path_map(a, b, f"{path}/{i}", mapping)
    elif source != public:
        if not isinstance(source, str) or not (ABS_PATH.match(source)
                or public == "[private source path, not published]"):
            raise ValueError(f"Prior public-copy difference is not a local path at {path}")
        if not isinstance(public, str) or ABS_PATH.match(public):
            raise ValueError(f"Unexpected prior path redaction at {path}")
        mapping[path] = (source, public)
    return mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-master", required=True, type=Path)
    parser.add_argument("--master", required=True, type=Path)
    parser.add_argument("--prior-public", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    prior = load_verified(args.prior_master, PRIOR_SHA)
    current = load_verified(args.master, CURRENT_SHA)
    verify(prior, current)
    prior_public = json.loads(args.prior_public.read_text(encoding="utf-8"))
    path_map = collect_path_map(prior, prior_public)

    def transform(value, path=""):
        if isinstance(value, dict):
            return {k: transform(v, f"{path}/{k}") for k, v in value.items()}
        if isinstance(value, list):
            return [transform(v, f"{path}/{i}") for i, v in enumerate(value)]
        previous = path_map.get(path)
        if previous and value == previous[0]:
            return previous[1]
        if isinstance(value, str) and EMBEDDED_PATH.search(value):
            if ABS_PATH.match(value):
                return path_replacement(value)
            return "[private source path, not published]"
        return value

    public = transform(current)
    raw = json.dumps(public, ensure_ascii=False, indent=2) + "\n"
    if re.search(r"(?i)(?:(?<![A-Z])[A-Z]:[\\/]|file://|\.copilot[\\/]|session-state[\\/]|attachments[\\/])", raw):
        raise ValueError("Private path remains in the staged master")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(raw, encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": "PASS",
        "source_master_sha256": sha(args.master),
        "public_master_sha256": sha(args.out),
        "bytes": args.out.stat().st_size,
        "local_paths_redacted": True,
    }, indent=2))


if __name__ == "__main__":
    main()
