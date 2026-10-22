"""service-b — сервис расчёта стоимости.

GET / «рассчитывает» стоимость заказа. Контекст трейса приходит из service-a
в заголовке traceparent, номер заказа — в заголовке baggage.
"""
import random
import time

from flask import Flask, jsonify
from opentelemetry import baggage, trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor

from telemetry import init_tracing

init_tracing()
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
tracer = trace.get_tracer("service-b")


@app.get("/")
def calculate_price():
    order_id = baggage.get_baggage("order.id") or "unknown"
    with tracer.start_as_current_span("price.calculate") as span:
        polygons = random.randint(10_000, 500_000)
        span.set_attribute("order.id", order_id)
        span.set_attribute("model.polygons", polygons)

        time.sleep(polygons / 1_000_000)  # имитация расчёта: чем сложнее модель, тем дольше
        amount = round(polygons * 0.05, 2)
        span.set_attribute("price.calculation.result", "success")

    return jsonify(order_id=order_id, amount=amount, currency="RUB")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
