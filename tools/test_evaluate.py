"""Regression probes for coverage reduction, using disposable repository copies."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EvaluatorCoverageTests(unittest.TestCase):
    def test_smoke_replacement_rejected_before_and_after_inventory_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for name in ["snapshots", "acceptance", "fixtures", "experiments", "tools", "provenance"]:
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
            target = root / "results/018/phase23"
            target.mkdir(parents=True)
            shutil.copy(ROOT / "results/018/phase23/test_r1.py", target)
            for name in ["pyproject.toml", "uv.lock"]:
                shutil.copy(ROOT / name, root / name)
            changed = [root / "acceptance/test_014.py"]
            for role in ["luna", "sol"]:
                tests = root / f"snapshots/014/{role}/tests"
                for path in tests.glob("test_*.py"):
                    path.write_text("def test_smoke():\n    assert True\n")
                    changed.append(path)
            changed[0].write_text("def test_smoke():\n    assert True\n")
            command = [sys.executable, "-B", "-c",
                       "import sys; from pathlib import Path; sys.path.insert(0, sys.argv.pop(1)); "
                       "import evaluate; evaluate.ROOT=Path(sys.argv.pop(1)); "
                       "sys.exit(evaluate.main())",
                       str(ROOT / "tools"), str(root), "--experiment", "014"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Published evaluation inputs differ", result.stderr)
            self.assertFalse((root / "validation").exists())
            # Deliberately reseal tampered inputs: collection preservation must
            # independently reject reduced tests even if integrity is bypassed.
            inventory_path = root / "provenance/p1-publication-checksums.json"
            inventory = json.loads(inventory_path.read_text())
            for path in changed:
                inventory[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
            inventory_path.write_text(json.dumps(inventory))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn("Published evaluation inputs differ", result.stderr)
            report = json.loads(next((root / "validation").glob("*/report.json")).read_text())
            for candidate in report["candidates"].values():
                for suite in ["repository", "acceptance"]:
                    self.assertFalse(candidate["checks"][suite]["collection_matches_expected"])


    def test_missing_suite_and_modified_input_are_rejected(self):
        import evaluate

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for name in ["snapshots", "acceptance", "fixtures", "experiments", "tools", "provenance"]:
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
            target = root / "results/018/phase23"
            target.mkdir(parents=True)
            shutil.copy(ROOT / "results/018/phase23/test_r1.py", target)
            for name in ["pyproject.toml", "uv.lock"]:
                shutil.copy(ROOT / name, root / name)
            original_root = evaluate.ROOT
            evaluate.ROOT = root
            try:
                evaluate.verify_inputs()
                suite = root / "acceptance/test_014.py"
                saved = suite.read_bytes()
                suite.unlink()
                with self.assertRaisesRegex(ValueError, "acceptance/test_014.py"):
                    evaluate.verify_inputs()
                suite.write_bytes(saved)
                implementation = root / "snapshots/014/luna/problems/pair_counter.py"
                implementation.write_text(implementation.read_text() + "\n# unauthorized modification\n")
                with self.assertRaisesRegex(ValueError, "pair_counter.py"):
                    evaluate.verify_inputs()
            finally:
                evaluate.ROOT = original_root

    def test_environment_deselection_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = ROOT / "validation" / Path(temporary).name
            env = dict(os.environ, PYTEST_ADDOPTS="-k no_such_test_should_exist")
            result = subprocess.run(
                [sys.executable, "-B", str(ROOT / "tools/evaluate.py"),
                 "--experiment", "014", "--output", str(output)],
                env=env, capture_output=True, text=True,
            )
            try:
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads((output / "report.json").read_text())
                for candidate in report["candidates"].values():
                    for suite in ["repository", "acceptance"]:
                        self.assertFalse(candidate["checks"][suite]["collection_matches_expected"])
            finally:
                if output.exists():
                    shutil.rmtree(output)

    def test_013_equal_value_type_mutations_are_rejected(self):
        # Load the acceptance helper with a preserved implementation, then
        # mutate its output, leaving values equal under Python's == rules.
        import importlib.util

        sys.path.insert(0, str(ROOT / "snapshots/013/luna"))
        try:
            spec = importlib.util.spec_from_file_location("acceptance_013", ROOT / "acceptance/test_013.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            reference = module.DATA["cases"][0]["result"]
            module.assert_same_types(reference, reference)
            for replacement in [1.0, True]:
                mutated = json.loads(json.dumps(reference))
                mutated["lines"][0]["quantity"] = replacement
                self.assertEqual(mutated, reference)
                with self.assertRaises(AssertionError):
                    module.assert_same_types(mutated, reference)
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
