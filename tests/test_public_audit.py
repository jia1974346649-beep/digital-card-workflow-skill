"""Public-package checks. All unsafe examples are assembled only in temporary files."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_public_package.py"
SPEC = importlib.util.spec_from_file_location("public_package_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class PublicPackageAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "public-manifest.json"
        self.write("README.md", "# Demonstration\nContact: person@example.com\n")
        self.allow("README.md", "public-manifest.json")

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def allow(self, *paths):
        self.manifest.write_text(json.dumps({"files": list(paths)}), encoding="utf-8")

    def audit(self, history=False, denied=()):
        return AUDIT.Auditor(self.root, self.manifest, denied).run(history)

    def categories(self, result):
        return {item["category"] for item in result["findings"]}

    def git(self, *arguments):
        completed = subprocess.run(
            ["git", "-C", str(self.root), *arguments], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(completed.returncode, 0, "Temporary Git operation failed")

    def initialize_git(self):
        if not shutil.which("git"):
            self.skipTest("Git is unavailable")
        self.git("init", "--quiet")
        self.git("config", "user.name", "Example Author")
        self.git("config", "user.email", "author@example.com")

    @staticmethod
    def private_email():
        return "person" + "@" + "not-public" + ".net"

    def test_safe_document_and_local_svg_pass(self):
        self.write("diagram.svg", '<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"/></defs><rect fill="url(#g)" width="20" height="20"/></svg>')
        self.allow("README.md", "diagram.svg", "public-manifest.json")
        self.assertTrue(self.audit()["ok"])

    def test_unlisted_file_fails(self):
        self.write("extra.md", "Unreviewed content")
        self.assertIn("unlisted-file", self.categories(self.audit()))

    def test_manifest_must_itself_be_listed(self):
        self.allow("README.md")
        self.assertIn("manifest-not-listed", self.categories(self.audit()))

    def test_traversal_in_manifest_fails(self):
        self.allow("README.md", "public-manifest.json", "../outside.md")
        self.assertIn("manifest-invalid", self.categories(self.audit()))

    def test_symbolic_link_fails(self):
        target = self.root / "linked.md"
        try:
            target.symlink_to(self.root / "README.md")
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable")
        self.allow("README.md", "linked.md", "public-manifest.json")
        self.assertIn("symbolic-link", self.categories(self.audit()))

    def test_sensitive_values_are_detected_without_disclosure(self):
        samples = {
            "email": self.private_email(),
            "phone-number": "138" + "2468" + "1357",
            "ip-address": ".".join(("198", "51", "100", "42")),
            "app-id": "w" + "x" + "a" * 16,
            "absolute-local-path": "C" + ":" + "/" + "Users" + "/" + "example" + "/notes",
            "long-identifier": "aB3_" * 10,
            "credential-assignment": "api" + "_key" + " = " + "not-a-placeholder",
            "private-key": "-----" + "BEGIN " + "PRIVATE KEY" + "-----",
        }
        for expected, value in samples.items():
            with self.subTest(category=expected):
                self.write("README.md", "Example\n" + value)
                result = self.audit()
                self.assertIn(expected, self.categories(result))
                self.assertNotIn(value, json.dumps(result))
                self.assertTrue(all(item["line"] >= 1 for item in result["findings"]))

    def test_generic_key_discussion_and_placeholders_pass(self):
        self.write("README.md", "An API key must be kept outside the package.\nAPI_KEY: <API_KEY>\n")
        self.assertTrue(self.audit()["ok"])

    def test_relative_skill_resource_path_is_safe(self):
        self.write("README.md", "See [skill](skills/card-product-workflow/SKILL.md).")
        self.assertTrue(self.audit()["ok"])

    def test_sensitive_value_inside_path_segment_is_rejected(self):
        value = "aB3_" * 10
        self.write("README.md", "See assets/" + value + "/diagram.svg")
        result = self.audit()
        self.assertIn("long-identifier", self.categories(result))
        self.assertNotIn(value, json.dumps(result))

    def test_nonstandard_external_url_is_rejected(self):
        self.write("README.md", "https" + "://" + "not-approved" + ".xyz/path")
        self.assertIn("unapproved-domain", self.categories(self.audit()))

    def test_denied_term_in_filename_is_redacted(self):
        term = "Internal" + "Company"
        filename = term + ".md"
        self.write(filename, "Example")
        self.allow("README.md", "public-manifest.json", filename)
        result = self.audit(denied=(term,))
        self.assertIn("denied-term", self.categories(result))
        self.assertNotIn(term, json.dumps(result))

    def test_binary_is_rejected_even_with_text_extension(self):
        (self.root / "README.md").write_bytes(bytes((0, 255, 1)))
        self.assertIn("binary-or-non-utf8", self.categories(self.audit()))

    def test_dotenv_and_archive_are_rejected(self):
        self.write(".env", "Nothing to publish")
        self.write("bundle.zip", "This extension remains forbidden even when textual")
        self.allow("README.md", "public-manifest.json", ".env", "bundle.zip")
        categories = self.categories(self.audit())
        self.assertIn("forbidden-file", categories)
        self.assertIn("unsupported-file-type", categories)

    def test_svg_external_image_and_active_content_fail(self):
        address = "https" + "://" + "outside" + ".invalid" + "/portrait.svg"
        self.write("diagram.svg", '<svg xmlns="http://www.w3.org/2000/svg"><image href="' + address + '"/><script>noop()</script></svg>')
        self.allow("README.md", "diagram.svg", "public-manifest.json")
        categories = self.categories(self.audit())
        self.assertIn("svg-external-reference", categories)
        self.assertIn("svg-active-or-image-content", categories)

    def test_staged_content_is_scanned_independently(self):
        self.initialize_git()
        self.write("README.md", self.private_email())
        self.git("add", "README.md", "public-manifest.json")
        self.write("README.md", "Clean current working copy")
        result = self.audit()
        self.assertIn("staged.email", self.categories(result))
        self.assertNotIn(self.private_email(), json.dumps(result))

    def test_staged_link_mode_is_rejected(self):
        self.initialize_git()
        object_result = subprocess.run(
            ["git", "-C", str(self.root), "hash-object", "-w", "--stdin"],
            input=b"README.md", stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(object_result.returncode, 0)
        object_id = object_result.stdout.decode("ascii").strip()
        self.git("update-index", "--add", "--cacheinfo", "120000," + object_id + ",linked.md")
        self.assertIn("staged.symbolic-link", self.categories(self.audit()))

    def test_deleted_history_content_is_still_rejected(self):
        self.initialize_git()
        self.write("README.md", self.private_email())
        self.git("add", "README.md", "public-manifest.json")
        self.git("commit", "--quiet", "-m", "Temporary initial example")
        self.write("README.md", "Clean replacement")
        self.git("add", "README.md")
        self.git("commit", "--quiet", "-m", "Temporary replacement")
        self.assertTrue(self.audit()["ok"])
        result = self.audit(history=True)
        self.assertIn("history.email", self.categories(result))
        self.assertNotIn(self.private_email(), json.dumps(result))

    def test_other_branch_history_is_checked(self):
        self.initialize_git()
        self.git("add", "README.md", "public-manifest.json")
        self.git("commit", "--quiet", "-m", "Temporary safe baseline")
        self.git("branch", "safe-base")
        self.write("README.md", self.private_email())
        self.git("add", "README.md")
        self.git("commit", "--quiet", "-m", "Temporary alternate branch example")
        self.git("branch", "unsafe-example")
        self.git("checkout", "--quiet", "safe-base")
        self.assertIn("history.email", self.categories(self.audit(history=True)))

    def test_ref_pointing_directly_to_blob_is_checked(self):
        self.initialize_git()
        result = subprocess.run(
            ["git", "-C", str(self.root), "hash-object", "-w", "--stdin"],
            input=self.private_email().encode("utf-8"), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.git("update-ref", "refs/tags/blob-example", result.stdout.decode("ascii").strip())
        categories = self.categories(self.audit(history=True))
        self.assertIn("history.unmapped-blob", categories)
        self.assertIn("history.email", categories)


if __name__ == "__main__":
    unittest.main()
