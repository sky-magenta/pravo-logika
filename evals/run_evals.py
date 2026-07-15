#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E-прогон скилла pravo-logika по набору cases.jsonl через Claude API.

Каждый пример подаётся модели, у которой в системном контексте загружен весь
скилл (SKILL.md + все references). Ответ модели сверяется с ожиданием:
  • defect  — назван ли ожидаемый дефект (по алиасам / латинскому имени);
  • clean   — не выдуман ли дефект (вердикт «корректна / однозначна»).

Системный контекст (большой и неизменный) кэшируется prompt caching'ом —
он одинаков для всех 100 запросов, поэтому оплачивается по сути один раз.

Требуется ключ: экспортируйте ANTHROPIC_API_KEY (или войдите через `ant auth login`).

Примеры:
  python run_evals.py --dry-run                 # без сети: проверить сборку промптов
  python run_evals.py --limit 5                 # быстрый прогон на 5 примерах
  python run_evals.py --grader llm              # грейдинг вторым вызовом-судьёй (точнее для clean)
  python run_evals.py --model claude-opus-4-8   # прогнать весь набор
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES_PATH = os.path.join(HERE, "cases.jsonl")

DEFAULT_MODEL = "claude-opus-4-8"

# Файлы скилла, которые кладём в системный контекст модели.
SKILL_FILES = [
    "SKILL.md",
    "references/norm.md",
    "references/interpretation.md",
    "references/legal-errors.md",
    "references/contract.md",
    "references/proof.md",
    "references/logic/concepts.md",
    "references/logic/judgments.md",
    "references/logic/deontic.md",
    "references/logic/syllogism.md",
    "references/logic/induction.md",
    "references/logic/errors.md",
    "references/logic/laws.md",
    "references/compare.md",
]

MODE_INSTRUCTIONS = {
    "review": (
        "Режим РЕВЬЮ. Разбери правовую логику текста ниже строго по формату отчёта ревью из SKILL.md. "
        "Назови каждый дефект русским и латинским именем (где есть). Текст не переписывай."
    ),
    "clause-check": (
        "Режим CLAUSE-CHECK. Проверь договорную формулировку на логическую однозначность строго "
        "по формату clause-check из SKILL.md (оценка + таблица типов неоднозначности)."
    ),
    "fix": (
        "Режим ПРАВКА. Сначала краткая диагностика (назови дефект русским и латинским именем), "
        "затем переписанный текст с исправленной аргументацией и списком правок, по правилам SKILL.md."
    ),
    "compare": (
        "Режим СРАВНЕНИЕ. Разбери СООТНОШЕНИЕ двух встречных позиций строго по формату сравнения из SKILL.md "
        "(references/compare.md): предмет спора (об одном ли спорят), карта расхождений (право/факт/оценка), "
        "скрытые посылки, несущая точка, логическое соотношение, дефекты сопоставления. Материальную правоту "
        "не присуждай; дефект сопоставления называй русским и латинским именем, где есть."
    ),
}

# Сигналы «чисто» для быстрого (alias) грейдинга clean-примеров.
# Даны основами (без окончаний), сверка идёт по нормализованному тексту — см. _norm.
CLEAN_SIGNALS = [
    "корректн", "однозначн", "дефектов не найд", "не найд дефект",
    "неоднозначност не", "без дефект", "дефект не выявл", "нарушени не",
    "дефектов нет", "не выдум", "правки не требует", "устранение не требует",
    # сигналы «чисто» для режима сравнения (настоящий спор, дефекта сопоставления нет)
    "дефектов сопоставления нет", "дефекта сопоставления нет", "мнимого спора нет",
    "спор настоящий", "спор по существу", "спорят об одном", "спор реальный",
]

# ── Нормализация для морфологически устойчивого сопоставления ──────────────
# Русские алиасы страдают от склонений («закон тождества» ≠ «закона тождества»)
# и типографики («floor и cap» ≠ «floor/cap»). Нормализуем регистр и пунктуацию,
# а многословные алиасы сверяем по основам слов (первые 5 букв), а не буквально.
_PUNCT = "«»„“”\"'`()[]{}<>.,;:!?/\\|—–-… "
_TRANS = {ord(c): " " for c in _PUNCT}


def _norm(s):
    return " ".join(str(s).lower().translate(_TRANS).split())


def _stems(needle):
    # значимые слова алиаса → основы (первые 5 букв для слов длиннее 5)
    out = []
    for w in _norm(needle).split():
        if len(w) <= 2:
            continue
        out.append(w[:5] if len(w) > 5 else w)
    return out


def _hit(needle, norm_text):
    """Алиас найден, если целиком входит в текст ИЛИ все его основы присутствуют."""
    n = _norm(needle)
    if n and n in norm_text:
        return True
    stems = _stems(needle)
    return bool(stems) and all(st in norm_text for st in stems)


def read_skill_context():
    parts = []
    for rel in SKILL_FILES:
        p = os.path.join(ROOT, rel)
        with open(p, encoding="utf-8") as f:
            parts.append(f"===== ФАЙЛ: {rel} =====\n" + f.read())
    header = (
        "Ты действуешь как скилл pravo-logika. Ниже — полный текст скилла "
        "(SKILL.md и все references). Действуй строго по нему: проверяй ФОРМУ "
        "правового рассуждения, нормы и практику по памяти не подставляй "
        "(ставь флаг [требует проверки: норма / практика]).\n\n"
    )
    return header + "\n\n".join(parts)


def load_cases(limit=None, only_mode=None):
    cases = []
    with open(CASES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            if only_mode and c["mode"] != only_mode:
                continue
            cases.append(c)
    if limit:
        cases = cases[:limit]
    return cases


def build_user_prompt(case):
    return (
        MODE_INSTRUCTIONS[case["mode"]]
        + "\n\nТекст:\n"
        + case["input"]
    )


def grade_alias(case, output):
    """Быстрый детерминированный грейдинг по алиасам (морфологически устойчивый)."""
    norm = _norm(output)
    if case["expect"] == "clean":
        hit = any(_norm(sig) in norm for sig in CLEAN_SIGNALS)
        return hit, ("вердикт «чисто» найден" if hit else "не найден явный вердикт корректности/однозначности")
    # expect == defect
    needles = list(case.get("aliases", []))
    if case.get("defect_lat"):
        needles.append(case["defect_lat"])
    if case.get("defect_ru"):
        needles.append(case["defect_ru"])
    matched = [n for n in needles if _hit(n, norm)]
    return (len(matched) > 0), ("совпало: " + ", ".join(matched[:3]) if matched else "ожидаемый дефект не назван")


JUDGE_SYSTEM = (
    "Ты — строгий проверяющий (грейдер) результатов юридико-логического анализа. "
    "Тебе дают: ожидание и фактический ответ анализатора. Верни СТРОГО JSON "
    "{\"pass\": true|false, \"reason\": \"…\"} без пояснений вокруг."
)


def grade_llm(client, model, case, output):
    if case["expect"] == "clean":
        expectation = (
            "Ожидание: рассуждение КОРРЕКТНО / формулировка ОДНОЗНАЧНА. "
            "pass=true, только если анализатор НЕ выдумал дефект и по сути согласился, что всё корректно/однозначно "
            f"(допустимы флаги [требует проверки]). Почему корректно: {case.get('why','')}"
        )
    else:
        expectation = (
            f"Ожидаемый дефект: {case.get('defect_ru','')} ({case.get('defect_lat','')}). "
            f"Синонимы: {', '.join(case.get('aliases', []))}. "
            f"Суть: {case.get('why','')}. "
            "pass=true, если анализатор по существу выявил именно этот дефект (имя может отличаться формулировкой)."
        )
    user = (
        f"{expectation}\n\nФактический ответ анализатора:\n<<<\n{output}\n>>>\n\n"
        "Верни только JSON {\"pass\": …, \"reason\": …}."
    )
    msg = client.messages.create(
        model=model, max_tokens=400,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    try:
        start, end = text.find("{"), text.rfind("}")
        obj = json.loads(text[start:end + 1])
        return bool(obj.get("pass")), str(obj.get("reason", ""))
    except Exception:
        return False, f"судья вернул неразборчивый ответ: {text[:120]}"


def call_model(client, model, system_blocks, case, effort):
    """Один прогон примера. Возвращает текст ответа модели."""
    kwargs = dict(
        model=model,
        max_tokens=2000,
        system=system_blocks,
        messages=[{"role": "user", "content": build_user_prompt(case)}],
    )
    # Пробуем adaptive thinking + effort (новые SDK/модели); при отказе — без них.
    if effort:
        try:
            msg = client.messages.create(
                thinking={"type": "adaptive"},
                output_config={"effort": effort},
                **kwargs,
            )
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        except TypeError:
            pass  # старый SDK не знает этих параметров
        except Exception as e:
            if "thinking" not in str(e) and "output_config" not in str(e) and "effort" not in str(e):
                raise
    msg = client.messages.create(**kwargs)
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def main():
    ap = argparse.ArgumentParser(description="E2E-прогон pravo-logika по cases.jsonl")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=None, help="прогнать только первые N примеров")
    ap.add_argument("--mode", choices=["review", "clause-check", "fix"], default=None)
    ap.add_argument("--grader", choices=["alias", "llm"], default="alias",
                    help="alias — быстрый детерминированный; llm — вызов-судья (точнее для clean)")
    ap.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default="high")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(HERE, "results.json"))
    ap.add_argument("--dry-run", action="store_true", help="без сети: собрать промпты и выйти")
    args = ap.parse_args()

    cases = load_cases(limit=args.limit, only_mode=args.mode)
    system_text = read_skill_context()
    # Кэшируем большой неизменный системный контекст.
    system_blocks = [{"type": "text", "text": system_text,
                      "cache_control": {"type": "ephemeral"}}]

    if args.dry_run:
        print(f"[dry-run] примеров: {len(cases)}; системный контекст: {len(system_text)} символов "
              f"(~{len(system_text)//4} токенов, кэшируется)")
        ex = cases[0]
        print(f"[dry-run] пример {ex['id']} ({ex['mode']}):\n{build_user_prompt(ex)[:400]}…")
        print("[dry-run] сеть не вызывалась. Экспортируйте ANTHROPIC_API_KEY и уберите --dry-run для реального прогона.")
        return 0

    try:
        import anthropic
    except ImportError:
        print("Не установлен пакет anthropic:  pip install anthropic", file=sys.stderr)
        return 2
    client = anthropic.Anthropic()  # берёт ключ из окружения / профиля ant

    def run_one(case):
        try:
            output = call_model(client, args.model, system_blocks, case, args.effort)
        except Exception as e:
            return {"id": case["id"], "mode": case["mode"], "category": case["category"],
                    "expect": case["expect"], "passed": False, "error": str(e), "output": ""}
        if args.grader == "llm":
            ok, reason = grade_llm(client, args.model, case, output)
        else:
            ok, reason = grade_alias(case, output)
        return {"id": case["id"], "mode": case["mode"], "category": case["category"],
                "expect": case["expect"], "passed": ok, "reason": reason, "output": output}

    results = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for r in ex.map(run_one, cases):
            results.append(r)
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"[{mark}] {r['id']:<4} {r['mode']:<12} {r.get('reason', r.get('error',''))[:80]}")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    # Разбивка по разделам каталога (первая буква id).
    from collections import Counter
    sect_total, sect_pass = Counter(), Counter()
    for r in results:
        s = r["id"][0]
        sect_total[s] += 1
        sect_pass[s] += int(r["passed"])

    print("\n===== ИТОГ =====")
    print(f"Всего: {passed}/{total}  ({100*passed/max(total,1):.0f}%)  модель={args.model}  грейдер={args.grader}")
    for s in sorted(sect_total):
        print(f"  раздел {s}: {sect_pass[s]}/{sect_total[s]}")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"model": args.model, "grader": args.grader,
                   "passed": passed, "total": total, "results": results},
                  f, ensure_ascii=False, indent=2)
    print(f"\nПодробности: {args.out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
