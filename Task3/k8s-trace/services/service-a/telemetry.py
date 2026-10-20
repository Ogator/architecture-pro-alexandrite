"""Настройка OpenTelemetry SDK: провайдер трейсов и экспорт спанов в Jaeger по OTLP/HTTP.

Имя сервиса и адрес коллектора берутся из переменных окружения
OTEL_SERVICE_NAME и OTEL_EXPORTER_OTLP_ENDPOINT (см. k8s/services.yaml).
"""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def init_tracing() -> None:
    provider = TracerProvider(resource=Resource.create())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
