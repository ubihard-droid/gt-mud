# MUD — Memoria Unificada Distribuida

> Una fuente de verdad que varios agentes de IA leen y escriben **sin pisarse**,
> entregando a cada uno **solo la atención que necesita** — no toda la memoria.

![status](https://img.shields.io/badge/estado-draft%20evolutivo-blue)
![python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![deps](https://img.shields.io/badge/demo-solo%20stdlib-success)
![license](https://img.shields.io/badge/licencia-propietaria-lightgrey)

**Autor:** Gabriel Tabárez Atanasich — Director, División Informática
**Marca:** SNI SOFT by Tirnel · [tech.sni.com.uy](https://tech.sni.com.uy)
**Método:** Algoritmo Loop Espiral GT

---

## ¿Qué es?

En sistemas multiagente, cada agente suele recibir *todo* el contexto: sistema
completo, historial completo, configuración completa. Eso infla el contexto,
sube el costo y la latencia, y empeora el razonamiento.

**MUD invierte el modelo:**

```
Intención del agente → router de memoria → contexto mínimo relevante → mejor decisión
```

Los agentes no cargan la memoria: resuelven **punteros** hacia la porción exacta
que necesitan, con **presupuesto de tokens**, **permisos**, **trazabilidad** y
**consistencia verificable**.

## Piezas clave

| Pieza | Para qué |
|---|---|
| **MUD URI** | Identificar cada bloque de memoria (`mud:categoria/dominio/nombre@version`) |
| **Content hash** | Integridad e invalidación de caché (ETag) |
| **Event log** | Auditoría, replay y rollback |
| **Query planner** | Recuperar solo lo relevante que entra en el presupuesto |
| **Índice híbrido** | Exacto · BM25 · vectorial · grafo · temporal |
| **Memory tiers** | Working → episodic → semantic → procedural |
| **Vault / ACL** | Los secretos **no** entran al prompt: se referencian, se redactan |
| **Consolidation engine** | Convierte eventos crudos en conocimiento estable |

## Contenido del repo

| Archivo | Descripción |
|---|---|
| [`MUD-V3.md`](MUD-V3.md) | Especificación completa de la arquitectura (29 secciones) |
| [`mud.py`](mud.py) | Implementación MVP: SQLite + FTS5, concurrencia optimista |

## Probarlo en 10 segundos

El demo corre con **solo la librería estándar de Python** (sin instalar nada):

```bash
python mud.py demo
```

Muestra dos agentes (Claude y Hermes) compartiendo una sola verdad, un tercero
(Gemini) **bloqueado** al escribir sobre una versión vieja, y la auditoría de
quién tocó qué. *Una verdad, varios agentes, cero pisadas.*

### Levantar la API (opcional)

```bash
pip install fastapi uvicorn
python mud.py serve   # http://127.0.0.1:8077
```

Endpoints: `POST /query` · `POST /write` · `POST /resolve` · `GET /audit` · `GET /health`

## Benchmark: ¿ahorra atención de verdad?

[`bench.py`](bench.py) siembra **150 bloques** de memoria y hace **12 preguntas**,
cada una con un único bloque correcto. Compara dos estrategias sobre la misma memoria
(solo stdlib, reproducible con semilla fija):

| Estrategia | Tokens de contexto | ¿Llega el dato correcto? |
|---|---|---|
| **FLAT** — mandar toda la memoria al agente | **8.758** | sí, pero ahogado en ruido |
| **MUD** — consulta con presupuesto | **199** (promedio) | **100%** de las veces |

- 🟢 **Ahorro de tokens: 97.7%** por consulta.
- 🟢 **context_hit_rate: 100%** — el bloque que responde la pregunta no se pierde.
- 🟡 **Precisión del contexto: 13%** — con `top_k=5` el agente recibe el bloque correcto
  **+ vecinos cercanos**. Subir esta precisión es justo lo que ataca el **reranking de la
  Fase 3** del roadmap.

> El ahorro de atención y el recall ya están; la precisión es la próxima palanca, no un
> número maquillado.

Reproducilo:

```bash
python bench.py        # tabla en consola
python bench.py --md   # además emite el Markdown de esta tabla
```

## Manifiesto

> El contexto no es almacenamiento.
> La memoria no es un volcado de archivos.
> El conocimiento no es infinito.
> Los secretos no pertenecen al prompt.
> Cada bloque debe ser verificable.
> Cada escritura debe ser auditable.
> Cada lectura debe respetar presupuesto.
> Cada agente debe recibir solo la atención necesaria.

---

© 2026 Gabriel Tabárez Atanasich. Todos los derechos reservados.
