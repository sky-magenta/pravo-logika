# Third-Party Notices

`pravo-logika` — проприетарной части нет: весь проект под лицензией MIT (см. [`LICENSE`](LICENSE)).
Этот файл перечисляет сторонний материал, включённый в репозиторий или послуживший его основой, и условия его использования. Все перечисленные компоненты распространяются на пермиссивных условиях (MIT) либо находятся в общественном достоянии (public domain), что совместимо с MIT-лицензией настоящего проекта.

---

## 1. Skill «logika» — Pavel Rykov (MIT)

- **Проект:** `logika`, часть коллекции rpa-skills.
- **Автор / правообладатель:** Pavel Rykov.
- **Источник:** https://github.com/EvilFreelancer/logika
- **Лицензия:** MIT.

**Что перенесено в `pravo-logika`.** Логический слой («движок») и вспомогательные материалы восходят к `logika` и перенесены с минимальными косметическими изменениями:

| Файл в этом репозитории | Происхождение |
|---|---|
| `references/logic/concepts.md` | из `logika` |
| `references/logic/judgments.md` | из `logika` |
| `references/logic/syllogism.md` | из `logika` |
| `references/logic/induction.md` | из `logika` |
| `references/logic/errors.md` | из `logika` |
| `references/logic/laws.md` | из `logika` |
| `docs/konspekt.md` | конспект первоисточника (Челпанов), сопровождающий логический слой |

Структура скилла (мультиинструментные манифесты `.claude-plugin` / `.codex-plugin` / `.cursor-plugin`, формат команд, разметка референсов) также следует образцу `logika` / rpa-skills.

**Что НЕ является производным от `logika`.** Правовой слой и деонтический раздел логического слоя созданы для настоящего проекта и являются оригинальной работой [Sofya Smirnova](https://damascus-ink.ru) ([t.me/forgednotwritten](https://t.me/forgednotwritten)): `SKILL.md` (правовой движок, режимы, форматы), `references/norm.md`, `references/interpretation.md`, `references/legal-errors.md`, `references/contract.md`, `references/proof.md`, `references/logic/deontic.md` (деонтическая логика — материал новее «Учебника логики» и в `logika` отсутствует), `commands/review.md`, `commands/clause-check.md`, `README.md`, `docs/index.html`.

**Текст лицензии MIT (`logika`):**

```
MIT License

Copyright (c) 2026 Pavel Rykov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

> Если исходный `logika` использует иную формулировку или год в своём `LICENSE`, при публикации сверьте и приведите текст выше к оригиналу дословно.

---

## 2. «Учебник логики» — Г. И. Челпанов (public domain)

- **Произведение:** Г. И. Челпанов, «Учебник логики».
- **Статус:** общественное достояние (public domain) — срок действия авторского права истёк.
- **Как используется:** классический логический материал (учение о понятии, суждении, силлогизме, индукции, законах мышления, логических ошибках) лежит в основе логического слоя `references/logic/` и конспекта `docs/konspekt.md`. Формулировки, примеры и структура изложения восходят к этому учебнику.

Материал в общественном достоянии используется свободно; настоящее упоминание приведено для полноты атрибуции.

---

## 3. Шрифт Jun (лендинг)

- **Шрифт:** Jun (Regular, Italic) — автор **Василий Шишкин (Vasily Shishkin)**.
- **Условия:** свободен для коммерческого использования; embedding разрешён (`fsType=0`).
- **Как используется:** встроен в `docs/index.html` как base64 `@font-face` (заголовки, прозаический текст, вордмарк). Внешних сетевых загрузок лендинг не делает — страница самодостаточна.
- **Оговорка:** шрифт принадлежит его автору и **не покрывается MIT-лицензией** настоящего репозитория; MIT распространяется на текст и код проекта, но не передаёт прав на шрифт.

---

*Изменения в составе сторонних компонентов отражаются в этом файле. Основная лицензия проекта — [`LICENSE`](LICENSE).*
