    # Lab 02 — Data Structures and the Inverted Index

    ## Опис проєкту

    Розроблено пошукову систему на основі інвертованого індексу.
    Для тестування використано корпус із 300 документів,
    який містить 34 унікальні терміни.

    ## Структура проєкту

    - corpus.py — читання та токенізація документів.
    - index.py — побудова інвертованого індексу.
    - search.py — пошук документів.
    - store.py — збереження та завантаження індексу.
    - benchmark.py — порівняння продуктивності.
    - data/ — корпус текстових документів.

    ## Запуск програми

    Побудова індексу:

        python -m findex.index data --out index.bin

    Пошук алгоритмом merge:

        python -m findex.search index.bin "is OR a" --engine merge

    Пошук алгоритмом set:

        python -m findex.search index.bin "is OR a" --engine set

    ## Порівняння алгоритмів пошуку

    Кожен запит виконано 1000 разів.

    | Запит | Merge, мс | Set, мс |
    |---|---:|---:|
    | search AND python | 110.378 | 60.178 |
    | is AND a | 8.256 | 10.595 |
    | search OR python | 120.803 | 55.983 |
    | is OR a | 8.414 | 9.162 |

    На використаному корпусі алгоритм set показав кращі
    результати для поширених термінів, а merge — для рідкісних.

    ## Порівняння структур даних

    | Структура | Пікова пам'ять, байт | Розмір файлу, байт | Завантаження, мс |
    |---|---:|---:|---:|
    | Plain dataclass | 706495 | 86992 | 17.665 |
    | Slotted dataclass | 473338 | 67921 | 24.489 |
    | array('I') | 249371 | 39094 | 13.734 |

    Вимірювання проведено для списків входжень без метаданих.

    Slotted dataclass зменшує витрати пам'яті завдяки
    відсутності словника атрибутів екземпляра.

    Масив array('I') зберігає цілі числа компактніше,
    тому показав найменше використання пам'яті.

    ## Збереження індексу

    Реалізовано підтримку двох форматів: Pickle та JSON.

    Pickle не можна використовувати для завантаження
    файлів із недовірених джерел, оскільки десеріалізація
    може призвести до виконання довільного коду.

    ## Висновок

    Реалізовано інвертований індекс, логічний пошук,
    збереження даних та порівняння структур даних
    за використанням пам'яті й продуктивністю.


    ## Lab 03 — The Object Model and Ranking

    ### M1 — Object Model

    - Index supports len(), iteration, membership and item access.
    - Document statistics and cached average document length.
    - Context manager open_index().

    ### M2 — Ranking

    - TF-IDF and BM25 scoring.
    - Scorer protocol.
    - SearchResult dataclass.
    - Top-k selection using heapq.nlargest.

    #### Sanity checks

    | Check | Result | Status |
    |---|---|---|
    | Rare vs common term | 5.703782 > 0.006689 | PASS |
    | BM25 saturation | 0.002587 > 0.000023 | PASS |
    | Short vs long document | 0.014676 > 0.008280 | PASS |

    ### M3 — Query Parser

    - Recursive descent parser.
    - AND, OR, NOT operators.
    - Implicit AND and parentheses.
    - Exact phrase search.
    - Positional inverted index.
    - Pickle and JSON serialization.

    ### M4 — Performance and Evaluation

    - timed decorator for build_index, load and search.
    - LRU cache with maxsize=256.
    - Highlighted text snippets with 80-character context.

    #### Cache benchmark

    | Request | Time (ms) | Cache |
    |---|---:|---|
    | First | 0.428 | MISS |
    | Repeated | 0.050 | HIT |

    Cache hits do not guarantee faster overall ranking.

    #### Precision@5

    | Query | TF-IDF | BM25 |
    |---|---:|---:|
    | programming language | 0.00 | 0.00 |
    | dictionaries AND sets | 0.20 | 0.20 |
    | "inverted index" | 0.40 | 0.40 |
    | "hash tables" | 0.20 | 0.20 |
    | keys AND values | 0.20 | 0.20 |
    | "boolean queries" | 0.20 | 0.20 |
    | "data structures" | 0.00 | 0.00 |
    | "memory optimization" | 0.00 | 0.00 |
    | "text documents" | 0.20 | 0.20 |
    | "search engines" | 0.00 | 0.00 |
    | Mean Precision@5 | 0.14 | 0.14 |

    Both algorithms achieved the same measured precision.
    Evaluation uses 10 manually labelled queries.
    Relevance labels cover only the five original documents.

    ### Corpus statistics

    - Documents: 300
    - Unique terms: 34
    - Average document length: 196.83

    ### Usage

    Build positional index:

        python -m findex.index data --out index.bin --positions

    Ranked search:

        python -m findex.ranking "(python OR search) AND index" --k 5

    Cache demonstration:

        python -m findex.ranking "python AND search" --k 3 --repeat 2

    Sanity checks:

        python sanity_checks.py

    Evaluation:

        python evaluation.py

### Висновок

 У ході лабораторної роботи реалізовано ранжування документів за алгоритмами TF-IDF та BM25, логічні запити, пошук точних фраз, кешування та формування текстових фрагментів. проведено оцінювання точності пошуку за метрикою Precision@5. бидва алгоритми показали результат 0.14 на використаній розмітці корпусу.


---

## Laboratory work 4

### CI status

[![CI](https://github.com/8489279-web/Lab2/actions/workflows/ci.yml/badge.svg)](https://github.com/8489279-web/Lab2/actions/workflows/ci.yml)

### Installation

    uv sync
    uv tool install .

### CLI commands

    findex --help
    findex index data --out index.bin
    findex search "python" --scorer bm25 --k 5
    findex search "python" --scorer tfidf --k 5
    findex search "python" --json
    findex stats
    findex -v search "python"
    findex -vv search "python"

### Code quality

    uv run ruff check .
    uv run pyright
    uv run pytest -q

Results:

- Ruff: all checks passed.
- Pyright: 0 errors, 0 warnings.
- Pytest: 118 passed.
- Hypothesis: 3 property-based tests.
- Code coverage: 68%.

### Test coverage

    uv run pytest --cov=findex --cov-report=term-missing

| Module | Coverage |
|---|---:|
| benchmark.py | 0% |
| cache.py | 44% |
| cli.py | 94% |
| corpus.py | 83% |
| index.py | 70% |
| query.py | 95% |
| ranking.py | 46% |
| scoring.py | 91% |
| search.py | 83% |
| snippets.py | 0% |
| store.py | 74% |
| utils.py | 100% |
| Total | 68% |

Benchmark scripts and legacy demonstration entry points
were not specifically targeted by automated tests.
Snippet generation remains untested.
Some cache and ranking branches also remain uncovered.

### Slow tests

    uv run pytest -m "not slow" -q
    uv run pytest -m slow -q

- Fast tests: 116.
- Slow tests: 2.

### Conclusion

The Findex project was extended with strict type checking,
automated testing, property-based testing, package metadata,
a command-line interface, structured logging and CI configuration.
All 118 automated tests passed, and code coverage reached 68%.

