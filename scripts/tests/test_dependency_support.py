import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / "check_dependency_support.py"
spec = importlib.util.spec_from_file_location("check_dependency_support", path)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


class DependencySupportTests(unittest.TestCase):
    def test_lockfile_includes_direct_and_transitive_packages(self):
        lock = {
            "lockfileVersion": 3,
            "packages": {
                "": {},
                "node_modules/example": {"version": "1.0.0", "resolved": "https://registry.npmjs.org/example/-/example.tgz"},
                "node_modules/example/node_modules/@scope/child": {"version": "2.0.0", "resolved": "https://registry.npmjs.org/@scope/child/-/child.tgz"},
            },
        }
        self.assertEqual(support.npm_packages(lock), [("@scope/child", "2.0.0"), ("example", "1.0.0")])

    def test_unknown_lockfile_and_package_sources_fail(self):
        with self.assertRaises(ValueError):
            support.npm_packages({"lockfileVersion": 1})
        with self.assertRaises(ValueError):
            support.npm_packages({"lockfileVersion": 3, "packages": {
                "node_modules/example": {"version": "1.0.0", "resolved": "https://example.invalid/example.tgz"}
            }})

    def test_npm_registry_deprecation_and_exact_exception(self):
        with patch.object(support, "fetch_json", return_value={"name": "example", "version": "1.0.0", "deprecated": "unsupported"}):
            self.assertIn("unsupported", support.check_npm_package(("example", "1.0.0")))
        with patch.object(support, "fetch_json", return_value={"name": "eslint", "version": "9.39.5", "deprecated": "unsupported"}):
            self.assertIsNone(support.check_npm_package(("eslint", "9.39.5")))
        with patch.object(support, "fetch_json", return_value={"name": "eslint", "version": "9.39.4", "deprecated": "unsupported"}):
            self.assertIsNotNone(support.check_npm_package(("eslint", "9.39.4")))

    def test_registry_failure_and_bad_metadata_are_not_ignored(self):
        with patch.object(support, "fetch_json", side_effect=OSError("network unavailable")):
            with self.assertRaises(OSError):
                support.check_npm_package(("example", "1.0.0"))
        with patch.object(support, "fetch_json", return_value={}):
            with self.assertRaises(ValueError):
                support.check_python_package(("example", "1.0.0"))

    def test_pypi_inactive_and_yanked_releases(self):
        info = {"name": "Example", "version": "1.0.0", "classifiers": []}
        with patch.object(support, "fetch_json", return_value={"info": info, "urls": [{"yanked": True}]}):
            self.assertIn("yanked", support.check_python_package(("example", "1.0.0")))
        with patch.object(support, "fetch_json", return_value={"info": info, "urls": [{"yanked": False}, {"yanked": True}]}):
            self.assertIsNone(support.check_python_package(("example", "1.0.0")))
        info["classifiers"] = [support.INACTIVE_CLASSIFIER]
        with patch.object(support, "fetch_json", return_value={"info": info, "urls": [{"yanked": False}]}):
            self.assertIn("inactive", support.check_python_package(("example", "1.0.0")))

    def test_pypi_metadata_must_match_and_be_complete(self):
        base_info = {"name": "example", "version": "1.0.0", "classifiers": []}
        for info, urls in (
            ({**base_info, "name": "other"}, [{"yanked": False}]),
            ({**base_info, "version": "2.0.0"}, [{"yanked": False}]),
            (base_info, []),
            (base_info, [{}]),
            ({**base_info, "classifiers": None}, [{"yanked": False}]),
        ):
            with self.subTest(info=info, urls=urls), patch.object(
                support, "fetch_json", return_value={"info": info, "urls": urls}
            ):
                with self.assertRaises(ValueError):
                    support.check_python_package(("example", "1.0.0"))

    def test_runtime_eol_and_unknown_status_fail_closed(self):
        with patch.object(support, "fetch_json", return_value={"result": {
            "name": "24", "isEol": False, "isMaintained": True, "eolFrom": None
        }}):
            self.assertEqual(support.check_runtime("nodejs", "24.1.0"), 0)
        with patch.object(support, "fetch_json", return_value={"result": {
            "name": "24", "isEol": False, "isMaintained": True, "eolFrom": "2000-01-01"
        }}):
            self.assertEqual(support.check_runtime("nodejs", "24.1.0"), 1)
        with patch.object(support, "fetch_json", return_value={"result": {
            "name": "24", "isEol": False, "isMaintained": False, "eolFrom": None
        }}):
            self.assertEqual(support.check_runtime("nodejs", "24.1.0"), 1)
        with patch.object(support, "fetch_json", return_value={"result": {"name": "24", "isEol": None}}):
            with self.assertRaises(ValueError):
                support.check_runtime("nodejs", "24.1.0")
        self.assertEqual(support.runtime_cycle("terraform", "1.17.1"), "1.17")
        self.assertEqual(support.runtime_cycle("python", "3.11.18"), "3.11")

    def test_next_react_deprecated_combination(self):
        self.assertEqual(support.check_next_react("16.4.5", "18.3.1"), 1)
        self.assertEqual(support.check_next_react("16.4.5", "19.3.1"), 0)


if __name__ == "__main__":
    unittest.main()
