import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "validate_marketplace.py"
SPEC = importlib.util.spec_from_file_location("validate_marketplace", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MarketplaceValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "README.md").write_text("# Test marketplace\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_manifest(self, skills):
        (self.root / "marketplace.json").write_text(
            json.dumps({"skills": skills}), encoding="utf-8"
        )

    def add_skill(self, skill_id="audit-orchestrator", path="skills/audit-orchestrator",
                  frontmatter="name: audit-orchestrator\ndescription: Main audit entrypoint"):
        skill_dir = self.root / path
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\n{frontmatter}\n---\n\n# Skill\n", encoding="utf-8"
        )
        return {"id": skill_id, "path": path, "entrypoint": skill_id == "audit-orchestrator"}

    def validate_quietly(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return MODULE.validate_marketplace(str(self.root))

    def test_accepts_a_valid_manifest_and_skill(self):
        skill = self.add_skill()
        self.write_manifest([skill])
        self.assertTrue(self.validate_quietly())

    def test_rejects_duplicate_skill_ids(self):
        first = self.add_skill()
        second = dict(first)
        second["path"] = "skills/duplicate"
        second["entrypoint"] = False
        self.add_skill(skill_id="duplicate", path="skills/duplicate")
        self.write_manifest([first, second])
        self.assertFalse(self.validate_quietly())

    def test_rejects_parent_directory_traversal(self):
        skill = {
            "id": "audit-orchestrator",
            "path": "../audit-orchestrator",
            "entrypoint": True,
        }
        self.write_manifest([skill])
        self.assertFalse(self.validate_quietly())

    def test_rejects_non_mapping_frontmatter(self):
        skill = self.add_skill(frontmatter="[]")
        self.write_manifest([skill])
        self.assertFalse(self.validate_quietly())


if __name__ == "__main__":
    unittest.main()
