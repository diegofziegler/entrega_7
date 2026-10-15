# Evidencia de Phoenix

La API configura OpenInference durante su `lifespan`, antes de construir el grafo, y exporta las trazas OTLP al collector Phoenix. Cada solicitud de chat crea el span raíz `api.chat`; la instrumentación de LangChain agrega spans de grafo y de las invocaciones del modelo. Los proveedores que exponen uso añaden tokens de entrada/salida. Phoenix calcula costos estimados cuando se configura el pricing para el modelo utilizado.

## Capturar evidencia

1. Inicia el stack con `docker compose up --build` y envía una petición `POST /api/v1/chat` con un `thread_id` único.
2. Abre `http://localhost:6006`, selecciona el proyecto `entrega-7` y espera a que termine el envío de spans.
3. Guarda una captura del árbol de la ejecución expandido, incluyendo los spans del grafo y el span del LLM con tokens/costo si el proveedor y el modelo tienen esos datos configurados.
4. Guarda la imagen en este directorio, con nombre descriptivo, por ejemplo `chat-kanbun-english.png`.

Las capturas no se generan con datos simulados. Este repositorio necesita credenciales válidas de Pinecone y del proveedor LLM, y que Phoenix esté ejecutándose para producir evidencia real. Captura una traza por cada caso que quieras presentar como evidencia.

Para exportar los spans del proyecto a JSON desde PowerShell, sigue [EXPORTAR_TRAZAS.md](./EXPORTAR_TRAZAS.md).
