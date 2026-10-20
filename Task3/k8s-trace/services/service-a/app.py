"""service-a — сервис заказов.

GET / создаёт заказ и запрашивает его стоимость у service-b (сервиса расчёта).
Контекст трейса (traceparent) и номер заказа (baggage order.id) передаются
в HTTP-заголовках, поэтому оба сервиса попадают в один трейс.
"""
import os
import uuid

import requests
from flask import Flask, jsonify
from opentelemetry import baggage, context, trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from telemetry import init_tracing

init_tracing()
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
tracer = trace.get_tracer("service-a")

PRICING_URL = os.getenv("PRICING_URL", "http://service-b:8080/")


@app.get("/")
def create_order():
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    with tracer.start_as_current_span("order.create") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.channel", "b2c")

        # order.id уходит в service-b через заголовок baggage
        token = context.attach(baggage.set_baggage("order.id", order_id))
        try:
            response = requests.get(PRICING_URL, timeout=5)
            response.raise_for_status()
            price = response.json()
        finally:
            context.detach(token)

        span.set_attribute("order.status.from", "SUBMITTED")
        span.set_attribute("order.status.to", "PRICE_CALCULATED")
        trace_id = format(span.get_span_context().trace_id, "032x")

    return jsonify(order_id=order_id, status="PRICE_CALCULATED", price=price, trace_id=trace_id)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
