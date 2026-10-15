from entrega_7.config import settings
from entrega_7.logging_config import agentes_logger

_configured = False
_provider = None


def setup_telemetry() -> bool:
    """Configure LangChain/OpenInference export before the first graph invocation."""
    global _configured, _provider
    if _configured:
        return True
    if not settings.PHOENIX_ENABLED or not settings.PHOENIX_COLLECTOR_ENDPOINT:
        agentes_logger.info("Telemetría Phoenix deshabilitada por configuración.")
        return False
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        endpoint = settings.PHOENIX_COLLECTOR_ENDPOINT.rstrip("/")
        if not endpoint.endswith("/v1/traces"):
            endpoint += "/v1/traces"
        provider = TracerProvider(resource=Resource.create({"service.name": "entrega-7", "openinference.project.name": settings.PHOENIX_PROJECT_NAME}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        LangChainInstrumentor().instrument(tracer_provider=provider)
        _provider = provider
        _configured = True
        agentes_logger.info("Trazas OpenInference enviándose a Phoenix: %s", endpoint)
        return True
    except Exception:
        agentes_logger.exception("No se pudo configurar la exportación de trazas a Phoenix.")
        return False


def shutdown_telemetry() -> None:
    if _provider is not None:
        _provider.force_flush(timeout_millis=5_000)
        _provider.shutdown()
