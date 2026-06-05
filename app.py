from flask import Flask, request, Response
import time
import os
import random
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Core telemetry metrics
HTTP_REQUESTS_TOTAL = Counter(
    'flask_http_requests_total',
    'Total number of HTTP requests to the Flask application',
    ['method', 'endpoint', 'status']
)
HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    'flask_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)
IN_FLIGHT_REQUESTS = Gauge(
    'flask_in_flight_requests',
    'Number of HTTP requests currently being processed'
)

@app.before_request
def start_timer():
    IN_FLIGHT_REQUESTS.inc()
    request.start_time = time.time()

@app.after_request
def log_request(response):
    IN_FLIGHT_REQUESTS.dec()
    # Avoid scraping metrics of the /metrics endpoint itself
    if request.path == '/metrics':
        return response

    latency = time.time() - getattr(request, 'start_time', time.time())
    endpoint = request.path
    method = request.method
    status = str(response.status_code)

    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
    HTTP_REQUEST_LATENCY_SECONDS.labels(method=method, endpoint=endpoint).observe(latency)
    
    return response

@app.route('/')
def index():
    return {
        "status": "healthy",
        "service": "InfoSec Mock API",
        "timestamp": time.time(),
        "environment": os.getenv("ENV", "production")
    }

@app.route('/api/v1/resource')
def get_resource():
    # Simulate a lightweight request
    time.sleep(random.uniform(0.01, 0.05))
    return {
        "status": "success",
        "data": "Sensitive telemetry data accessed successfully."
    }

@app.route('/api/v1/auth', methods=['POST'])
def auth_mock():
    # Simulate authentication endpoint
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    
    if username == "admin" and data.get("password") == "secret123":
        return {"status": "authenticated", "token": "jwt_token_placeholder"}, 200
    
    # Randomly fail if brute forcing is simulated
    time.sleep(random.uniform(0.05, 0.2))
    return {"status": "unauthorized", "error": "Invalid credentials"}, 401

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
