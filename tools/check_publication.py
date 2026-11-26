#!/usr/bin/env python3
"""Check public evidence, privacy patterns, documentation links, and checksums."""

import argparse
import hashlib
import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".venv", ".cache", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".private-research"}
INVENTORY = "provenance/p1-publication-checksums.json"
REPORT = "provenance/p1-publication-checks.json"
SECRET = re.compile(
    r'(?i)(?:sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|'
    r'AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|'
    r'Bearer\s+[A-Za-z0-9_.-]{20,}|'
    r'"(?:access_token|refresh_token|id_token|OPENAI_API_KEY)"\s*:\s*"[^"\s]{8,}")'
)
EMAIL = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files():
    return [
        p
        for p in sorted(ROOT.rglob("*"))
        if p.is_file() and not any(part in SKIP for part in p.relative_to(ROOT).parts)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-checksums",
        action="store_true",
        help="After successful content checks, update the current publication inventory",
    )
    args = parser.parse_args()
    # Bootstrap generated metadata targets before checking documentation links.
    if args.refresh_checksums:
        for name in [INVENTORY, REPORT]:
            path = ROOT / name
            if not path.exists():
                path.write_text("{}\n")
    findings, archive_count, raw_log_count, link_count = [], 0, 0, 0
    checked = files()

    def scan(label, data):
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            findings.append({"path": label, "issue": "unexpected_nontext_file"})
            return
        categories = []
        if SECRET.search(text):
            categories.append("credential_pattern")
        # Recognize the actual local account without embedding its identity.
        account = Path.home().name
        if account not in ["USER", "root"] and re.search(
            r"(?<![A-Za-z])" + re.escape(account) + r"(?![A-Za-z])", text
        ):
            categories.append("local_account_name")
        homes = re.findall(r"/Users/([A-Za-z0-9_.-]+)", text)
        if any(p not in ["USER", "AGENTS.md"] for p in homes):
            categories.append("personal_home_path")
        if re.search(r"/(?:private/)?var/folders/(?!REDACTED)", text):
            categories.append("personal_temp_path")
        if any(x != "redacted@example.invalid" for x in EMAIL.findall(text)):
            categories.append("unredacted_email")
        if re.search(r'"(?:thread_id|session_id)"\s*:\s*"(?!REDACTED_SESSION_)[^"]+"', text):
            categories.append("unredacted_session_identifier")
        for category in categories:
            findings.append({"path": label, "issue": category})

    for path in checked:
        rel = str(path.relative_to(ROOT))
        if path.is_symlink():
            findings.append({"path": rel, "issue": "symlink"})
        if path.name in ["auth.json", ".env", "credentials.json"]:
            findings.append({"path": rel, "issue": "credential_filename"})
        if (ROOT / "provenance/RELEASE_EXCLUSIONS.json").exists() and path.suffix in [
            ".log", ".jsonl", ".tar"
        ]:
            findings.append({"path": rel, "issue": "excluded_raw_log_or_archive_present"})
        if path.suffix == ".tar":
            with tarfile.open(path) as archive:
                for member in archive.getmembers():
                    if (
                        member.issym()
                        or member.islnk()
                        or Path(member.name).is_absolute()
                        or ".." in Path(member.name).parts
                    ):
                        findings.append({"path": rel, "issue": "unsafe_archive_member"})
                    if member.isfile():
                        archive_count += 1
                        if member.uid or member.gid or member.uname or member.gname:
                            findings.append({"path": rel, "issue": "archive_owner_metadata"})
                        scan(rel + "!" + member.name, archive.extractfile(member).read())
            continue
        data = path.read_bytes()
        scan(rel, data)
        text = data.decode(errors="replace")
        if path.suffix == ".xml" and re.search(r' hostname="[^"]+"', text):
            findings.append({"path": rel, "issue": "identifying_junit_hostname"})
        if path.suffix in [".json", ".jsonl"]:
            try:
                if path.suffix == ".json":
                    json.loads(text)
                else:
                    for line in text.splitlines():
                        if line.strip():
                            json.loads(line)
            except json.JSONDecodeError:
                findings.append({"path": rel, "issue": "invalid_structured_file"})
        if path.name.endswith(".agent.stdout.log") or path.name in [
            "review.stdout.jsonl",
            "repair.stdout.jsonl",
        ]:
            raw_log_count += 1
            try:
                for line in text.splitlines():
                    if line.strip():
                        json.loads(line)
            except json.JSONDecodeError:
                findings.append({"path": rel, "issue": "invalid_agent_jsonl"})
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = target.strip("<>")
                parts = urlsplit(target)
                if parts.scheme or not parts.path:
                    continue
                link_count += 1
                if not (path.parent / unquote(parts.path)).exists():
                    findings.append({"path": rel, "issue": "broken_documentation_link", "target": target})
    manifest = json.loads((ROOT / "provenance/manifest.json").read_text())
    exclusion_file = ROOT / "provenance/RELEASE_EXCLUSIONS.json"
    if exclusion_file.exists():
        exclusions = json.loads(exclusion_file.read_text())
        for entry in exclusions["excluded_files"]:
            if (ROOT / entry["path"]).exists():
                findings.append({"path": entry["path"], "issue": "release_excluded_file_present"})
    lineage_paths = [s["path"] for s in manifest["snapshots"]]
    physical_paths = {
        str(p.relative_to(ROOT))
        for experiment in (ROOT / "snapshots").iterdir()
        if experiment.is_dir()
        for p in experiment.iterdir()
        if p.is_dir()
    }
    if len(lineage_paths) != len(set(lineage_paths)) or set(lineage_paths) != physical_paths:
        findings.append({"path": "provenance/manifest.json", "issue": "snapshot_lineage_mismatch"})
    archives = {}
    for artifact in manifest["artifacts"]:
        name = artifact["published_path"]
        if "!" in name:
            archive_name, member = name.split("!", 1)
            if archive_name not in archives:
                with tarfile.open(ROOT / archive_name) as archive:
                    archives[archive_name] = {
                        m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()
                    }
            data = archives[archive_name].get(member)
        else:
            path = ROOT / name
            data = path.read_bytes() if path.is_file() else None
        if data is None or sha(data) != artifact["published_sha256"]:
            findings.append({"path": name, "issue": "historical_provenance_checksum_mismatch"})
    inventory = {
        str(p.relative_to(ROOT)): sha(p.read_bytes())
        for p in checked
        if str(p.relative_to(ROOT)) not in [INVENTORY, REPORT]
    }
    if args.refresh_checksums and not findings:
        (ROOT / INVENTORY).write_text(json.dumps(inventory, indent=2) + "\n")
    inventory_file = ROOT / INVENTORY
    if inventory_file.exists():
        recorded = json.loads(inventory_file.read_text())
        if recorded != inventory:
            findings.append({"path": INVENTORY, "issue": "current_inventory_mismatch"})
    else:
        findings.append({"path": INVENTORY, "issue": "current_inventory_missing"})
    report = {
        "evidence_class": "newly_executed_publication_validation",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "public_files_scanned": len(checked),
        "archive_members_scanned": archive_count,
        "raw_agent_stdout_logs_scanned": raw_log_count,
        "local_documentation_links_checked": link_count,
        "historical_provenance_records_checked": len(manifest["artifacts"]),
        "current_inventory_entries": len(inventory),
        "findings": findings,
        "snapshot_lineages_checked": len(lineage_paths),
        "limitations": [
            "Pattern scanning does not prove absence of every private detail.",
            "System runtime paths and public package registry URLs are retained in historical evidence.",
            "The inventory excludes itself and this changing check report.",
            "These checks do not establish editorial quality, legal clearance or full correctness.",
        ],
    }
    (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
