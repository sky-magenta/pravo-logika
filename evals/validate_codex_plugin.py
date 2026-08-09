#!/usr/bin/env python3
"""Проверяет, что Codex-пакет содержит обнаруживаемый скилл и его референсы."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / ".codex-plugin" / "plugin.json"
ROOT_SKILL_PATH = ROOT / "SKILL.md"
VERSION_PATTERN = re.compile(r"^version:\s*(.+?)\s*$", re.MULTILINE)


def check() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    plugin_name = manifest["name"]
    errors: list[str] = []

    if manifest.get("skills") != "./skills/":
        errors.append(".codex-plugin/plugin.json должен указывать skills: ./skills/")

    packaged_skill_path = ROOT / "skills" / plugin_name / "SKILL.md"
    if not packaged_skill_path.is_file():
        errors.append(f"не найден Codex-скилл: {packaged_skill_path.relative_to(ROOT)}")
    elif packaged_skill_path.read_bytes() != ROOT_SKILL_PATH.read_bytes():
        errors.append("Codex-копия SKILL.md расходится с корневым SKILL.md")

    source_references = ROOT / "references"
    packaged_references = ROOT / "skills" / plugin_name / "references"
    for source_path in source_references.rglob("*"):
        if source_path.is_file():
            relative_path = source_path.relative_to(source_references)
            packaged_path = packaged_references / relative_path
            if not packaged_path.is_file():
                errors.append(f"не скопирован референс: {relative_path}")
            elif packaged_path.read_bytes() != source_path.read_bytes():
                errors.append(f"Codex-копия референса расходится: {relative_path}")

    skill_version = VERSION_PATTERN.search(ROOT_SKILL_PATH.read_text(encoding="utf-8"))
    if skill_version is None:
        errors.append("в SKILL.md не найдена версия")
    else:
        expected_version = skill_version.group(1)
        for path in (
            ROOT / ".claude-plugin" / "plugin.json",
            MANIFEST_PATH,
            ROOT / ".cursor-plugin" / "plugin.json",
        ):
            version = json.loads(path.read_text(encoding="utf-8")).get("version")
            if version != expected_version:
                errors.append(f"версия в {path.relative_to(ROOT)} ({version}) не совпадает с SKILL.md ({expected_version})")

    return errors


if __name__ == "__main__":
    errors = check()
    if errors:
        print("ОШИБКИ:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: Codex-пакет содержит синхронизированный скилл и референсы.")
