# MUD v3 — Memoria Unificada Distribuida

## Arquitectura de Atención, Estado y Conocimiento para Sistemas Multiagente

**Versión:** 3.0  
**Fecha:** 2026-08-17  
**Estado:** Draft evolutivo  
**Nombre:** MUD — Memoria Unificada Distribuida  
**Enfoque:** Multiagente IA, contexto bajo demanda, estado verificable, memoria con ciclo de vida.  
**Autor:** Gabriel Tabárez Atanasich — Director, División Informática  
**Marca:** SNI SOFT by Tirnel · tech.sni.com.uy  
**Método:** Algoritmo Loop Espiral GT  
**© 2026 Gabriel Tabárez Atanasich. Todos los derechos reservados.**

---

## 1. Visión

MUD v3 evoluciona la idea original de una base de memoria compartida hacia una **arquitectura de atención distribuida**.

El principio central es:

> Los agentes no deben cargar toda la memoria en su contexto.  
> Deben poder resolver punteros hacia la porción exacta de memoria que necesitan, con presupuesto de tokens, permisos, trazabilidad y consistencia verificable.

MUD resuelve cuatro problemas fundamentales:

1. **Saturación de contexto**  
   Los modelos no reciben documentos completos, sino bloques relevantes, resúmenes o punteros.

2. **Redundancia de estado**  
   La memoria persistente es una única fuente de verdad distribuida y versionada.

3. **Coherencia multiagente**  
   Varios agentes pueden leer, escribir y derivar conocimiento sin pisarse entre sí.

4. **Seguridad y auditabilidad**  
   La memoria sensible se puede consultar sin exponer secretos directamente al contexto del modelo.

---

## 2. Principios de Diseño

### 2.1 Contexto como recurso escaso

El contexto no es almacenamiento. Es atención cara y limitada.

Por tanto:

- Se inyectan solo bloques necesarios.
- Se priorizan resúmenes cuando el detalle no es imprescindible.
- Se usan punteros para lectura diferida.
- Se aplica presupuesto de tokens por consulta.

### 2.2 Memoria como contenido direccionable

Cada bloque de memoria se identifica por su hash de contenido.

Esto permite:

- Detectar cambios.
- Invalidar cachés.
- Verificar integridad.
- Reconstruir estado.
- Evitar duplicados.

### 2.3 Escritura basada en eventos

La memoria no se sobrescribe de forma opaca.

Se registra como una secuencia de eventos:

- Creación.
- Parche.
- Reemplazo.
- Deprecación.
- Consolidación.
- Borrado lógico.

Esto habilita auditoría, replay y rollback.

### 2.4 Lectura con presupuesto

Cada consulta define cuántos tokens puede gastar.

El sistema devuelve:

- Bloques completos si hay presupuesto.
- Resúmenes si el presupuesto es bajo.
- Punteros si el agente puede resolver después.
- Omisiones explícitas cuando no hay espacio.

### 2.5 Memoria con ciclo de vida

La memoria no es eterna por defecto.

Tiene estados:

- Activa.
- Fría.
- Consolidada.
- Archivada.
- Deprecada.
- Eliminada lógicamente.

### 2.6 Seguridad por diseño

Los secretos no deberían entrar automáticamente en contexto.

MUD soporta:

- Referencias a vault.
- Redacción automática.
- Permisos por agente.
- Campos enmascarados.
- Auditoría de acceso.

---

## 3. Problema que Resuelve

En sistemas multiagente tradicionales, cada agente suele recibir:

- Sistema completo.
- Historial completo.
- Documentación completa.
- Configuración completa.
- Estado previo completo.

Esto produce:

```text
Contexto inflado → mayor costo → mayor latencia → mayor confusión → peor razonamiento
```

MUD propone:

```text
Intención del agente → router de memoria → contexto mínimo relevante → mejor decisión
```

---

## 4. Diagrama General de Arquitectura

```text
                         ┌────────────────────┐
                         │      AGENTES       │
                         │   Gemini, Claude,  │
                         │ OpenCode, Hermes…  │
                         └─────────┬──────────┘
                                   │
                                   │ Query / Resolve / Write
                                   ▼
                        ┌─────────────────────┐
                        │    MUD GATEWAY      │
                        │  API + Auth + ACL   │
                        └─────────┬───────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ QUERY PLANNER│  │ WRITE LEDGER │  │  SUBSCRIBE   │
        │ Context Router│ │ Event Sourcing│ │  Change Bus  │
        └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
               │                 │                 │
               ▼                 ▼                 ▼
        ┌──────────────────────────────────────────────┐
        │              ÍNDICE HÍBRIDO                  │
        │  Exact KV | BM25 | Vector | Grafo | Temporal │
        └──────────────────────┬───────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │ MEMORY STORE │     │  EVENT LOG   │     │ VAULT / ACL  │
  │ CAS + Blobs  │     │ Append-only  │     │ Secret Refs  │
  └──────────────┘     └──────────────┘     └──────────────┘
          │
          ▼
  ┌──────────────────────────────┐
  │     CONSOLIDATION ENGINE     │
  │ Resumen, decaimiento, GC     │
  └──────────────────────────────┘
```

---

## 5. Capas del Sistema

### 5.1 Capa de Agentes

Los agentes son consumidores efímeros de contexto.

No poseen la memoria principal. Solo mantienen:

- Contexto de sesión.
- Caché temporal.
- Punteros resueltos.
- Estado de tarea actual.

Ejemplos:

- Gemini.
- Claude Code.
- OpenCode.
- Hermes.
- Agentes especializados.
- Workers autónomos.

### 5.2 MUD Gateway

Punto único de entrada.

Responsabilidades:

- Autenticación de agentes.
- Autorización por categoría y operación.
- Aplicación de presupuesto de tokens.
- Validación de esquemas.
- Redacción de secretos.
- Métricas de acceso.

Endpoints conceptuales:

```text
POST /query
POST /resolve
POST /write
POST /subscribe
POST /compact
GET  /audit
```

### 5.3 Query Planner

Es el router de atención.

Recibe una intención y decide:

- Qué categorías buscar.
- Qué índices usar.
- Qué profundidad devolver.
- Qué bloques omitir.
- Qué resumen generar.
- Qué punteros dejar para resolución diferida.

### 5.4 Índice Híbrido

MUD v3 no depende solo de embeddings.

Usa varios índices combinados:

| Índice | Uso principal |
|---|---|
| Exact KV | Búsqueda por claves exactas. |
| BM25 / Full-text | Términos técnicos, nombres, IDs. |
| Vectorial | Similitud semántica. |
| Grafo | Relaciones entre bloques. |
| Temporal | Recencia, versiones, sesiones. |

### 5.5 Memory Store

Almacenamiento persistente de bloques.

Puede ser híbrido:

- Archivos Markdown/JSON para memoria legible.
- Object storage para blobs.
- Base de datos relacional para metadatos.
- Vector DB para embeddings.
- Content-addressable storage para integridad.

### 5.6 Event Log

Registro inmutable de cambios.

Cada escritura produce un evento.

Permite:

- Auditoría.
- Replay.
- Rollback.
- Reconstrucción de memoria.
- Detección de conflictos.

### 5.7 Consolidation Engine

Proceso asíncrono que transforma memoria cruda en conocimiento estable.

Funciones:

- Resumir episodios.
- Fusionar memorias similares.
- Detectar contradicciones.
- Aplicar decaimiento.
- Promover memoria episódica a semántica.
- Generar índices derivados.

### 5.8 Vault / Policy Engine

Controla acceso a información sensible.

Responsabilidades:

- Evitar exposición directa de secretos.
- Devolver referencias en lugar de valores.
- Redactar PII.
- Aplicar políticas por agente.
- Registrar accesos sensibles.

---

## 6. Modelo de Memoria

MUD v3 usa dos dimensiones:

1. **Categoría funcional**
2. **Tipo cognitivo de memoria**

Esto permite organizar tanto el *qué* como el *para qué*.

---

## 7. Categorías Funcionales

### 7.1 Behavior

Directivas de comportamiento del sistema.

Contiene:

- Personalidad.
- Tono.
- Límites.
- Formato de salida.
- Reglas de seguridad.
- Restricciones de herramientas.

Ejemplo:

```json
{
  "category": "behavior",
  "key": "agent.output_style",
  "summary": "Respuestas técnicas, concisas y con ejemplos accionables."
}
```

### 7.2 Task

Contexto de la tarea activa.

Contiene:

- Prompt actual.
- Objetivo.
- Criterios de aceptación.
- Entradas del usuario.
- Estado de ejecución.
- Resultados parciales.

Ejemplo:

```json
{
  "category": "task",
  "key": "task.mud-evolution",
  "summary": "Evolucionar MUD v1 hacia una arquitectura de atención distribuida."
}
```

### 7.3 Environment

Infraestructura y contexto técnico.

Contiene:

- Rutas de archivos.
- Configuración de servicios.
- Puertos.
- Esquemas de base de datos.
- Variables de entorno.
- Versiones.
- Referencias a secretos.

Ejemplo:

```json
{
  "category": "environment",
  "key": "env.db.production",
  "summary": "Configuración de PostgreSQL para producción."
}
```

### 7.4 Metrics / Tendencia

Histórico numérico y analítico.

Contiene:

- Métricas de rendimiento.
- Logs agregados.
- Distribuciones.
- Patrones de uso.
- Errores recurrentes.
- Costes por consulta.
- Probabilidades y tendencias.

Ejemplo:

```json
{
  "category": "metrics",
  "key": "metrics.context_miss_rate",
  "summary": "Tasa de fallos de recuperación contextual en los últimos 7 días."
}
```

### 7.5 Knowledge

Conocimiento estable del dominio.

Contiene:

- Decisiones arquitectónicas.
- Conceptos.
- Reglas de negocio.
- Lecciones aprendidas.
- Hechos verificados.

Ejemplo:

```json
{
  "category": "knowledge",
  "key": "knowledge.mud.pointer_strategy",
  "summary": "Los agentes deben recibir punteros antes que documentos completos."
}
```

### 7.6 Events

Memoria episódica cruda.

Contiene:

- Interacciones.
- Ejecuciones.
- Errores.
- Cambios de estado.
- Decisiones puntuales.

Ejemplo:

```json
{
  "category": "events",
  "key": "event.2026-08-17.agent.claude.task.mud-evolution",
  "summary": "Claude propuso una mejora de punteros para MUD."
}
```

---

## 8. Tipos Cognitivos de Memoria

### 8.1 Working Memory

Memoria caliente de sesión.

Características:

- Vida corta.
- Alta prioridad.
- Acceso inmediato.
- Muy contextual.

Ejemplos:

- Último mensaje del usuario.
- Tarea actual.
- Variables temporales.
- Punteros recientemente usados.

TTL sugerido:

```text
minutos a horas
```

### 8.2 Episodic Memory

Registro de eventos y experiencias.

Características:

- Temporal.
- Detallada.
- Auditable.
- No necesariamente consolidada.

Ejemplos:

- Una ejecución de agente.
- Una conversación.
- Un error concreto.
- Una decisión tomada en una sesión.

TTL sugerido:

```text
días a semanas
```

### 8.3 Semantic Memory

Conocimiento consolidado.

Características:

- Estable.
- Resumida.
- Reutilizable.
- Versionada.

Ejemplos:

- Arquitectura de MUD.
- Reglas de seguridad.
- Configuración base.
- Decisiones confirmadas.

TTL sugerido:

```text
permanente hasta deprecación
```

### 8.4 Procedural Memory

Procedimientos, habilidades y runbooks.

Características:

- Orientada a acción.
- Ejecutable o accionable.
- Asociada a herramientas.

Ejemplos:

- Cómo desplegar.
- Cómo recuperar un fallo.
- Cómo consultar MUD.
- Cómo validar un cambio.

TTL sugerido:

```text
permanente con versiones
```

---

## 9. Estructura de Identidad

### 9.1 MUD URI

Formato recomendado:

```text
mud:<category>/<namespace>/<name>@<version_or_hash>
```

Ejemplos:

```text
mud:behavior/agents/output-style@v3
mud:task/mud-evolution/current@v1
mud:environment/db/production@sha256:9f2c...
mud:metrics/context-miss-rate@2026-08-17
mud:knowledge/mud/pointer-strategy@v2
```

### 9.2 Fragmentos internos

Para apuntar a una sección interna:

```text
mud:environment/db/production@v12#pool_size
```

Esto significa:

- Categoría: `environment`
- Dominio: `db`
- Nombre: `production`
- Versión: `v12`
- Bloque interno: `pool_size`

---

## 10. Objeto de Memoria

Cada entrada de memoria se llama **Memory Object**.

```json
{
  "mud_id": "mud:environment/db/production@v12",
  "category": "environment",
  "memory_type": "semantic",
  "kind": "config",
  "title": "Configuración de base de datos de producción",
  "summary": "Parámetros principales de PostgreSQL en producción.",
  "content_hash": "sha256:8f2a...",
  "version": 12,
  "state": "active",
  "created_at": "2026-08-10T09:00:00Z",
  "updated_at": "2026-08-17T12:00:00Z",
  "ttl": null,
  "importance": 0.85,
  "access_policy": "restricted",
  "tags": ["db", "postgres", "production"],
  "links": [
    "mud:knowledge/db/schema@v7",
    "mud:environment/vault/db-password@v1"
  ],
  "provenance": {
    "created_by": "claude-code",
    "validated_by": "human:admin",
    "source": "deployment-manifest"
  },
  "embedding_ref": "vec:env/db/production/v12",
  "storage": {
    "backend": "cas",
    "uri": "cas/sha256/8f2a....json"
  }
}
```

---

## 11. Puntero MUD

Un puntero es una referencia ligera que un agente puede pasar en contexto sin cargar el contenido completo.

```json
{
  "pointer": "mud:environment/db/production@v12#pool_size",
  "content_hash": "sha256:8f2a...",
  "etag": "v12-8f2a",
  "view": "summary",
  "budget_tokens": 120,
  "fallback": "return_summary_only",
  "expires_at": "2026-08-17T18:00:00Z"
}
```

### Tipos de vista

| View | Descripción |
|---|---|
| `pointer` | Solo URI y hash. |
| `summary` | Resumen breve. |
| `block` | Bloque específico. |
| `full` | Contenido completo. |
| `lazy` | Se resuelve solo si el agente lo solicita. |

---

## 12. Protocolo de Consulta

### 12.1 Query

Un agente consulta al MUD Gateway.

```json
{
  "query_id": "q_01J9X...",
  "agent": "hermes",
  "intent": "Necesito la configuración de conexión a la base de datos de producción",
  "budget_tokens": 800,
  "categories": ["environment", "knowledge"],
  "memory_types": ["semantic", "procedural"],
  "filters": {
    "tags": ["db", "production"]
  },
  "top_k": 5,
  "include_summaries": true,
  "include_pointers": true,
  "allow_full_blocks": false
}
```

### 12.2 Respuesta

```json
{
  "query_id": "q_01J9X...",
  "confidence": 0.91,
  "context_tokens_used": 412,
  "budget_tokens": 800,
  "selected": [
    {
      "mud_id": "mud:environment/db/production@v12",
      "score": 0.94,
      "view": "summary",
      "summary": "Configuración PostgreSQL de producción: host, puerto, pool, timeouts.",
      "pointer": "mud:environment/db/production@v12",
      "content_hash": "sha256:8f2a..."
    },
    {
      "mud_id": "mud:environment/db/production@v12#pool_size",
      "score": 0.90,
      "view": "block",
      "content": {
        "pool_size": 20
      },
      "pointer": "mud:environment/db/production@v12#pool_size",
      "content_hash": "sha256:1c4d..."
    }
  ],
  "omitted": [
    {
      "mud_id": "mud:environment/db/replicas@v3",
      "reason": "budget_exceeded",
      "pointer": "mud:environment/db/replicas@v3"
    }
  ],
  "fallback": null
}
```

### 12.3 Cálculo de `confidence`

El campo `confidence` de la respuesta indica cuánto confía el planner en que el
contexto devuelto responde la intención. Debe ser reproducible, no un número
arbitrario. Definición sugerida:

```text
confidence = clamp(
    0.6 * top_score
  + 0.2 * score_margin        # top_score - segundo_score (separación del mejor match)
  + 0.2 * coverage,           # fracción de la intención cubierta por lo recuperado
    0.0, 1.0)
```

Donde:

- `top_score`: score del mejor bloque seleccionado.
- `score_margin`: qué tan destacado está el mejor resultado frente al siguiente
  (margen alto ⇒ recuperación menos ambigua).
- `coverage`: proporción de sub-intenciones o filtros solicitados que quedaron
  cubiertos por los bloques devueltos (no omitidos por presupuesto o ACL).

Si `confidence` cae por debajo de un umbral configurable, el planner debería
activar `fallback_broad` (ver 16.3) en lugar de responder con contexto pobre.

---

## 13. Protocolo de Resolución

Si el agente necesita el contenido completo:

```json
{
  "agent": "hermes",
  "pointers": [
    "mud:environment/db/production@v12#pool_size"
  ],
  "view": "block",
  "max_tokens": 300,
  "redact_secrets": true
}
```

Respuesta:

```json
{
  "resolved": [
    {
      "pointer": "mud:environment/db/production@v12#pool_size",
      "content": {
        "pool_size": 20
      },
      "content_hash": "sha256:1c4d...",
      "version": 12,
      "redacted_fields": []
    }
  ]
}
```

---

## 14. Protocolo de Escritura

### 14.1 Escritura optimista

Para evitar conflictos, cada escritura debe referenciar el estado previo.

```json
{
  "op": "patch",
  "mud_uri": "mud:environment/db/production@v12",
  "actor": "claude-code",
  "reason": "Ajustar pool_size por carga observada",
  "before_hash": "sha256:8f2a...",
  "lease_id": "lease_9f3e...",
  "patch": [
    {
      "op": "replace",
      "path": "/pool_size",
      "value": 25
    }
  ]
}
```

### 14.2 Evento generado

```json
{
  "event_id": "evt_01J9Y...",
  "type": "patched",
  "mud_uri": "mud:environment/db/production@v13",
  "previous_uri": "mud:environment/db/production@v12",
  "actor": "claude-code",
  "timestamp": "2026-08-17T15:10:00Z",
  "before_hash": "sha256:8f2a...",
  "after_hash": "sha256:b7e1...",
  "reason": "Ajustar pool_size por carga observada",
  "trace_id": "trace_7d2c..."
}
```

---

## 15. Consistencia y Concurrencia

### 15.1 Modelo recomendado

MUD v3 usa:

- **Event sourcing** para cambios.
- **Content hashing** para integridad.
- **Optimistic concurrency** para escrituras.
- **Leases temporales** para ediciones largas.
- **Tombstones** para borrado lógico.

### 15.2 Conflictos

Cuando dos agentes escriben el mismo objeto:

1. Se detecta conflicto por `before_hash`.
2. Se rechaza el segundo write si no hay lease válido.
3. Se genera un evento `conflict_detected`.
4. El Consolidation Engine puede proponer fusión semántica.
5. Si la memoria es crítica, requiere revisión humana.

### 15.3 Estrategias de resolución

| Tipo de memoria | Estrategia |
|---|---|
| Configuración | Last-writer-wins con validación. |
| Conocimiento | Merge semántico supervisado. |
| Métricas | Agregación automática. |
| Tareas | Estado más reciente con historial. |
| Secretos | Solo escritura vía vault autorizado. |

### 15.4 Consistencia de los índices (proyecciones)

El **Event Log es la única fuente de verdad**. El Índice Híbrido (KV, BM25,
vector, grafo, temporal) son **proyecciones derivadas** del log, no autoridad.
Por lo tanto la búsqueda es **eventualmente consistente**: tras un write, hay una
ventana en la que los índices todavía no reflejan el cambio.

Reglas para que esto no rompa nada:

- Cada índice guarda el `event_offset` (o `after_hash`) del último evento aplicado.
- Un reindexador consume el log de forma incremental y actualiza cada proyección.
- Toda respuesta puede incluir el `content_hash` real del bloque; el agente valida
  contra él antes de confiar en un resultado (un hit de índice apuntando a un hash
  viejo se descarta y se reencola para reindexar).
- Lecturas por `mud_uri` + `content_hash` (exactas) **sí** son fuertemente
  consistentes; solo la búsqueda semántica/full-text es eventual.
- Métrica `stale_pointer_rate` (ver 20.2) vigila el desfase.

### 15.5 Ciclo de vida del embedding

`embedding_ref` en el Memory Object apunta a un vector que corresponde a una
**versión y hash específicos** del bloque. Cuando el bloque cambia (`patch` /
`replace` ⇒ nuevo `content_hash` y `version`), el embedding anterior queda obsoleto.

Para evitar punteros de embedding corruptos silenciosos:

- El evento de escritura marca el `embedding_ref` como `stale`.
- El reindexador regenera el embedding contra el nuevo contenido y publica un
  `embedding_ref` nuevo versionado (ej. `vec:env/db/production/v13`).
- Hasta que se regenere, la búsqueda vectorial ignora la versión `stale` y cae en
  BM25/exacta para ese bloque (degradación, no resultado incorrecto).
- El GC (18.4) elimina embeddings huérfanos de versiones ya deprecadas.

---

## 16. Recuperación Híbrida

### 16.1 Pipeline de recuperación

```text
Consulta del agente
        │
        ▼
Normalización de intención
        │
        ▼
Filtro ACL y presupuesto
        │
        ▼
Búsqueda exacta / KV
        │
        ▼
Búsqueda BM25
        │
        ▼
Búsqueda vectorial
        │
        ▼
Expansión por grafo de dependencias
        │
        ▼
Filtrado por recencia y estado
        │
        ▼
Reranking
        │
        ▼
Compactación de contexto
        │
        ▼
Redacción de secretos
        │
        ▼
Respuesta con punteros y bloques
```

### 16.2 Fórmula de puntuación sugerida

```text
raw_score =
  0.35 * semantic_similarity
+ 0.25 * lexical_match
+ 0.15 * recency
+ 0.10 * importance
+ 0.10 * graph_relevance
+ 0.05 * access_frequency
- 0.10 * staleness_penalty

score = clamp(raw_score, 0.0, 1.0)
```

> **Nota de consistencia:** los pesos positivos suman 1.0 y `staleness_penalty`
> está normalizado en `[0,1]`, por lo que `raw_score` puede quedar levemente
> negativo; el `clamp` lo evita. El control de acceso **no** se modela como término
> del score (podía volverlo negativo y distorsionar el ranking): se aplica como
> **filtro duro previo** en el pipeline de recuperación (ver 16.1, paso "Filtro ACL
> y presupuesto"). Un bloque sin permiso no puntúa bajo: no entra.

### 16.3 Presupuesto

El sistema no solo devuelve lo más relevante, sino lo que cabe.

Modos:

| Modo | Comportamiento |
|---|---|
| `strict` | No excede el presupuesto. |
| `summary_first` | Devuelve resúmenes y punteros. |
| `pointer_only` | Solo punteros si el budget es mínimo. |
| `fallback_broad` | Si no hay match, devuelve contexto general breve. |

### 16.4 Reranking por brecha de relevancia (implementado)

La recuperación por `top_k` tiene un problema de **precisión**: junto al bloque que
responde la intención entran vecinos que solo compartían una palabra con la
consulta. El contexto se llena de señal débil.

El **corte por brecha de relevancia** lo resuelve sin costo extra: el bloque
correcto casi siempre tiene un score BM25 **muy superior** al del ruido. En vez de
devolver ciegamente `top_k`, se calcula la relevancia del mejor resultado y se
descartan los bloques por debajo de un umbral relativo.

```text
relevancia = -bm25(bloque)          # menor bm25 = mejor, así que negamos
mejor      = relevancia del top-1
se conserva el bloque  ⇔  relevancia ≥ mejor × keep_ratio
```

- `keep_ratio = 0.0` → desactivado (comportamiento `top_k` clásico).
- `0 < keep_ratio < 1` → descarta lo que valga menos que `keep_ratio` del top.
  El #1 siempre se conserva (nunca devuelve vacío ante un match).
- Sube la precisión **sin tocar el recall** cuando hay un ganador claro, y de paso
  gasta menos tokens (menos bloques ruidosos en contexto).

Es la materialización de la **Fase 3 (retrieval híbrido → reranking)** del roadmap.

#### Resultado medido

Banco de pruebas (`bench.py`): 150 bloques de memoria, 12 consultas con una única
respuesta correcta cada una, presupuesto de 400 tokens. Frente a mandarle **toda**
la memoria al agente:

| Métrica | MUD sin rerank | MUD + rerank (`keep_ratio=0.5`) |
|---|---|---|
| Tokens de contexto (promedio) | 110 | **28** |
| Ahorro vs. mandar todo | 98.7 % | **99.7 %** |
| `context_hit_rate` | 100 % | **100 %** |
| Precisión del contexto | 20 % | **80 %** |

El reranking sube la precisión **+60 puntos** manteniendo el recall intacto. El
`keep_ratio` es una perilla precisión/recall que se puede barrer para elegir el
óptimo con datos.

---

## 17. Seguridad y Permisos

### 17.1 ACL por agente

```json
{
  "agent": "hermes",
  "permissions": {
    "behavior": ["read"],
    "task": ["read", "write"],
    "environment": ["read:redacted"],
    "metrics": ["read", "write"],
    "knowledge": ["read", "write"],
    "events": ["read", "append"]
  }
}
```

### 17.2 Niveles de acceso

| Nivel | Significado |
|---|---|
| `none` | Sin acceso. |
| `read` | Lectura normal. |
| `read:redacted` | Lectura con campos sensibles ocultos. |
| `read:pointer_only` | Solo puede obtener punteros. |
| `write` | Escritura permitida. |
| `append` | Solo añadir eventos. |
| `admin` | Gestión de políticas y borrado. |

### 17.3 Referencias a secretos

En lugar de exponer secretos:

```json
{
  "database_password": "{{vault:prod/db_password}}"
}
```

El agente puede saber que existe, pero no ve el valor.

Si necesita usarlo, el runtime lo resuelve en un executor seguro:

```text
Agent context:
  database_password = {{vault:prod/db_password}}

Executor runtime:
  database_password = real_secret_value
```

### 17.4 Redacción automática

Campos candidatos:

- API keys.
- Tokens.
- Contraseñas.
- Emails.
- IPs internas sensibles.
- Credenciales DB.
- Certificados.
- Claves privadas.

Ejemplo:

```json
{
  "api_key": "REDACTED:api_key",
  "db_password": "REDACTED:vault_ref",
  "user_email": "REDACTED:pii"
}
```

---

## 18. Ciclo de Vida de la Memoria

### 18.1 Estados

```text
draft → active → consolidated → archived → deprecated → tombstoned
```

### 18.2 Promoción

```text
Working Memory
      │
      ▼
Episodic Memory
      │
      ▼
Semantic Memory
      │
      ▼
Procedural Memory
```

Ejemplo:

1. Un agente resuelve un error.
2. Se guarda evento episódico.
3. El consolidador detecta patrón.
4. Genera conocimiento semántico.
5. Si es accionable, crea runbook procedural.

### 18.3 Decaimiento

Cada memoria puede tener una puntuación de vida:

```text
life_score =
  importance * 0.4
+ access_frequency * 0.3
+ recency * 0.2
+ link_count * 0.1
```

Si `life_score` baja:

- Se enfría.
- Se resume.
- Se archiva.
- Se elimina lógicamente si corresponde.

### 18.4 Garbage Collection

El GC debe buscar:

- Punteros huérfanos.
- Bloques sin referencias.
- Versiones obsoletas.
- Eventos expirados.
- Memorias duplicadas.
- Resúmenes inconsistentes.

---

## 19. Invalidación de Caché

Cada bloque usa `content_hash` como ETag.

### 19.1 Estrategia

```text
If-None-Match: sha256:8f2a...
```

Si el hash cambió:

```text
200 OK + nuevo contenido
```

Si no cambió:

```text
304 Not Modified
```

### 19.2 Canales de cambio

Los agentes pueden suscribirse:

```text
subscribe:mud:environment/db/production
subscribe:category:metrics
subscribe:agent:hermes:task
```

Evento:

```json
{
  "event": "memory.updated",
  "mud_uri": "mud:environment/db/production@v13",
  "previous_hash": "sha256:8f2a...",
  "new_hash": "sha256:b7e1...",
  "actor": "claude-code",
  "timestamp": "2026-08-17T15:10:00Z"
}
```

---

## 20. Observabilidad

### 20.1 Trazas

Cada consulta debe tener:

```text
trace_id
query_id
agent_id
budget_tokens
retrieval_latency
selected_blocks
omitted_blocks
confidence
tokens_saved
```

### 20.2 Métricas clave

| Métrica | Descripción |
|---|---|
| `context_hit_rate` | Porcentaje de consultas con contexto útil. |
| `context_miss_rate` | Consultas sin recuperación relevante. |
| `token_savings` | Tokens ahorrados por punteros/resúmenes. |
| `retrieval_latency_p95` | Latencia de recuperación. |
| `write_conflict_rate` | Conflictos de escritura. |
| `stale_pointer_rate` | Punteros inválidos detectados. |
| `secret_leak_attempts` | Intentos de acceso sensible. |
| `consolidation_backlog` | Episodios pendientes de consolidar. |

### 20.3 Auditoría

Cada acceso sensible registra:

```json
{
  "audit_id": "aud_01J9Z...",
  "agent": "hermes",
  "mud_uri": "mud:environment/db/production@v13",
  "operation": "resolve",
  "view": "block",
  "redacted": true,
  "timestamp": "2026-08-17T15:12:00Z",
  "policy_applied": "environment:redacted"
}
```

---

## 21. Ejemplo de Flujo Completo

### 21.1 Agente pregunta

```text
Hermes necesita saber el tamaño del pool de conexión de PostgreSQL en producción.
```

### 21.2 Consulta MUD

```json
{
  "agent": "hermes",
  "intent": "Obtener pool_size de PostgreSQL producción",
  "budget_tokens": 200,
  "categories": ["environment"],
  "memory_types": ["semantic"],
  "include_summaries": true,
  "allow_full_blocks": true
}
```

### 21.3 MUD responde

```json
{
  "selected": [
    {
      "mud_id": "mud:environment/db/production@v12#pool_size",
      "score": 0.97,
      "view": "block",
      "content": {
        "pool_size": 20
      },
      "pointer": "mud:environment/db/production@v12#pool_size"
    }
  ],
  "context_tokens_used": 48
}
```

### 21.4 Resultado

El agente no recibe toda la infraestructura.

Solo recibe:

```json
{
  "pool_size": 20
}
```

Con puntero para trazabilidad:

```text
mud:environment/db/production@v12#pool_size
```

---

## 22. Estructura de Almacenamiento Recomendada

```text
/mud
├── cas/
│   └── sha256/
│       ├── 8f2a....json
│       ├── 1c4d....json
│       └── b7e1....json
├── events/
│   ├── 2026-08-17/
│   │   ├── evt_01J9X.json
│   │   └── evt_01J9Y.json
├── indices/
│   ├── exact/
│   ├── fts/
│   ├── vector/
│   └── graph/
├── policies/
│   ├── acl.json
│   ├── redaction.json
│   └── retention.json
├── memory/
│   ├── working/
│   ├── episodic/
│   ├── semantic/
│   └── procedural/
├── vault_refs/
│   ├── prod.json
│   └── staging.json
└── observability/
    ├── audit/
    ├── metrics/
    └── traces/
```

---

## 23. Implementación Mínima Viable

### 23.1 MVP local

Objetivo: validar el concepto sin infraestructura pesada.

Componentes:

```text
Gateway: FastAPI
Metadata: SQLite
Full-text: SQLite FTS5
Vectors: sqlite-vec / LanceDB / FAISS local
Storage: filesystem + hash SHA-256
Events: JSON Lines append-only
Cache: filesystem ETag
Pub/Sub: polling o Redis opcional
```

### 23.2 MVP distribuido

Para producción:

```text
Gateway: FastAPI / gRPC
Metadata: PostgreSQL
Vectors: pgvector / Qdrant / Weaviate
Full-text: Meilisearch / OpenSearch
Storage: S3 compatible
Events: Kafka / NATS JetStream
Cache: Redis
Secrets: Vault
Observability: OpenTelemetry + Prometheus + Grafana
```

---

## 24. Roadmap de Evolución

### Fase 0 — Núcleo de punteros

Objetivo: que los agentes puedan referirse a memoria sin cargarla.

Entregables:

- MUD URI.
- Content hash.
- Registro de punteros.
- Resolución simple.
- Lectura de bloques JSON/Markdown.

### Fase 1 — Query router

Objetivo: búsqueda básica con presupuesto.

Entregables:

- Endpoint `/query`.
- Filtro por categoría.
- Búsqueda exacta.
- Búsqueda full-text.
- Respuestas con summary + pointer.

### Fase 2 — Escritura verificable

Objetivo: evitar corrupción y conflictos.

Entregables:

- Event log.
- Optimistic concurrency.
- `before_hash`.
- Leases.
- Auditoría básica.

### Fase 3 — Retrieval híbrido

Objetivo: mejorar precisión.

Entregables:

- Vector search.
- Reranking.
- Grafo de dependencias.
- Presupuesto inteligente.
- Métricas de retrieval.

### Fase 4 — Consolidación

Objetivo: convertir eventos en conocimiento.

Entregables:

- Consolidation Engine.
- Resumen automático.
- Promoción episódica → semántica.
- Detección de duplicados.
- Decaimiento.

### Fase 5 — Seguridad avanzada

Objetivo: operar con secretos y PII de forma segura.

Entregables:

- Vault.
- Redacción automática.
- ACL por agente.
- Acceso pointer-only.
- Auditoría sensible.

### Fase 6 — Distribución

Objetivo: operar múltiples nodos y agentes concurrentes.

Entregables:

- Replicación.
- Particionado por categoría.
- CRDT opcional para memorias colaborativas.
- Snapshotting.
- Disaster recovery.

---

## 25. Diferencias entre MUD v1 y MUD v3

| Aspecto | MUD v1 | MUD v3 |
|---|---|---|
| Enfoque | Memoria compartida | Atención distribuida |
| Contexto | Bloques relevantes | Presupuesto + resumen + punteros |
| Escritura | Locking / mutex | Event sourcing + optimistic concurrency |
| Identidad | `seccion_id#bloque_hash` | MUD URI + content hash + version |
| Búsqueda | RAG ligero | Híbrida: exacta, BM25, vector, grafo |
| Seguridad | Básica | ACL, vault, redacción, auditoría |
| Ciclo de vida | No explícito | Working, episodic, semantic, procedural |
| Observabilidad | Limitada | Traces, métricas, auditoría |
| Consolidación | Manual o ausente | Motor asíncrono de consolidación |
| Escalabilidad | Monolítica | Gateway + índices + storage distribuido |

---

## 26. Riesgos y Mitigaciones

### 26.1 Recuperación insuficiente

**Riesgo:** el agente no recibe contexto suficiente.

**Mitigación:**

- Modo `fallback_broad`.
- Resúmenes jerárquicos.
- Punteros de expansión.
- Métrica `context_miss_rate`.

### 26.2 Fuga de secretos

**Riesgo:** contenido sensible entra en contexto.

**Mitigación:**

- Redacción automática.
- Vault references.
- ACL por agente.
- Tests de fuga.

### 26.3 Memoria contaminada

**Riesgo:** un agente escribe conocimiento incorrecto.

**Mitigación:**

- Provenance.
- Validación humana para memorias críticas.
- Versionado.
- Detección de contradicciones.

### 26.4 Crecimiento descontrolado

**Riesgo:** la memoria se vuelve infinita.

**Mitigación:**

- TTL.
- Decaimiento.
- Consolidación.
- Archivado.
- GC de bloques huérfanos.

### 26.5 Sobreingeniería

**Riesgo:** construir demasiado antes de validar.

**Mitigación:**

- Empezar por punteros simples.
- Luego retrieval.
- Luego consolidación.
- Luego distribución.

---

## 27. Manifiesto MUD v3

```text
El contexto no es almacenamiento.
La memoria no es un volcado de archivos.
El conocimiento no es infinito.
Los secretos no pertenecen al prompt.
Cada bloque debe ser verificable.
Cada escritura debe ser auditable.
Cada lectura debe respetar presupuesto.
Cada agente debe recibir solo la atención necesaria.
```

---

## 28. Resumen Ejecutivo

MUD v3 convierte la memoria multiagente en una infraestructura formal de atención.

Sus piezas clave son:

1. **MUD URI** para identificar memoria.
2. **Content hash** para integridad e invalidación.
3. **Event log** para auditoría y consistencia.
4. **Query planner** para recuperar solo lo relevante.
5. **Budget tokens** para no saturar modelos.
6. **Índice híbrido** para precisión técnica y semántica.
7. **Memory tiers** para gestionar ciclo de vida.
8. **Vault/ACL** para proteger información sensible.
9. **Consolidation engine** para transformar eventos en conocimiento.
10. **Observability** para medir y mejorar el sistema.

---

## 29. Frase Final

> MUD no solo almacena memoria.  
> Decide qué merece convertirse en atención para cada agente.