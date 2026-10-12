# The Intelligence System (Entrega 7)

Sistema de inteligencia artificial de grado de producción, diseñado para razonar, recordar, escalar y ofrecer trazabilidad completa. Este proyecto consolida e integra pre-entregas previas (RAG, Agentes con supervisor en LangGraph, API con FastAPI y persistencia con Redis y Pinecone) en una única arquitectura limpia, asíncrona y robusta.

---

## 🏗️ Arquitectura del Sistema

El sistema implementa un flujo unificado estructurado en capas:

1. **Capa de API (FastAPI):** Interfaz profesional y documentada con endpoints asíncronos para chat multi-agente (`/api/v1/chat`), consulta de historial (`/api/v1/history/{thread_id}`), ingesta de conocimiento (`/api/v1/rag/ingest`) y verificación de estado (`/health`).
2. **Capa de Orquestación y Razonamiento (LangGraph):** Grafo de agentes con un *Supervisor* autónomo capaz de delegar tareas entre el *Agente Investigador RAG* y el *Agente Analista/Sintetizador* multilingüe.
3. **Capa de Memoria y Persistencia:** Uso de *Checkpointers* de LangGraph respaldados por Redis (o almacenamiento en memoria resiliente) para garantizar que el estado de las conversaciones persista por `thread_id`.
4. **Capa de Conocimiento (RAG Avanzado):** Recuperación híbrida y gestión de metadatos utilizando **Pinecone** como base de datos vectorial (con fallback local/en memoria resiliente para desarrollo y pruebas).
5. **Capa de Observabilidad:** Trazado de ejecución de punta a punta con *Arize Phoenix* (OpenInference / OTLP) y generación de logs dedicados (`log/agentes.log` y `log/rag.log`).

```mermaid
graph TD  
    User([Usuario / Cliente API]) -->|Async Request| FastAPI[FastAPI Backend]  
    FastAPI --> Supervisor[LangGraph Supervisor]  
    Supervisor -->|Delega| Agent1[Agente Investigador RAG]  
    Supervisor -->|Delega| Agent2[Agente Analista / Sintetizador]
    Agent1 --> Pinecone[(Pinecone Vector DB / Local Fallback)]
    FastAPI --> Redis[(Redis Checkpointer / Estado)]  
    Supervisor --> Phoenix[Arize Phoenix / Trazas]
```

---

## 🛠️ Requisitos del Sistema

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** (Gestor de dependencias ultrarrápido)
- **Docker & Docker Compose** (Opcional, para ejecución de servicios complementarios como Redis)

---

## 🚀 Instalación y Configuración (con `uv`)

### 1. Instalar `uv` (si no lo tienes en tu sistema)

- **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows (PowerShell):** `irm https://astral.sh/uv/install.ps1 | iex`

### 2. Clonar el repositorio y sincronizar el entorno

```bash
git clone https://github.com/diegofziegler/entrega_7.git  
cd entrega_7  
uv sync
```

### 3. Configurar las Variables de Entorno

Crea un archivo `.env` basado en el archivo de ejemplo:

```bash
cp .env.example .env
```

*(Variables requeridas / opcionales: `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `REDIS_URL`, etc.)*

---

## ▶️ Ejecución del Proyecto

### Opción A: Ejecución local con `uv`

Para iniciar el servidor de desarrollo de FastAPI utilizando el entorno virtual gestionado por `uv`:

```bash
uv run uvicorn src.entrega_7.main:app --reload
```

---

## 🌐 Endpoints de la API

- `GET /health`: Verificación del estado del sistema, proveedor LLM activo y estado del RAG y Checkpointer.
- `POST /api/v1/chat`: Inicia o continúa una interacción con el orquestador multi-agente.
  - **Payload:**
    ```json
    {
      "message": "¿De qué tratan las técnicas básicas del Karate Uechi-Ryu?",
      "thread_id": "sesion-123",
      "idioma_destino": "Inglés"
    }
    ```
- `GET /api/v1/history/{thread_id}`: Recupera el historial de mensajes asociado a una sesión activa.
- `POST /api/v1/rag/ingest`: Ejecuta o fuerza la ingesta de documentos Markdown ubicados en `./data`.

---

## 📊 Observabilidad y Trazas

El sistema cuenta con observabilidad e historial de trazabilidad integrados:

1. **Logs de Ejecución:**
   - `./log/agentes.log`: Decisiones del supervisor y síntesis del analista.
   - `./log/rag.log`: Ingesta y búsquedas de similitud vectorial.
2. **Telemetría OTLP (Arize Phoenix / OpenInference):**
   - Configura `PHOENIX_COLLECTOR_ENDPOINT` en `.env`.
   - Evidencias guardadas en el directorio [`./trazas`](./trazas).

---

## 🧪 Pruebas Unitarias e Integración

Para ejecutar la suite completa de pruebas unitarias e integración:

```bash
PYTHONPATH=. uv run pytest tests/test_system.py
```
