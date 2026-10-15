"""Prueba de integración de cinco preguntas y exportación de trazas Phoenix.

Ejecutar desde la raíz del repositorio con:
    uv run python tests/test_5_preguntas.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = Path(__file__).resolve().with_name("test_5_preguntas.log")
TRACES_PATH = ROOT_DIR / "trazas" / "spans.json"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PHOENIX_COLLECTOR_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"
)
PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "entrega-7")
REQUEST_TIMEOUT_SETTING = os.getenv("TEST_REQUEST_TIMEOUT_SECONDS", "180")

PREGUNTAS = [
    ("¿Qué significa el término Karate?", "Español"),
    ("¿Cuáles son los tres estilos de Karate de Okinawa?", "Inglés"),
    ("¿Quién fue Kanbun Uechi?", "Francés"),
    ("¿Cuál es el significado de Sanchin?", "Portugués"),
    ("Nombra los 3 principales Katas del estilo Uechi-ryu", "Español"),
]


def configurar_logging() -> logging.Logger:
    logger = logging.getLogger("test_5_preguntas")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


async def comprobar_api_disponible(logger: logging.Logger) -> list[str]:
    """Comprueba el endpoint de salud antes de iniciar las consultas."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            response.raise_for_status()
            try:
                health_data = response.json()
            except ValueError:
                health_data = {}
            estado = health_data.get("status", "desconocido") if isinstance(health_data, dict) else "desconocido"
            rag_status = health_data.get("rag_status", "desconocido") if isinstance(health_data, dict) else "desconocido"
            logger.info(
                "Health check correcto: HTTP %d; status=%s; rag_status=%s.",
                response.status_code,
                estado,
                rag_status,
            )
            return []
    except httpx.ConnectError as exc:
        detalle = (
            f"No se pudo conectar con {API_BASE_URL}/health. "
            "Comprueba que el ambiente y la API estén iniciados."
        )
        logger.exception("%s (%s)", detalle, exc)
        return [detalle]
    except httpx.TimeoutException as exc:
        detalle = f"La comprobación de /health agotó el tiempo de espera: {exc}"
        logger.exception(detalle)
        return [detalle]
    except httpx.HTTPStatusError as exc:
        detalle = (
            f"La comprobación de /health devolvió HTTP {exc.response.status_code}: "
            f"{exc.response.text[:1000]}"
        )
        logger.error(detalle)
        return [detalle]
    except httpx.RequestError as exc:
        detalle = f"Error de red consultando /health: {type(exc).__name__}: {exc}"
        logger.exception(detalle)
        return [detalle]
    except Exception as exc:
        detalle = f"Error inesperado comprobando /health: {type(exc).__name__}: {exc}"
        logger.exception(detalle)
        return [detalle]


async def enviar_preguntas(logger: logging.Logger) -> list[str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    errores: list[str] = []
    try:
        timeout_seconds = float(REQUEST_TIMEOUT_SETTING)
        if timeout_seconds <= 0:
            raise ValueError("debe ser mayor que cero")
        timeout = httpx.Timeout(timeout_seconds, connect=10.0)
    except ValueError as exc:
        detalle = (
            "TEST_REQUEST_TIMEOUT_SECONDS debe ser un número mayor que cero; "
            f"valor recibido: {REQUEST_TIMEOUT_SETTING!r} ({exc})."
        )
        logger.exception(detalle)
        return [detalle]

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for numero, (pregunta, idioma_destino) in enumerate(PREGUNTAS, start=1):
                thread_id = f"test-5-preguntas-{timestamp}-{numero}"
                payload = {
                    "message": pregunta,
                    "thread_id": thread_id,
                    "idioma_destino": idioma_destino,
                }
                logger.info(
                    "Pregunta %d/%d (respuesta en %s): %s",
                    numero,
                    len(PREGUNTAS),
                    idioma_destino,
                    pregunta,
                )
                try:
                    response = await client.post(
                        f"{API_BASE_URL}/api/v1/chat", json=payload
                    )
                    response.raise_for_status()
                    data: dict[str, Any] = response.json()
                    reply = data.get("reply")
                    if not isinstance(reply, str) or not reply.strip():
                        raise ValueError("La API respondió sin un campo 'reply' válido.")
                    logger.info("Respuesta %d: %s", numero, reply)
                    logger.info("Pregunta %d completada (thread_id=%s).", numero, thread_id)

                    history_response = await client.get(
                        f"{API_BASE_URL}/api/v1/history/{thread_id}"
                    )
                    history_response.raise_for_status()
                    history_data: dict[str, Any] = history_response.json()
                    history = history_data.get("messages")
                    if not isinstance(history, list):
                        raise ValueError(
                            "El endpoint de historial no devolvió una lista 'messages'."
                        )
                    if not history:
                        raise ValueError(
                            f"El historial está vacío para thread_id={thread_id}."
                        )
                    logger.info(
                        "Historial recuperado: %d mensaje(s) para thread_id=%s.",
                        len(history),
                        thread_id,
                    )
                    for item in history:
                        if isinstance(item, dict):
                            logger.info(
                                "  %s: %s",
                                item.get("sender", "desconocido"),
                                item.get("content", ""),
                            )
                except httpx.ConnectError as exc:
                    detalle = (
                        f"No se pudo conectar con la API en {API_BASE_URL}. "
                        "Comprueba que Docker Compose/API esté iniciado."
                    )
                    logger.exception("Pregunta %d: %s (%s)", numero, detalle, exc)
                    errores.append(detalle)
                    break
                except httpx.TimeoutException as exc:
                    detalle = f"Tiempo de espera agotado en la pregunta {numero}: {exc}"
                    logger.exception(detalle)
                    errores.append(detalle)
                except httpx.HTTPStatusError as exc:
                    detalle = (
                        f"La API devolvió HTTP {exc.response.status_code} para la pregunta "
                        f"{numero}: {exc.response.text[:1000]}"
                    )
                    logger.error(detalle)
                    errores.append(detalle)
                except (httpx.RequestError, ValueError, TypeError) as exc:
                    detalle = f"Falló la pregunta {numero}: {type(exc).__name__}: {exc}"
                    logger.exception(detalle)
                    errores.append(detalle)
    except Exception as exc:
        detalle = f"Error preparando o ejecutando las solicitudes: {type(exc).__name__}: {exc}"
        logger.exception(detalle)
        errores.append(detalle)

    return errores


def exportar_trazas(logger: logging.Logger) -> int:
    # Phoenix lee esta variable al crear el cliente; se define también aquí para
    # que el script funcione aunque no se haya exportado previamente en PowerShell.
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = PHOENIX_COLLECTOR_ENDPOINT
    TRACES_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        from phoenix.client import Client

        spans = Client().spans.get_spans_dataframe(project_name=PHOENIX_PROJECT_NAME)
        spans.to_json(
            TRACES_PATH,
            orient="records",
            force_ascii=False,
            indent=2,
        )
        cantidad = len(spans)
        logger.info("Exportados %d spans a %s", cantidad, TRACES_PATH)
        return cantidad
    except ImportError as exc:
        logger.exception("No se pudo importar el cliente Phoenix. Ejecuta 'uv sync'.")
        raise RuntimeError("Falta la dependencia arize-phoenix en el entorno.") from exc
    except Exception as exc:
        logger.exception(
            "No se pudieron exportar spans desde Phoenix (%s, proyecto=%s): %s",
            PHOENIX_COLLECTOR_ENDPOINT,
            PHOENIX_PROJECT_NAME,
            exc,
        )
        raise RuntimeError(
            "Falló la exportación de trazas. Verifica Phoenix, el endpoint, "
            "el nombre del proyecto y el log del test."
        ) from exc


async def main() -> int:
    logger = configurar_logging()
    logger.info("Inicio de prueba: API=%s; Phoenix=%s", API_BASE_URL, PHOENIX_COLLECTOR_ENDPOINT)
    errores = await comprobar_api_disponible(logger)
    if errores:
        logger.error("Se omiten las preguntas porque el health check no fue satisfactorio.")
    else:
        errores.extend(await enviar_preguntas(logger))

    try:
        exportar_trazas(logger)
    except RuntimeError as exc:
        errores.append(str(exc))

    if errores:
        logger.error("Prueba finalizada con %d error(es):", len(errores))
        for error in errores:
            logger.error("- %s", error)
        logger.info("Consulta el detalle en %s", LOG_PATH)
        return 1

    logger.info("Prueba completada: las cinco preguntas fueron respondidas y las trazas exportadas.")
    logger.info("Log: %s", LOG_PATH)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logging.getLogger("test_5_preguntas").warning("Prueba interrumpida por el usuario.")
        sys.exit(130)
    except Exception:
        logger = logging.getLogger("test_5_preguntas")
        logger.exception("Error inesperado durante la ejecución del test.")
        sys.exit(1)
