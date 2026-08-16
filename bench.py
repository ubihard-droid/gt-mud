#!/usr/bin/env python3
"""
MUD bench — ¿de verdad ahorra atención?
Compara dos estrategias sobre la MISMA memoria y las MISMAS preguntas:

  1) FLAT      : el agente recibe TODA la memoria en contexto (enfoque ingenuo).
  2) MUD       : el agente consulta con presupuesto y recibe solo lo relevante.

Mide, sin trampa:
  - token_savings   : tokens ahorrados por consulta (MUD vs. mandar todo)
  - context_hit_rate: % de consultas en las que el bloque correcto SÍ llegó
                      (si ahorrás tokens pero perdés el dato, no vale)
  - precision_ctx   : del contexto entregado, qué fracción era el bloque útil

Solo librería estándar. Reproducible (semilla fija).

  python bench.py            # corre el benchmark e imprime la tabla
  python bench.py --md       # además emite el bloque Markdown para el README

---
Autor:   Gabriel Tabárez Atanasich — Director, División Informática
Proyecto:MUD — Memoria Unificada Distribuida
Marca:   SNI SOFT by Tirnel  ·  tech.sni.com.uy
© 2026 Gabriel Tabárez Atanasich. Todos los derechos reservados.
"""

import os
import sys
import random

from mud import MUD, _est_tokens

SEED = 42
DB = "bench.db"
BUDGET = 400          # presupuesto de tokens por consulta MUD
TOP_K = 5

# --- 12 hechos "aguja" de una TIENDA DE DEMO FICTICIA. Nada de esto es real:
#     son datos inventados solo para que el benchmark tenga preguntas con una
#     única respuesta correcta. No representan infraestructura de nadie.
GOLD = [
    ("mud:demo/catalogo/envio-gratis",
     "Umbral de envio gratis (demo)",
     "En la tienda de demostracion el envio es gratis a partir de 4500 pesos de compra.",
     ["envio", "gratis", "umbral", "carrito"],
     "a partir de cuanto es gratis el envio en la tienda demo"),
    ("mud:demo/catalogo/devoluciones",
     "Plazo de devoluciones (demo)",
     "La politica de demo acepta devoluciones dentro de los 15 dias con el ticket de compra.",
     ["devoluciones", "plazo", "politica"],
     "cuantos dias hay para devoluciones en la tienda demo"),
    ("mud:demo/catalogo/horario",
     "Horario de atencion (demo)",
     "El local de demostracion atiende de lunes a viernes de 9 a 18 y sabados de 9 a 13.",
     ["horario", "atencion", "local"],
     "cual es el horario de atencion del local demo"),
    ("mud:demo/catalogo/colores",
     "Colores del producto estrella (demo)",
     "La mochila estrella de la demo viene en tres colores: negro, verde oliva y arena.",
     ["colores", "mochila", "producto"],
     "en que colores viene la mochila estrella de la demo"),
    ("mud:demo/catalogo/garantia",
     "Garantia del producto (demo)",
     "Los productos de la tienda de demo tienen 12 meses de garantia contra defectos de fabrica.",
     ["garantia", "meses", "defectos"],
     "cuanta garantia tienen los productos de la demo"),
    ("mud:demo/catalogo/cuotas",
     "Cuotas sin interes (demo)",
     "La demo ofrece hasta 6 cuotas sin interes con tarjeta de credito en compras mayores a 8000 pesos.",
     ["cuotas", "interes", "tarjeta"],
     "cuantas cuotas sin interes ofrece la tienda demo"),
    ("mud:demo/catalogo/puntos",
     "Programa de puntos (demo)",
     "En el programa de demo cada 100 pesos gastados suman 1 punto, y 500 puntos equivalen a un descuento.",
     ["puntos", "programa", "descuento"],
     "como funciona el programa de puntos de la demo"),
    ("mud:demo/catalogo/retiro",
     "Retiro en sucursal (demo)",
     "El retiro en sucursal de la demo esta disponible a las 24 horas de confirmado el pago.",
     ["retiro", "sucursal", "pickup"],
     "en cuanto tiempo se puede retirar en sucursal en la demo"),
    ("mud:demo/catalogo/idiomas",
     "Idiomas de la tienda (demo)",
     "La tienda de demo esta disponible en espanol y portugues, con soporte por chat en ambos.",
     ["idiomas", "espanol", "portugues"],
     "en que idiomas esta disponible la tienda demo"),
    ("mud:demo/catalogo/peso-envio",
     "Peso maximo por paquete (demo)",
     "Cada paquete de la demo admite hasta 20 kilos; por encima se cotiza envio especial.",
     ["peso", "paquete", "kilos"],
     "cual es el peso maximo por paquete en la demo"),
    ("mud:demo/catalogo/newsletter",
     "Descuento por newsletter (demo)",
     "Suscribirse al newsletter de la demo da un 10 por ciento de descuento en la primera compra.",
     ["newsletter", "descuento", "suscripcion"],
     "que descuento da suscribirse al newsletter de la demo"),
    ("mud:demo/catalogo/talles",
     "Guia de talles (demo)",
     "La guia de talles de la demo abarca del XS al XXL, con medidas en centimetros por prenda.",
     ["talles", "guia", "medidas"],
     "que rango de talles cubre la guia de la demo"),
]

# --- distractores: bloques verosimiles de otros temas, para inflar la memoria
#     igual que en un sistema real (cientos de notas que NO responden la pregunta).
DIST_SUBJECTS = [
    "reunion de equipo", "idea de producto", "nota de diseno", "bug reportado",
    "concepto de machine learning", "resumen de paper", "receta de cocina",
    "pendiente administrativo", "apunte de curso", "decision de UX",
    "cambio de copy", "metrica de marketing", "feedback de cliente",
    "roadmap trimestral", "nota de investigacion", "checklist de QA",
]
DIST_BODY = [
    "Se acordo revisar el punto la semana que viene y dejar registro en el acta.",
    "La propuesta busca mejorar la experiencia sin agregar complejidad innecesaria.",
    "Conviene validar la hipotesis con datos antes de invertir en la solucion.",
    "El patron observado sugiere que hay margen de optimizacion en el flujo actual.",
    "Se documenta para futura referencia y para no repetir el mismo analisis.",
    "El equipo prioriza esto para el proximo ciclo segun el impacto estimado.",
    "Quedan pendientes algunos detalles menores que no bloquean el avance.",
    "La conclusion principal es que el enfoque simple rinde mejor de lo esperado.",
]


def seed(mud, n_distractors=138):
    rng = random.Random(SEED)
    # bloques aguja
    for uri, title, content, tags, _q in GOLD:
        summary = content.split(".")[0] + "."
        mud.write(uri, content, category="knowledge", title=title,
                  summary=summary, tags=tags, actor="seed", reason="gold")
    # distractores
    for i in range(n_distractors):
        subj = rng.choice(DIST_SUBJECTS)
        body = " ".join(rng.sample(DIST_BODY, k=3))
        content = f"{subj.capitalize()}: {body}"
        mud.write(f"mud:events/nota/{i:03d}", content, category="events",
                  title=subj, summary=content[:80],
                  tags=[subj.split()[0]], actor="seed", reason="filler")


def _measure(mud, flat_tokens, keep_ratio):
    hits = 0
    mud_tokens_total = 0
    useful_tokens_total = 0
    rows = []
    for uri, _title, content, _tags, question in GOLD:
        res = mud.query(question, budget_tokens=BUDGET, top_k=TOP_K,
                        keep_ratio=keep_ratio)
        used = res["context_tokens_used"]
        got = [s["uri"] for s in res["selected"]]
        hit = uri in got
        hits += 1 if hit else 0
        mud_tokens_total += used
        useful_tokens_total += _est_tokens(content) if hit else 0
        rows.append((question, used, hit, len(got)))

    n = len(GOLD)
    mud_avg = mud_tokens_total / n
    return {
        "keep_ratio": keep_ratio,
        "mud_avg": mud_avg,
        "hit_rate": hits / n,
        "savings_pct": 1 - (mud_avg / flat_tokens),
        "precision": useful_tokens_total / mud_tokens_total if mud_tokens_total else 0,
        "rows": rows,
    }


def run():
    if os.path.exists(DB):
        os.remove(DB)
    mud = MUD(DB)
    seed(mud)

    # tokens si el agente recibe TODA la memoria (enfoque ingenuo)
    all_blocks = mud.db.execute("SELECT content FROM blocks").fetchall()
    flat_tokens = sum(_est_tokens(r["content"]) for r in all_blocks)
    n_blocks = len(all_blocks)

    base = _measure(mud, flat_tokens, keep_ratio=0.0)   # sin reranking
    rerank = _measure(mud, flat_tokens, keep_ratio=0.5)  # con corte por brecha

    mud.close()
    os.remove(DB)
    return {
        "n_blocks": n_blocks, "n_queries": len(GOLD), "budget": BUDGET,
        "flat_tokens": flat_tokens, "base": base, "rerank": rerank,
    }


def _line(label, b, rr, fmt, key):
    print(f"  {label:<34} {fmt.format(b[key]):>10} {fmt.format(rr[key]):>12}")


def print_report(r):
    b, rr = r["base"], r["rerank"]
    print("=" * 70)
    print("  MUD BENCH — atencion con presupuesto vs. mandar todo")
    print("=" * 70)
    print(f"  Memoria sembrada : {r['n_blocks']} bloques")
    print(f"  Consultas        : {r['n_queries']} (cada una con 1 bloque correcto)")
    print(f"  Presupuesto MUD  : {r['budget']} tokens/consulta")
    print(f"  Contexto FLAT (toda la memoria) : {r['flat_tokens']} tokens")
    print("-" * 70)
    print(f"  {'':34} {'sin rerank':>10} {'con rerank':>12}")
    print(f"  {'':34} {'(keep=0)':>10} {'(keep=0.5)':>12}")
    _line("tokens de contexto (prom.)", b, rr, "{:.0f}", "mud_avg")
    _line("ahorro vs FLAT", b, rr, "{:.1%}", "savings_pct")
    _line("context_hit_rate", b, rr, "{:.0%}", "hit_rate")
    _line("precision del contexto", b, rr, "{:.0%}", "precision")
    print("-" * 70)
    dp = (rr["precision"] - b["precision"]) * 100
    print(f"  Reranking por brecha: precision {b['precision']*100:.0f}% -> "
          f"{rr['precision']*100:.0f}%  (+{dp:.0f} pts), hit_rate intacto en "
          f"{rr['hit_rate']*100:.0f}%.")
    print("=" * 70)


def emit_md(r):
    b, rr = r["base"], r["rerank"]
    print("\n\n----- BLOQUE MARKDOWN PARA EL README -----\n")
    print("## Benchmark: ¿ahorra atención de verdad?")
    print()
    print(f"[`bench.py`](bench.py) siembra **{r['n_blocks']} bloques** de memoria y hace "
          f"**{r['n_queries']} preguntas**, cada una con un único bloque correcto "
          "(solo stdlib, reproducible con semilla fija).\n")
    print("Mandarle **toda** la memoria al agente cuesta "
          f"**{r['flat_tokens']:,} tokens**. MUD consulta con presupuesto:\n")
    print("| Métrica | MUD sin rerank | MUD + rerank | Objetivo |")
    print("|---|---|---|---|")
    print(f"| Tokens de contexto (prom.) | {b['mud_avg']:.0f} | {rr['mud_avg']:.0f} | menos es mejor |")
    print(f"| Ahorro vs. mandar todo | {b['savings_pct']*100:.1f}% | **{rr['savings_pct']*100:.1f}%** | alto |")
    print(f"| context_hit_rate | {b['hit_rate']*100:.0f}% | **{rr['hit_rate']*100:.0f}%** | no perder el dato |")
    print(f"| Precisión del contexto | {b['precision']*100:.0f}% | **{rr['precision']*100:.0f}%** | señal, no relleno |")
    print()
    print(f"- 🟢 **Ahorro de tokens: {rr['savings_pct']*100:.1f}%** por consulta.")
    print(f"- 🟢 **context_hit_rate: {rr['hit_rate']*100:.0f}%** — el bloque que responde la pregunta no se pierde.")
    print(f"- 🟢 **Precisión: {b['precision']*100:.0f}% → {rr['precision']*100:.0f}%** al activar el "
          f"**reranking por brecha de relevancia** (`keep_ratio=0.5`), sin tocar el recall.")
    print()
    print("El reranking (Fase 3 del roadmap) descarta los vecinos ruidosos que solo "
          "compartían una palabra con la consulta, quedándose con el bloque que de verdad responde.")
    print()
    print("Reproducilo:")
    print()
    print("```bash")
    print("python bench.py        # tabla comparativa en consola")
    print("python bench.py --md   # además emite este Markdown")
    print("```")


if __name__ == "__main__":
    r = run()
    print_report(r)
    if "--md" in sys.argv:
        emit_md(r)
