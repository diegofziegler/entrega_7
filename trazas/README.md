# Evidencia de Trazas y Logs de Ejecución

Este directorio contiene las evidencias de las ejecuciones del sistema, garantizando la trazabilidad completa requerida por la Entrega 7.

## 1. Logs de Ejecución Almacenados en `./log`

Se generan de forma separada y continua dos archivos de log durante las operaciones del sistema:

- **`./log/agentes.log`**: Registra la toma de decisiones del Agente Supervisor, la invocación del Agente Investigador (RAG) y la redacción/síntesis multilingüe del Agente Analista.
- **`./log/rag.log`**: Registra la inicialización del modelo de embeddings (`sentence-transformers/all-MiniLM-L6-v2`), la ingesta de documentos `.md` y las consultas de búsqueda vectorial (Pinecone / fallback local).

### Muestra de `./log/agentes.log`:
```text
[2026-10-12 21:42:01,811] [INFO] [agentes]: API Chat recibida: thread_id=test-session-unit, idioma=Español
[2026-10-12 21:42:01,812] [INFO] [agentes]: --- NODO SUPERVISOR ---
[2026-10-12 21:42:01,815] [INFO] [agentes]: Supervisor decidió siguiente paso: INVESTIGADOR
[2026-10-12 21:42:01,816] [INFO] [agentes]: --- NODO INVESTIGADOR (RAG) ---
[2026-10-12 21:42:01,816] [INFO] [agentes]: Investigador buscando información para: '¿Quién fue Kanbun Uechi?'
[2026-10-12 21:42:01,821] [INFO] [agentes]: --- NODO SUPERVISOR ---
[2026-10-12 21:42:01,824] [INFO] [agentes]: Supervisor decidió siguiente paso: ANALISTA
[2026-10-12 21:42:01,825] [INFO] [agentes]: --- NODO ANALISTA / SINTETIZADOR ---
[2026-10-12 21:42:01,830] [INFO] [agentes]: Analista generó respuesta en idioma 'Español'
```

### Muestra de `./log/rag.log`:
```text
[2026-10-12 21:42:01,000] [INFO] [rag]: Inicializando embeddings con modelo: sentence-transformers/all-MiniLM-L6-v2
[2026-10-12 21:42:01,200] [INFO] [rag]: Usando SimpleLocalVectorStore como almacenamiento vectorial fallback.
[2026-10-12 21:42:01,300] [INFO] [rag]: Iniciando ingesta de documentos desde: ./data
[2026-10-12 21:42:01,700] [INFO] [rag]: LocalVectorStore: Agregados 220 documentos al almacenamiento local/en memoria.
[2026-10-12 21:42:01,701] [INFO] [rag]: Ingesta completada: 220 chunks procesados e indexados.
```

---

## 2. Observabilidad y Trazado (Arize Phoenix / OpenInference)

El sistema integra la instrumentación asíncrona de **OpenInference / LangChain** (`src/entrega_7/telemetry.py`), enviando spans OTLP al colector de Arize Phoenix (`http://localhost:6006/v1/traces`).

Cada span de la ejecución registra:
- Traza del Grafo de LangGraph (Supervisor -> Investigador -> Supervisor -> Analista).
- Consultas de recuperación vectorial RAG.
- Prompts, tokens y latencias de invocaciones al LLM.
