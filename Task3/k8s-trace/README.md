# Jaeger в Minikube с сервисами

## Описание
MVP трассировки для будущего развёртывания в Kubernetes. Два сервиса:
1. **service-a** — сервис заказов. `GET /` создаёт заказ и запрашивает его стоимость у service-b.
2. **service-b** — сервис расчёта стоимости. `GET /` «рассчитывает» цену по сложности модели.

Оба сервиса используют OpenTelemetry SDK (Python) и отправляют спаны в Jaeger по OTLP/HTTP.
Контекст трейса (`traceparent`) и номер заказа (`baggage: order.id`) передаются в HTTP-заголовках,
поэтому вызов service-a → service-b целиком попадает в один трейс, а `order.id` виден в спанах обоих сервисов.

```
service-a: GET /                 (HTTP-сервер, Flask)
└─ order.create                  order.id, order.channel, order.status.from/to
   └─ GET                        (HTTP-клиент, requests) → http://service-b:8080/
      └─ service-b: GET /        (HTTP-сервер, Flask)
         └─ price.calculate      order.id (из baggage), model.polygons
```

## Требования
- Minikube
- kubectl
- Docker

## Установка

### 1. Запуск Minikube
```bash
minikube start --addons=ingress
```
Ingress нужен для вызовов

### 2. Установка cert-manager
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml
```

### 3. Развертывание Jaeger
```bash
kubectl create namespace observability
kubectl create -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.51.0/jaeger-operator.yaml -n observability
kubectl apply -f k8s/jaeger-instance.yaml
```

> **Если под `jaeger-operator` висит в `ImagePullBackOff`.** Манифест оператора ссылается на образ
> `gcr.io/kubebuilder/kube-rbac-proxy:v0.13.1`, который удалён из реестра. Это сайдкар для метрик оператора,
> заменяем его на тот же образ из исходного репозитория:
> ```bash
> kubectl -n observability set image deploy/jaeger-operator kube-rbac-proxy=quay.io/brancz/kube-rbac-proxy:v0.13.1
> kubectl -n observability rollout status deploy/jaeger-operator
> ```
> После перезапуска оператору может понадобиться до двух минут, чтобы получить блокировку лидера
> и создать deployment `simplest`.

### 4. Сборка и деплой сервисов
```bash
# Сборка образов
minikube image build -t service-a:latest services/service-a/
minikube image build -t service-b:latest services/service-b/

# Развертывание
kubectl apply -f k8s/services.yaml
```

Адрес приёмника спанов задаётся переменными окружения в `k8s/services.yaml`:
`OTEL_SERVICE_NAME` и `OTEL_EXPORTER_OTLP_ENDPOINT=http://simplest-collector:4318`.

## Проверка работы

### Тестирование сервисов
```bash
# Вызов service-a, который вызывает service-b
kubectl exec -it $(kubectl get pods -l app=service-a -o jsonpath='{.items[0].metadata.name}') -- wget -qO- http://service-a:8080
```

Пример ответа:
```json
{"order_id":"ORD-8AAD46F9","price":{"amount":5672.8,"currency":"RUB","order_id":"ORD-8AAD46F9"},"status":"PRICE_CALCULATED","trace_id":"b1edd428f60d920cfb26d5b885333315"}
```

### Доступ к Jaeger UI
```bash
kubectl port-forward svc/simplest-query 16686:16686
```
Откройте в браузере: http://localhost:16686. Найти трейс можно по `trace_id` из ответа
или в Search: сервис `service-a`, тег `order.id=<номер заказа>`.

### Результат

Один трейс: 2 сервиса, 5 спанов, `order.id` передан из service-a в service-b:

![Трейс в Jaeger](../jaeger-trace.png)

## Структура проекта
- `services/service-a/` - Исходный код service-a (сервис заказов)
- `services/service-b/` - Исходный код service-b (сервис расчёта)
- `services/*/telemetry.py` - Настройка OpenTelemetry SDK и экспорта в Jaeger
- `k8s/services.yaml` - Конфигурация Kubernetes для сервисов
- `k8s/jaeger-instance.yaml` - Конфигурация Jaeger
