#!/usr/bin/env python3
"""
Tests de MUD — solo librería estándar (unittest), sin dependencias.

    python -m unittest -v
    # o simplemente:
    python test_mud.py

Cubren lo que hay que poder defender: hashing determinista, versionado,
concurrencia optimista (conflictos), presupuesto de tokens, reranking y auditoría.
"""

import os
import tempfile
import unittest

from mud import MUD, Conflict, _hash, _est_tokens


class MUDTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join(tempfile.mkdtemp(), "t.db")
        self.mud = MUD(self.tmp)

    def tearDown(self):
        self.mud.close()
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    # -- helpers --------------------------------------------------------------
    def _w(self, uri, content, **kw):
        return self.mud.write(uri, content, actor="test", **kw)

    # -- hashing --------------------------------------------------------------
    def test_hash_es_determinista(self):
        self.assertEqual(_hash("hola"), _hash("hola"))
        self.assertNotEqual(_hash("hola"), _hash("chau"))
        self.assertTrue(_hash("x").startswith("sha256:"))

    def test_est_tokens_positivo(self):
        self.assertGreaterEqual(_est_tokens(""), 1)
        self.assertLess(_est_tokens("abcd"), _est_tokens("abcd" * 100))

    # -- escritura / versionado ----------------------------------------------
    def test_create_arranca_en_v1(self):
        r = self._w("mud:test/a", {"x": 1})
        self.assertEqual(r["op"], "create")
        self.assertEqual(r["version"], 1)

    def test_update_incrementa_version(self):
        r1 = self._w("mud:test/a", {"x": 1})
        r2 = self._w("mud:test/a", {"x": 2}, before_hash=r1["content_hash"])
        self.assertEqual(r2["op"], "update")
        self.assertEqual(r2["version"], 2)

    # -- concurrencia optimista ----------------------------------------------
    def test_conflicto_con_hash_viejo(self):
        r1 = self._w("mud:test/a", {"x": 1})
        self._w("mud:test/a", {"x": 2}, before_hash=r1["content_hash"])  # v2
        # segundo agente escribe con el hash v1 (viejo) -> conflicto
        with self.assertRaises(Conflict):
            self._w("mud:test/a", {"x": 3}, before_hash=r1["content_hash"])

    def test_create_con_before_hash_es_rechazado(self):
        with self.assertRaises(Conflict):
            self._w("mud:test/nuevo", {"x": 1}, before_hash="sha256:loquesea")

    def test_conflicto_no_corrompe_el_bloque(self):
        r1 = self._w("mud:test/a", {"x": 1})
        self._w("mud:test/a", {"x": 2}, before_hash=r1["content_hash"])
        try:
            self._w("mud:test/a", {"x": 3}, before_hash=r1["content_hash"])
        except Conflict:
            pass
        # el bloque debe seguir en v2, sin rastro del write fallido
        block = self.mud.resolve("mud:test/a")
        self.assertEqual(block["version"], 2)

    # -- resolución -----------------------------------------------------------
    def test_resolve_inexistente_es_none(self):
        self.assertIsNone(self.mud.resolve("mud:test/no-existe"))

    # -- consulta / presupuesto ----------------------------------------------
    def test_query_encuentra_el_bloque(self):
        self._w("mud:test/db", "pool de conexiones postgres produccion",
                title="pool", summary="pool postgres", tags=["db"])
        res = self.mud.query("pool de postgres", budget_tokens=200)
        uris = [s["uri"] for s in res["selected"]]
        self.assertIn("mud:test/db", uris)

    def test_presupuesto_no_se_excede(self):
        for i in range(6):
            self._w(f"mud:test/big{i}", "alfa " * 200,  # ~250 tokens c/u
                    summary="alfa " * 200, tags=["alfa"])
        res = self.mud.query("alfa", budget_tokens=60)
        self.assertLessEqual(res["context_tokens_used"], 60)

    # -- reranking por brecha -------------------------------------------------
    def test_reranking_sube_precision_sin_perder_gold(self):
        # gold matchea las 4 palabras; distractores comparten solo una
        self._w("mud:test/gold", "alfa beta gamma delta objetivo unico",
                summary="alfa beta gamma delta", tags=["alfa"])
        for i in range(5):
            self._w(f"mud:test/ruido{i}", "alfa relleno generico distinto",
                    summary="alfa relleno", tags=["alfa"])
        q = "alfa beta gamma delta"
        base = self.mud.query(q, budget_tokens=800, keep_ratio=0.0)
        rr = self.mud.query(q, budget_tokens=800, keep_ratio=0.5)
        # el rerank no debe devolver MÁS que el base...
        self.assertLessEqual(len(rr["selected"]), len(base["selected"]))
        # ...y el bloque correcto tiene que seguir presente
        self.assertIn("mud:test/gold", [s["uri"] for s in rr["selected"]])

    # -- auditoría ------------------------------------------------------------
    def test_audit_registra_los_writes(self):
        r1 = self._w("mud:test/a", {"x": 1})
        self._w("mud:test/a", {"x": 2}, before_hash=r1["content_hash"])
        log = self.mud.audit("mud:test/a")
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["version"], 2)   # más reciente primero
        self.assertEqual(log[0]["actor"], "test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
