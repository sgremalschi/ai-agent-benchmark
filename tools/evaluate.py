#!/usr/bin/env python3
"""Evaluate preserved candidates locally; never invokes an AI service."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "008": "problem_0056_merge_intervals",
    "009": "ttl_cache",
    "010": "ttl_cache",
    "011": "bounded_task_queue",
    "012": "rate_limiter",
    "013": "order_processor",
    "014": "pair_counter",
    "015": "job_scheduler",
    "016": "inventory",
    "017": "order_system",
    "018": "job_scheduler",
}


def hashes(path):
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


def normalize(text, candidate):
    for source, replacement in [(str(candidate), "<candidate>"), (str(ROOT), "<repo>")]:
        text = text.replace(source, replacement)
    return text


def run(command, cwd, env):
    start = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=60)
        data = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired as exc:
        data = {"returncode": None, "stdout": exc.stdout or "", "stderr": exc.stderr or ""}
    data["seconds"] = round(time.monotonic() - start, 4)
    for key in ["stdout", "stderr"]:
        if isinstance(data[key], bytes):
            data[key] = data[key].decode(errors="replace")
        data[key] = normalize(data[key], cwd)
    return data


def expected_failures(exp, role, suite):
    if suite == "interruption" and role in ["luna", "luna-original", "luna-repaired"]:
        return [
            "test_interrupted_batch_preserves_unstarted_jobs[KeyboardInterrupt]",
            "test_interrupted_batch_preserves_unstarted_jobs[SystemExit]",
        ]
    if exp == "018" and role == "luna-original" and suite == "r1":
        return ["test_jobs_scheduled_during_clock_read_wait_for_next_invocation"]
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", choices=MODULES, help="Default: all preserved experiments")
    parser.add_argument("--output", type=Path, help="New directory; never overwrites existing results")
    args = parser.parse_args()
    out = args.output or ROOT / "validation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = out.resolve()
    if not out.is_relative_to(ROOT / "validation"):
        parser.error("--output must be a new directory under validation/")
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {
        "evidence_class": "newly_executed_publication_validation",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "pytest": importlib.metadata.version("pytest"),
            "ruff": importlib.metadata.version("ruff"),
        },
        "model_experiments_launched": 0,
        "candidates": {},
    }
    experiments = [args.experiment] if args.experiment else list(MODULES)
    before = hashes(ROOT / "snapshots")
    for exp in experiments:
        roles = {"luna": f"snapshots/{exp}/luna", "sol": f"snapshots/{exp}/sol"}
        if exp == "018":
            roles = {
                "luna-original": "snapshots/015/luna",
                "sol-original": "snapshots/015/sol",
                "luna-repaired": "snapshots/018/repaired-luna",
            }
        for role, source in roles.items():
            key = f"{exp}/{role}"
            with tempfile.TemporaryDirectory(prefix="benchmark-eval-") as temporary:
                candidate = Path(temporary).resolve() / "candidate"
                shutil.copytree(ROOT / source, candidate)
                env = {
                    k: v
                    for k, v in os.environ.items()
                    if not any(s in k.upper() for s in ["TOKEN", "SECRET", "API_KEY", "CODEX", "OPENAI"])
                }
                env.update(
                    PYTHONPATH=str(candidate), PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
                )
                suites = {"repository": candidate / "tests"}
                if (ROOT / f"acceptance/test_{exp}.py").exists():
                    suites["acceptance"] = ROOT / f"acceptance/test_{exp}.py"
                if exp == "018":
                    suites["acceptance"] = ROOT / "acceptance/test_015.py"
                if exp in ["015", "018"]:
                    suites["interruption"] = ROOT / "acceptance/test_015_interrupt.py"
                if exp == "018":
                    suites["r1"] = ROOT / "results/018/phase23/test_r1.py"
                checks = {}
                for suite, testfile in suites.items():
                    xml = out / f"{exp}-{role}-{suite}.xml"
                    module = "problems." + MODULES[exp]
                    expected_path = candidate / "problems" / (MODULES[exp] + ".py")
                    if exp == "017":
                        expected_path = candidate / "problems/order_system/__init__.py"
                    code = (
                        "import importlib,os,sys; m=importlib.import_module(sys.argv.pop(1)); "
                        "assert os.path.realpath(m.__file__)==os.path.realpath(sys.argv.pop(1)),m.__file__; "
                        "import pytest; sys.exit(pytest.main(sys.argv[1:]))"
                    )
                    command = [
                        sys.executable,
                        "-B",
                        "-c",
                        code,
                        module,
                        str(expected_path),
                        "-c",
                        str(candidate / "pyproject.toml"),
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        "--junitxml=" + str(xml),
                        str(testfile),
                    ]
                    data = run(command, candidate, env)
                    if xml.exists():
                        tree = ET.fromstring(xml.read_text())
                        # Normalize parsed XML values, then serialize with escaping.
                        # Failure tracebacks contain filenames inside attributes/text.
                        for node in tree.iter():
                            node.attrib.update({k: normalize(v, candidate) for k, v in node.attrib.items()})
                            if node.text:
                                node.text = normalize(node.text, candidate)
                            if node.tail:
                                node.tail = normalize(node.tail, candidate)
                        # JUnit hostname is unnecessary identifying machine metadata.
                        for node in tree.iter("testsuite"):
                            node.attrib.pop("hostname", None)
                        xml.write_text(ET.tostring(tree, encoding="unicode") + "\n")
                        cases = list(tree.iter("testcase"))
                        failed = sorted(t.attrib["name"] for t in cases if t.find("failure") is not None)
                        errors = sum(t.find("error") is not None for t in cases)
                        skipped = sum(t.find("skipped") is not None for t in cases)
                        data["counts"] = {
                            "total": len(cases),
                            "passed": len(cases) - len(failed) - errors - skipped,
                            "failed": len(failed),
                            "errors": errors,
                            "skipped": skipped,
                        }
                        data["failure_names"] = failed
                        wanted = sorted(expected_failures(exp, role, suite))
                        data["expected_failure_names"] = wanted
                        data["matches_documented_outcome"] = (
                            failed == wanted
                            and errors == 0
                            and skipped == 0
                            and bool(cases)
                            and data["returncode"] == (1 if wanted else 0)
                        )
                    else:
                        data["matches_documented_outcome"] = False
                    checks[suite] = data
                if "acceptance" not in suites:
                    checks["acceptance"] = {
                        "status": "unavailable",
                        "reason": "No preserved independent suite; repository tests are not independent.",
                    }
                module_path = "problems/" + MODULES[exp] + ("" if exp == "017" else ".py")
                test_path = (
                    "tests/test_problem_0056_merge_intervals.py"
                    if exp == "008"
                    else "tests/test_" + MODULES[exp] + ".py"
                )
                for scope, paths in [("scoped_ruff", [module_path, test_path]), ("repository_ruff", ["."])]:
                    data = run(
                        [
                            sys.executable,
                            "-m",
                            "ruff",
                            "check",
                            "--no-cache",
                            "--output-format",
                            "json",
                            *paths,
                        ],
                        candidate,
                        env,
                    )
                    try:
                        diagnostics = json.loads(data["stdout"])
                    except json.JSONDecodeError:
                        diagnostics = None
                    wanted = (
                        [("I001", "problems/order_processor.py")]
                        if scope == "repository_ruff" and int(exp) >= 14
                        else []
                    )
                    observed = (
                        [(d["code"], d["filename"].removeprefix("<candidate>/")) for d in diagnostics]
                        if isinstance(diagnostics, list)
                        else None
                    )
                    data["expected_diagnostics"] = wanted
                    data["matches_documented_outcome"] = observed == wanted and data["returncode"] == (
                        1 if wanted else 0
                    )
                    checks[scope] = data
                report["candidates"][key] = {"snapshot": source, "checks": checks}
                print(
                    key
                    + ": "
                    + ", ".join(
                        f"{s}={d.get('counts', {}).get('passed', d.get('returncode', d.get('status')))}"
                        for s, d in checks.items()
                    ),
                    flush=True,
                )
    report["snapshots_unchanged"] = before == hashes(ROOT / "snapshots")
    unexpected = [
        f"{name}:{suite}"
        for name, candidate in report["candidates"].items()
        for suite, check in candidate["checks"].items()
        if check.get("matches_documented_outcome") is False
    ]
    report.update(
        ended_utc=datetime.now(timezone.utc).isoformat(),
        seconds=round(time.monotonic() - started, 4),
        unexpected_outcomes=unexpected,
    )
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "summary.md").write_text(summary(report))
    print(f"Report: {out.relative_to(ROOT)}/report.json; unexpected outcomes: {len(unexpected)}")
    return 0 if not unexpected and report["snapshots_unchanged"] else 1


def summary(report):
    lines = [
        "# Newly executed publication validation",
        "",
        "These are fresh local checks, not reconstructed historical measurements.",
        "",
        "| Candidate | Repository | Acceptance | Interruption | R1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, data in report["candidates"].items():
        cells = []
        for suite in ["repository", "acceptance", "interruption", "r1"]:
            check = data["checks"].get(suite, {})
            c = check.get("counts")
            cells.append(f"{c['passed']}/{c['total']}" if c else check.get("status", "—"))
        lines.append("| " + " | ".join([name, *cells]) + " |")
    lines += [
        "",
        "Unexpected outcomes: " + str(len(report["unexpected_outcomes"])),
        "Snapshots unchanged: " + str(report["snapshots_unchanged"]),
        "See report.json for lint diagnostics, known failures, runtime versions and timing.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
