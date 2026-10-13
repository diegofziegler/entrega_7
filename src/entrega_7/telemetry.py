from src.entrega_7.config import settings
from src.entrega_7.logging_config import agentes_logger


def setup_telemetry():
    if settings.PHOENIX_COLLECTOR_ENDPOINT:
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor
            from opentelemetry import trace as trace_api
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            tracer_provider = TracerProvider()
            endpoint = f"{settings.PHOENIX_COLLECTOR_ENDPOINT.rstrip('/')}/v1/traces"
            span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
            tracer_provider.add_span_processor(span_processor)
            trace_api.set_tracer_provider(tracer_provider)

            LangChainInstrumentor().instrument()
            agentes_logger.info(f"Arize Phoenix OpenInference Telemetry instrumentado hacia {endpoint}")
        except Exception as e:
            agentes_logger.warning(f"No se pudo configurar OpenInference / Phoenix Telemetry ({e}).")


setup_telemetry()
