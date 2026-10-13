"""Validate marketplace metadata and skill packages before distribution."""
import json
import os
import re
import sys

import yaml


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_marketplace(root_dir):
    root_dir = os.path.realpath(root_dir)
    manifest_path = os.path.join(root_dir, "marketplace.json")
    if not os.path.isfile(manifest_path):
        return fail("marketplace.json not found.")

    try:
        with open(manifest_path, encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"marketplace.json could not be read as valid JSON: {exc}")

    skills = manifest.get("skills") if isinstance(manifest, dict) else None
    if not isinstance(skills, list) or not skills:
        return fail("marketplace.json must contain a non-empty 'skills' list.")

    entrypoints = [
        skill for skill in skills
        if isinstance(skill, dict) and skill.get("entrypoint") is True
    ]
    if len(entrypoints) != 1:
        return fail(f"Expected exactly 1 entrypoint, found {len(entrypoints)}.")
    if entrypoints[0].get("id") != "audit-orchestrator":
        print("WARNING: Entrypoint is not 'audit-orchestrator'; verify this is intentional.")

    seen_ids = set()
    seen_paths = set()
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            return fail(f"Skill at index {index} must be a JSON object.")

        skill_id = skill.get("id")
        path = skill.get("path")
        if not isinstance(skill_id, str) or not skill_id.strip():
            return fail(f"Skill at index {index} must have a non-empty string 'id'.")
        if skill_id in seen_ids:
            return fail(f"Duplicate skill id: {skill_id}.")
        seen_ids.add(skill_id)

        if not isinstance(path, str) or not path.strip():
            return fail(f"Skill {skill_id} must have a non-empty string 'path'.")

        # Normalize both separator styles before checking path traversal.
        normalized_path = path.replace("\\", "/")
        path_parts = normalized_path.split("/")
        if normalized_path.startswith("/") or any(part == ".." for part in path_parts):
            return fail(f"Skill path must stay inside the repository: {path!r}.")
        if path in seen_paths:
            return fail(f"Duplicate skill path: {path}.")
        seen_paths.add(path)

        if not normalized_path.rstrip("/").endswith(skill_id):
            return fail(f"Skill path {path} does not match skill id {skill_id}.")

        skill_dir = os.path.realpath(os.path.join(root_dir, *path_parts))
        if os.path.commonpath([root_dir, skill_dir]) != root_dir:
            return fail(f"Skill path resolves outside the repository: {path!r}.")
        if not os.path.isdir(skill_dir):
            return fail(f"Skill directory not found at {path}.")

        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            return fail(f"SKILL.md missing in {path}.")

        try:
            with open(skill_md, encoding="utf-8") as stream:
                content = stream.read()
        except OSError as exc:
            return fail(f"Cannot read {skill_md}: {exc}")

        match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.DOTALL)
        if not match:
            return fail(f"SKILL.md in {path} has malformed YAML frontmatter.")

        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            return fail(f"SKILL.md in {path} has invalid YAML frontmatter: {exc}")

        if not isinstance(frontmatter, dict):
            return fail(f"SKILL.md in {path} frontmatter must be a YAML mapping.")
        for required in ("name", "description"):
            value = frontmatter.get(required)
            if not isinstance(value, str) or not value.strip():
                return fail(
                    f"SKILL.md in {path} frontmatter must contain a non-empty '{required}'."
                )

    if not os.path.isfile(os.path.join(root_dir, "README.md")):
        return fail("README.md not found at repository root.")

    print(f"SUCCESS: Marketplace validation passed ({len(skills)} skills checked).")
    return True


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return 0 if validate_marketplace(root_dir) else 1


if __name__ == "__main__":
    sys.exit(main())
