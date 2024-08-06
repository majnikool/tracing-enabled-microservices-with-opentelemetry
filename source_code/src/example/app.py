import json
import os
import time
import redis
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaTimeoutError, TopicAlreadyExistsError, NoBrokersAvailable
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource as OTResource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Initialize logging
class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.trace_id = getattr(record, 'trace_id', 'N/A')
        record.span_id = getattr(record, 'span_id', 'N/A')
        record.parent_span_id = getattr(record, 'parent_span_id', 'N/A')
        return super().format(record)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s [Trace ID: %(trace_id)s] [Span ID: %(span_id)s] [Parent Span ID: %(parent_span_id)s] %(message)s')
logger = logging.getLogger(__name__)

# Ensure that the CustomFormatter is used in all handlers
for handler in logging.root.handlers:
    handler.setFormatter(CustomFormatter(handler.formatter._fmt))

# Set Kafka library logging level to WARNING to reduce verbosity
kafka_logger = logging.getLogger('kafka')
kafka_logger.setLevel(logging.WARNING)

# Initialize FastAPI app
app = FastAPI()

# OpenTelemetry tracing setup
if os.getenv('ENABLE_TRACING', 'false').lower() == 'true':
    otlp_endpoint = os.getenv('OTLP_ENDPOINT', 'localhost:4317')
    resource = OTResource.create({"service.name": "test-app-api-gateway"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    RedisInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

# Initialize Redis client with connection pool
redis_pool = redis.ConnectionPool(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=6379,
    db=0,
    password=os.getenv('REDIS_PASSWORD'),
    max_connections=20
)
redis_client = redis.StrictRedis(connection_pool=redis_pool)

def check_redis():
    try:
        redis_client.ping()
        logger.info("Redis connection successful.")
        return True
    except redis.ConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        return False

# Kafka configuration
kafka_broker = os.getenv('KAFKA_BROKER', 'localhost:9092')

def check_kafka():
    try:
        admin_client = KafkaAdminClient(bootstrap_servers=kafka_broker)
        admin_client.list_topics()
        logger.info("Kafka connection successful.")
        return True
    except NoBrokersAvailable as e:
        logger.error(f"Kafka connection failed: {e}")
        return False

# Kafka topic setup
def ensure_kafka_topics():
    admin_client = KafkaAdminClient(bootstrap_servers=kafka_broker)
    topics = ['data_requests', 'data_responses']
    existing_topics = admin_client.list_topics()
    for topic in topics:
        if topic not in existing_topics:
            try:
                admin_client.create_topics([NewTopic(name=topic, num_partitions=1, replication_factor=1)])
                logger.info(f"Created Kafka topic: {topic}")
            except TopicAlreadyExistsError:
                logger.info(f"Kafka topic {topic} already exists")

# Kafka producer setup
producer = KafkaProducer(
    bootstrap_servers=kafka_broker,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    retries=5,
    reconnect_backoff_ms=50,
    reconnect_backoff_max_ms=1000
)

# Initialize request_contexts dictionary
request_contexts = {}

# Define getter and setter functions for context propagation
propagator = TraceContextTextMapPropagator()

class DictGetter:
    def get(self, carrier, key):
        return carrier.get(key, None)

class DictSetter:
    def set(self, carrier, key, value):
        carrier[key] = value

getter = DictGetter()
setter = DictSetter()

# Redis helper functions
def get_data_from_redis(entered_id):
    data = redis_client.get(entered_id)
    logger.info(f"Redis get for ID {entered_id}: {data}")
    return data

def cache_data_in_redis(entered_id, data):
    if '_id' in data:
        data['id'] = data.pop('_id')
    redis_client.set(entered_id, json.dumps(data))
    logger.info(f"Redis set for ID {entered_id}: {data}")

# Kafka message helper functions
def send_message_to_kafka(request_type, entered_id, data, context=None):
    with tracer.start_as_current_span("send_message_to_kafka") as span:
        message = {
            'type': request_type,
            'id': entered_id,
            'data': data
        }

        # Inject context only if it does not already exist
        carrier = {}
        current_context = context if context else trace.set_span_in_context(span)
        propagator.inject(carrier, context=current_context)
        
        # Ensure no duplicate traceparent headers
        headers = {k: v for k, v in carrier.items()}
        if 'traceparent' in headers:
            headers = [(key, bytes(value, 'utf-8')) for key, value in headers.items() if key == 'traceparent']

        logger.info(f"Sending message to Kafka: {message}")
        logger.info(f"Span context before sending: Trace ID: {span.get_span_context().trace_id}, Span ID: {span.get_span_context().span_id}")
        logger.info(f"Injected headers: {carrier}")

        for attempt in range(3):
            try:
                future = producer.send('data_requests', value=message, headers=headers)
                record_metadata = future.get(timeout=3)
                logger.info(f"Message sent to Kafka topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")
                return
            except KafkaTimeoutError as e:
                logger.error(f"Failed to send message to Kafka (attempt {attempt + 1}/3): {e}")
                time.sleep(4)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return

def get_result_from_kafka(entered_id):
    consumer = KafkaConsumer(
        'data_responses',
        bootstrap_servers=kafka_broker,
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='api_gateway_group',
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    )

    for msg in consumer:
        traceparent_header = next((header[1].decode('utf-8') for header in msg.headers if header[0] == 'traceparent'), None)
        headers = {'traceparent': traceparent_header} if traceparent_header else {}
        
        extracted_context = propagator.extract(carrier=headers, getter=DictGetter())

        with tracer.start_as_current_span("process_kafka_message", context=extracted_context) as span:
            logger.info(f"Using span: Trace ID: {span.get_span_context().trace_id}, Span ID: {span.get_span_context().span_id}")
            
            if msg.value['id'] == entered_id:
                consumer.close()
                data = msg.value['data']
                if data and '_id' in data:
                    data['id'] = data.pop('_id')
                return data

    consumer.close()
    return None

# Define Pydantic models
class BaseItem(BaseModel):
    name: str
    price: int
    year: str

class Item(BaseItem):
    id: int

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    return templates.TemplateResponse("portfolio.html", {"request": request})

@app.get("/myapi/{entered_id}", response_model=Item)
async def get_item(entered_id: int):
    logger.info(f"Received GET request for ID {entered_id}")
    with tracer.start_as_current_span("get_request") as span:
        logger.info(f"Span context: Trace ID: {span.get_span_context().trace_id}, Span ID: {span.get_span_context().span_id}")
        cached_data = get_data_from_redis(entered_id)
        if cached_data:
            logger.info(f"Found cached data for ID {entered_id}")
            data = json.loads(cached_data)
            return data

        logger.info(f"Cached data not found for ID {entered_id}. Sending message to Kafka.")
        send_message_to_kafka('GET', entered_id, None, context=trace.set_span_in_context(span))
        data = get_result_from_kafka(entered_id)
        if data:
            if 'error' in data:
                raise HTTPException(status_code=400, detail=data['error'])
            logger.info(f"Received data from Kafka for ID {entered_id}. Caching the data.")
            cache_data_in_redis(entered_id, data)

            return data

        raise HTTPException(status_code=404, detail=f"Could not find data with ID {entered_id}")

@app.put("/myapi/{entered_id}", response_model=Item)
async def put_item(entered_id: int, item: BaseItem):
    logger.info(f"Received PUT request for ID {entered_id}")
    data = item.dict()
    data['id'] = entered_id  # Add ID to the data
    with tracer.start_as_current_span("put_request") as span:
        logger.info(f"Span context: Trace ID: {span.get_span_context().trace_id}, Span ID: {span.get_span_context().span_id}")
        context = trace.set_span_in_context(span)
        send_message_to_kafka('PUT', entered_id, data, context=context)
        result = get_result_from_kafka(entered_id)

    if result:
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        return result
    raise HTTPException(status_code=404, detail=f"Could not find data with ID {entered_id}")

@app.patch("/myapi/{entered_id}", response_model=Item)
async def patch_item(entered_id: int, item: BaseItem):
    logger.info(f"Received PATCH request for ID {entered_id}")
    data = {key: value for key, value in item.dict().items() if value is not None}
    data['id'] = entered_id  # Add ID to the data
    with tracer.start_as_current_span("patch_request") as span:
        logger.info(f"Span context: Trace ID: {span.get_span_context().trace_id}, Span ID: {span.get_span_context().span_id}")
        context = trace.set_span_in_context(span)
        send_message_to_kafka('PATCH', entered_id, data, context=context)
        result = get_result_from_kafka(entered_id)

    if result:
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        return result
    raise HTTPException(status_code=404, detail=f"Could not find data with ID {entered_id}")

@app.delete("/myapi/{entered_id}", status_code=204)
async def delete_item(entered_id: int):
    logger.info(f"Received DELETE request for ID {entered_id}")
    with tracer.start_as_current_span("delete_request") as span:
        logger.info(f"Span context: Trace ID: {span.get_span_context().trace_id}, Span ID: {span.get_span_context().span_id}")
        context = trace.set_span_in_context(span)
        send_message_to_kafka('DELETE', entered_id, None, context=context)
        result = get_result_from_kafka(entered_id)

    if result is not None:
        return JSONResponse(status_code=204)
    raise HTTPException(status_code=404, detail=f"Could not find data with ID {entered_id}")

def run_health_checks():
    logger.info("Starting health checks...")
    redis_status = check_redis()
    kafka_status = check_kafka()

    if redis_status:
        logger.info("Redis health check passed.")
    else:
        logger.error("Redis health check failed.")

    if kafka_status:
        logger.info("Kafka health check passed.")
    else:
        logger.error("Kafka health check failed")

    if redis_status and kafka_status:
        ensure_kafka_topics()
        logger.info("Health checks passed. Starting the application.")
    else:
        logger.error("Health checks failed. Application not started.")

@app.on_event("startup")
async def startup_event():
    run_health_checks()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
