#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Офлайн-проверка набора cases.jsonl — структура, уникальность, покрытие.

Не требует ни ключа API, ни сети. Годится для CI и как pytest-тест.

    python validate_cases.py            # печатает отчёт, exit!=0 при ошибке
    pytest evals/validate_cases.py      # те же проверки как тест
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_PATH = os.path.join(HERE, "cases.jsonl")

MODES = {"review", "clause-check", "fix"}
EXPECTS = {"defect", "clean"}
DIFFICULTIES = {"easy", "medium", "hard"}
REQUIRED = {"id", "mode", "category", "difficulty", "input", "expect"}
# Разделы каталога дефектов, которые набор обязан покрывать.
REQUIRED_SECTIONS = {"A", "B", "C", "D", "E", "F", "K", "N", "X"}


def load_cases(path=CASES_PATH):
    cases = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise AssertionError(f"строка {i}: невалидный JSON: {e}")
    return cases


def check(cases):
    """Возвращает список строк-ошибок (пустой = всё в порядке)."""
    errors = []
    ids = set()
    for c in cases:
        cid = c.get("id", "<no-id>")
        missing = REQUIRED - set(c)
        if missing:
            errors.append(f"{cid}: нет полей {sorted(missing)}")
        if c.get("id") in ids:
            errors.append(f"{cid}: дублирующийся id")
        ids.add(c.get("id"))
        if c.get("mode") not in MODES:
            errors.append(f"{cid}: mode={c.get('mode')!r} не из {MODES}")
        if c.get("expect") not in EXPECTS:
            errors.append(f"{cid}: expect={c.get('expect')!r} не из {EXPECTS}")
        if c.get("difficulty") not in DIFFICULTIES:
            errors.append(f"{cid}: difficulty={c.get('difficulty')!r} не из {DIFFICULTIES}")
        if not str(c.get("input", "")).strip():
            errors.append(f"{cid}: пустой input")
        if c.get("expect") == "defect":
            aliases = c.get("aliases") or []
            if len(aliases) < 2:
                errors.append(f"{cid}: у defect-примера должно быть ≥2 алиасов (сейчас {len(aliases)})")
            if not str(c.get("defect_ru", "")).strip():
                errors.append(f"{cid}: у defect-примера пустой defect_ru")
        if c.get("expect") == "clean" and (c.get("aliases")):
            errors.append(f"{cid}: у clean-примера не должно быть алиасов")
    return errors


def coverage(cases):
    by_mode = Counter(c["mode"] for c in cases)
    by_expect = Counter(c["expect"] for c in cases)
    by_diff = Counter(c["difficulty"] for c in cases)
    by_section = Counter(c["id"][0] for c in cases)
    return by_mode, by_expect, by_diff, by_section


def run():
    cases = load_cases()
    errors = check(cases)
    by_mode, by_expect, by_diff, by_section = coverage(cases)

    print(f"Всего примеров: {len(cases)}")
    print(f"По режимам:     {dict(by_mode)}")
    print(f"По ожиданию:    {dict(by_expect)}")
    print(f"По сложности:   {dict(by_diff)}")
    print(f"По разделам:    {dict(sorted(by_section.items()))}")

    missing_sections = REQUIRED_SECTIONS - set(by_section)
    if missing_sections:
        errors.append(f"не покрыты разделы: {sorted(missing_sections)}")
    if by_expect.get("clean", 0) < 10:
        errors.append("слишком мало clean-примеров (нужно ≥10) — иначе не ловим галлюцинации дефектов")
    if len(by_mode) < 3:
        errors.append("покрыты не все три режима (review / clause-check / fix)")

    if errors:
        print("\nОШИБКИ:")
        for e in errors:
            print("  -", e)
    else:
        print("\nOK: структура валидна, таксономия и режимы покрыты.")
    return errors


# ── pytest-совместимые тесты ─────────────────────────────────────────────
def test_structure_valid():
    assert not check(load_cases())


def test_coverage_complete():
    cases = load_cases()
    _, by_expect, _, by_section = coverage(cases)
    assert REQUIRED_SECTIONS <= set(by_section), "не все разделы покрыты"
    assert by_expect.get("clean", 0) >= 10, "нужно ≥10 clean-примеров"
    assert len(cases) >= 100, "ожидается не менее 100 примеров"


if __name__ == "__main__":
    import sys
    sys.exit(1 if run() else 0)
