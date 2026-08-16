#!/usr/bin/env python3
"""
MUD mini — Memoria Unificada Distribuida (núcleo)
Una fuente de verdad que varios agentes leen y escriben sin pisarse.

Núcleo, nada más:
  - 1 base SQLite = fuente de verdad (un archivo)
  - cada bloque: uri + content_hash + version
  - /query : búsqueda full-text con presupuesto de tokens (nadie carga todo)
  - /write : escritura con before_hash (concurrencia optimista -> no se pisan)
  - /resolve : traer un bloque completo por uri
  - /audit : quién escribió qué

Uso:
  python mud.py demo            # corre una demo de 2 agentes (solo stdlib)
  python mud.py serve           # levanta la API (requiere: pip install fastapi uvicorn)

---
Autor:   Gabriel Tabárez Atanasich — Director, División Informática
Proyecto:MUD — Memoria Unificada Distribuida
Marca:   SNI SOFT by Tirnel  ·  tech.sni.com.uy
Método:  Algoritmo Loop Espiral GT
© 2026 Gabriel Tabárez Atanasich. Todos los derechos reservados.
"""

import sqlite3
import hashlib
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from typing import Optional

DB_PATH = "mud.db"


# ---------------------------------------------------------------------------
# Núcleo: la clase MUD opera directo sobre SQLite. No depende de HTTP.
# ---------------------------------------------------------------------------

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _est_tokens(text: str) -> int:
    # aproximación barata: ~4 chars por token
    return max(1, math.ceil(len(text) / 4))


def _fts_query(intent: str) -> str:
    # Sanitiza la intención: solo palabras, unidas con OR entre comillas.
    # Evita que un agente inyecte operadores FTS5 raros o rompa la sintaxis.
    words = re.findall(r"\w+", intent, flags=re.UNICODE)
    words = [w for w in words if len(w) > 1][:12]
    if not words:
        return '""'
    return " OR ".join(f'"{w}"' for w in words)


class Conflict(Exception):
    """La escritura chocó: el bloque cambió desde que el agente lo leyó."""


class MUD:
    def __init__(self, path: str = DB_PATH):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                uri          TEXT PRIMARY KEY,
                category     TEXT,
                title        TEXT,
                content      TEXT NOT NULL,
                summary      TEXT,
                tags         TEXT,
                content_hash TEXT NOT NULL,
                version      INTEGER NOT NULL,
                updated_at   TEXT NOT NULL,
                updated_by   TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts USING fts5(
                uri UNINDEXED, title, summary, content, tags,
                content='blocks', content_rowid='rowid'
            );

            -- triggers para mantener el índice FTS sincronizado con la verdad
            CREATE TRIGGER IF NOT EXISTS blocks_ai AFTER INSERT ON blocks BEGIN
                INSERT INTO blocks_fts(rowid, uri, title, summary, content, tags)
                VALUES (new.rowid, new.uri, new.title, new.summary, new.content, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS blocks_ad AFTER DELETE ON blocks BEGIN
                INSERT INTO blocks_fts(blocks_fts, rowid, uri, title, summary, content, tags)
                VALUES ('delete', old.rowid, old.uri, old.title, old.summary, old.content, old.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS blocks_au AFTER UPDATE ON blocks BEGIN
                INSERT INTO blocks_fts(blocks_fts, rowid, uri, title, summary, content, tags)
                VALUES ('delete', old.rowid, old.uri, old.title, old.summary, old.content, old.tags);
                INSERT INTO blocks_fts(rowid, uri, title, summary, content, tags)
                VALUES (new.rowid, new.uri, new.title, new.summary, new.content, new.tags);
            END;

            CREATE TABLE IF NOT EXISTS writes_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                uri         TEXT NOT NULL,
                op          TEXT NOT NULL,          -- create | update
                before_hash TEXT,
                after_hash  TEXT NOT NULL,
                version     INTEGER NOT NULL,
                actor       TEXT,
                reason      TEXT,
                ts          TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    # -- escritura con concurrencia optimista -----------------------------
    def write(self, uri, content, *, category=None, title=None, summary=None,
              tags=None, before_hash=None, actor=None, reason=None) -> dict:
        if isinstance(content, (dict, list)):
            content = json.dumps(content, ensure_ascii=False)
        tags = ",".join(tags) if isinstance(tags, list) else (tags or "")
        after_hash = _hash(content)

        # BEGIN IMMEDIATE: toma el lock de escritura ya, evita carreras.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT content_hash, version FROM blocks WHERE uri=?", (uri,)
            ).fetchone()

            if row is None:
                # bloque nuevo
                if before_hash not in (None, ""):
                    raise Conflict(f"{uri} no existe pero se envió before_hash")
                version, op = 1, "create"
                self.db.execute(
                    """INSERT INTO blocks
                       (uri, category, title, content, summary, tags,
                        content_hash, version, updated_at, updated_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (uri, category, title, content, summary, tags,
                     after_hash, version, _now(), actor),
                )
            else:
                # bloque existente: el before_hash tiene que coincidir
                if before_hash != row["content_hash"]:
                    raise Conflict(
                        f"conflicto en {uri}: esperado {row['content_hash']}, "
                        f"enviado {before_hash!r}. Re-leé y reintentá."
                    )
                version, op = row["version"] + 1, "update"
                self.db.execute(
                    """UPDATE blocks SET category=?, title=?, content=?, summary=?,
                       tags=?, content_hash=?, version=?, updated_at=?, updated_by=?
                       WHERE uri=?""",
                    (category, title, content, summary, tags, after_hash,
                     version, _now(), actor, uri),
                )

            self.db.execute(
                """INSERT INTO writes_log
                   (uri, op, before_hash, after_hash, version, actor, reason, ts)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (uri, op, before_hash, after_hash, version, actor, reason, _now()),
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {"uri": uri, "op": op, "version": version,
                "content_hash": after_hash}

    # -- resolución -------------------------------------------------------
    def resolve(self, uri: str) -> Optional[dict]:
        row = self.db.execute("SELECT * FROM blocks WHERE uri=?", (uri,)).fetchone()
        return dict(row) if row else None

    # -- consulta con presupuesto ----------------------------------------
    def query(self, intent, *, budget_tokens=800, top_k=5,
              category=None, view="auto", keep_ratio=0.0) -> dict:
        """
        keep_ratio: corte por brecha de relevancia (reranking barato, Fase 3).
          0.0  -> desactivado: devuelve hasta top_k candidatos.
          0<r<1 -> descarta los bloques cuya relevancia sea menor que
                   (mejor_relevancia * r). El #1 siempre se conserva.
          Sube la precisión sin perder recall cuando hay un ganador claro.
        """
        match = _fts_query(intent)
        sql = (
            "SELECT b.uri, b.category, b.title, b.summary, b.content, "
            "b.content_hash, b.version, bm25(blocks_fts) AS rank "
            "FROM blocks_fts JOIN blocks b ON b.rowid = blocks_fts.rowid "
            "WHERE blocks_fts MATCH ? "
        )
        params = [match]
        if category:
            sql += "AND b.category = ? "
            params.append(category)
        sql += "ORDER BY rank LIMIT ?"          # bm25: menor = mejor
        params.append(top_k)

        rows = self.db.execute(sql, params).fetchall()

        # Reranking por brecha: bm25 devuelve menor = mejor, así que
        # relevancia = -rank (mayor = mejor). Cortamos el ruido lejano al top.
        if rows and keep_ratio > 0.0:
            rels = [-r["rank"] for r in rows]
            best = rels[0]
            if best > 0:
                cut = best * keep_ratio
                rows = [r for r, rel in zip(rows, rels) if rel >= cut]

        selected, omitted, used = [], [], 0
        for r in rows:
            pointer = f"{r['uri']}@v{r['version']}"
            full = r["content"]
            summ = r["summary"] or (full[:160] + ("…" if len(full) > 160 else ""))

            # elegir la vista más rica que entre en el presupuesto
            if view in ("auto", "full") and used + _est_tokens(full) <= budget_tokens:
                chosen, payload = "full", full
            elif view in ("auto", "full", "summary") and used + _est_tokens(summ) <= budget_tokens:
                chosen, payload = "summary", summ
            elif used + _est_tokens(pointer) <= budget_tokens:
                chosen, payload = "pointer", pointer
            else:
                omitted.append({"uri": r["uri"], "pointer": pointer,
                                "reason": "budget_exceeded"})
                continue

            used += _est_tokens(payload)
            selected.append({
                "uri": r["uri"], "pointer": pointer, "view": chosen,
                "content_hash": r["content_hash"],
                ("content" if chosen == "full" else "value"): payload,
            })

        return {"intent": intent, "budget_tokens": budget_tokens,
                "context_tokens_used": used, "selected": selected,
                "omitted": omitted}

    # -- cierre -----------------------------------------------------------
    def close(self):
        # Cerrar la conexión libera el archivo .db (en Windows no se puede
        # borrar/mover un SQLite con la conexión todavía abierta).
        self.db.close()

    # -- auditoría --------------------------------------------------------
    def audit(self, uri: Optional[str] = None, limit: int = 50) -> list:
        if uri:
            rows = self.db.execute(
                "SELECT * FROM writes_log WHERE uri=? ORDER BY id DESC LIMIT ?",
                (uri, limit)).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM writes_log ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# API HTTP (imports perezosos: el demo no necesita FastAPI instalado)
# ---------------------------------------------------------------------------

def build_app(db_path: str = DB_PATH):
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    mud = MUD(db_path)
    app = FastAPI(title="MUD mini", version="1.0")

    class WriteReq(BaseModel):
        uri: str
        content: object
        category: Optional[str] = None
        title: Optional[str] = None
        summary: Optional[str] = None
        tags: Optional[list] = None
        before_hash: Optional[str] = None
        actor: Optional[str] = None
        reason: Optional[str] = None

    class QueryReq(BaseModel):
        intent: str
        budget_tokens: int = 800
        top_k: int = 5
        category: Optional[str] = None
        view: str = "auto"
        keep_ratio: float = 0.0

    @app.get("/health")
    def health():
        return {"ok": True, "ts": _now()}

    @app.post("/write")
    def write(req: WriteReq):
        try:
            return mud.write(req.uri, req.content, category=req.category,
                             title=req.title, summary=req.summary, tags=req.tags,
                             before_hash=req.before_hash, actor=req.actor,
                             reason=req.reason)
        except Conflict as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.post("/query")
    def query(req: QueryReq):
        return mud.query(req.intent, budget_tokens=req.budget_tokens,
                         top_k=req.top_k, category=req.category, view=req.view,
                         keep_ratio=req.keep_ratio)

    @app.post("/resolve")
    def resolve(uri: str):
        block = mud.resolve(uri)
        if not block:
            raise HTTPException(status_code=404, detail=f"{uri} no encontrado")
        return block

    @app.get("/audit")
    def audit(uri: Optional[str] = None, limit: int = 50):
        return mud.audit(uri, limit)

    return app


def serve():
    import uvicorn
    uvicorn.run(build_app(), host="127.0.0.1", port=8077)


# ---------------------------------------------------------------------------
# Demo: dos agentes compartiendo una sola verdad (solo stdlib)
# ---------------------------------------------------------------------------

def demo():
    import os
    if os.path.exists("mud_demo.db"):
        os.remove("mud_demo.db")
    mud = MUD("mud_demo.db")

    print("== 1) Claude escribe un bloque de conocimiento ==")
    r1 = mud.write(
        "mud:knowledge/db/pool",
        {"pool_size": 20, "db": "postgres", "env": "produccion"},
        category="environment", title="Pool de conexiones PG",
        summary="PostgreSQL producción: pool_size=20.",
        tags=["db", "postgres", "produccion"],
        actor="claude-code", reason="registro inicial")
    print("  ->", r1)

    print("\n== 2) Hermes consulta con presupuesto (no carga todo) ==")
    q = mud.query("configuracion del pool de postgres en produccion",
                  budget_tokens=200)
    print("  tokens usados:", q["context_tokens_used"])
    for s in q["selected"]:
        print("  ->", s["uri"], f"[{s['view']}]",
              s.get("content") or s.get("value"))

    print("\n== 3) Dos agentes intentan escribir el MISMO bloque ==")
    current = mud.resolve("mud:knowledge/db/pool")["content_hash"]
    print("  hash actual:", current)

    # Hermes escribe primero, con el hash correcto -> OK
    r2 = mud.write(
        "mud:knowledge/db/pool",
        {"pool_size": 25, "db": "postgres", "env": "produccion"},
        category="environment", title="Pool de conexiones PG",
        summary="PostgreSQL producción: pool_size=25 (subido por carga).",
        tags=["db", "postgres", "produccion"],
        before_hash=current, actor="hermes", reason="mas carga observada")
    print("  Hermes OK ->", r2)

    # Gemini escribe con el hash VIEJO -> conflicto detectado (no se pisan)
    try:
        mud.write(
            "mud:knowledge/db/pool",
            {"pool_size": 30},
            before_hash=current, actor="gemini", reason="queria 30")
    except Conflict as e:
        print("  Gemini BLOQUEADO ->", e)

    print("\n== 4) Auditoría: quién tocó el bloque ==")
    for a in mud.audit("mud:knowledge/db/pool"):
        print(f"  v{a['version']} {a['op']:6} por {a['actor']:11} — {a['reason']}")

    print("\nOK. Una verdad, varios agentes, cero pisadas.")
    mud.close()
    os.remove("mud_demo.db")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if cmd == "serve":
        serve()
    else:
        demo()
