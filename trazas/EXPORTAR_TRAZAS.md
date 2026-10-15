# Exportar trazas de Phoenix a archivos locales

Esta guía explica cómo guardar en `trazas/` los spans recibidos por Phoenix y cómo capturar el árbol de una ejecución desde el dashboard. Ejecuta los comandos de PowerShell desde la raíz del repositorio.

## Requisitos

1. Configura las claves del proveedor LLM, Pinecone y embeddings en `.env`.
2. Levanta los servicios desde la raíz del proyecto:

   ```powershell
   docker compose up --build -d
   ```

3. Envía una petición a `POST http://localhost:8000/api/v1/chat` con un `thread_id` nuevo. Espera a que la ejecución termine y verifica que Phoenix reciba spans.
4. Si todavía no sincronizaste el entorno Python, ejecuta `uv sync --frozen`.

Phoenix está disponible en `http://localhost:6006`; el proyecto usado por la aplicación se llama `entrega-7`.

## Exportar los spans como JSON

En la misma ventana de PowerShell y desde la raíz del repositorio, configura el endpoint local de Phoenix y ejecuta el cliente Python:

```powershell
$env:PHOENIX_COLLECTOR_ENDPOINT = "http://localhost:6006"
@'
from pathlib import Path
from phoenix.client import Client

Path("trazas").mkdir(exist_ok=True)
spans = Client().spans.get_spans_dataframe(project_name="entrega-7")
spans.to_json("trazas/spans.json", orient="records", force_ascii=False, indent=2)
print(f"Exportados {len(spans)} spans a trazas/spans.json")
'@ | uv run python -
```

El resultado queda en `trazas/spans.json`. Cada fila representa un span; el archivo incluye los spans de las ejecuciones que Phoenix tenga en ese proyecto al momento de exportar. El número impreso es la cantidad de spans exportados, no la cantidad de conversaciones.

Puedes volver a ejecutar el comando después de nuevas pruebas. El archivo `spans.json` existente se reemplazará con la exportación actual.

## Capturar el árbol visual en Phoenix

1. Abre `http://localhost:6006` y selecciona el proyecto `entrega-7`.
2. Abre la traza correspondiente al `thread_id` de tu petición y expande el árbol de spans.
3. Comprueba que se vea la ejecución completa. Para evidenciar costos, incluye el costo de la traza o el desglose de los spans LLM cuando Phoenix lo muestre.
4. En Windows, usa **Win + Shift + S** para capturar el área del dashboard y guarda la imagen en `trazas/` con un nombre descriptivo, por ejemplo `chat-tecnicas-uechi-ryu.png`.

Si no aparecen costos, revisa en Phoenix que la traza tenga el nombre del modelo y los tokens de entrada/salida, y que exista una tarifa configurada para ese modelo.

## Cuidado con los datos

Los spans pueden contener preguntas, documentos recuperados y respuestas. Revisa `spans.json` y las capturas antes de compartirlos o incluirlos en un commit; elimina o redacta cualquier dato que no quieras publicar.
