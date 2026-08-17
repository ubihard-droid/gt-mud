# Changelog

Todas las novedades relevantes de MUD se registran acá.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/).

## [0.2.0] — 2026-08-16

### Agregado
- **Reranking por brecha de relevancia** (`keep_ratio`) en `query()`: sube la
  precisión del contexto de 20% a 80% sin perder recall (Fase 3 del roadmap).
- **Benchmark** (`bench.py`): mide ahorro de tokens (99.7%), hit-rate (100%) y
  precisión, comparando "mandar todo" vs. MUD con presupuesto. Solo stdlib.
- **Suite de tests** (`test_mud.py`, 12 casos, unittest): hashing, versionado,
  concurrencia optimista, presupuesto, reranking y auditoría.
- **CI** con GitHub Actions: tests + demo + benchmark en Python 3.9 / 3.11 / 3.13.
- Gráfico del benchmark en el README.
- Sección 16.4 del spec documentando el reranking implementado.

### Corregido
- `MUD.close()` libera el archivo SQLite: el demo fallaba al borrar la base en
  Windows por tener la conexión abierta.

## [0.1.0] — 2026-08-16

### Agregado
- Especificación **MUD v3** (`MUD-V3.md`): arquitectura de atención distribuida
  para sistemas multiagente.
- Implementación **MVP** (`mud.py`): SQLite + FTS5, content hashing, concurrencia
  optimista con `before_hash`, consulta con presupuesto de tokens, auditoría, y
  API HTTP opcional (FastAPI).
