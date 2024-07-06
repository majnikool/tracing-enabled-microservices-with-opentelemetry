import json
import os
import logging
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from opentelemetry import trace, context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.propagate import extract, inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from mongoengine import connect, DoesNotExist, disconnect
from config import MONGO_URI
from models import Car

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Suppress verbose Kafka logs
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.consumer.fetcher').setLevel(logging.WARNING)
logging.getLogger('kafka.protocol.parser').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)

# Custom logger function
def custom_logger(msg, level=logging.INFO, exc_info=None):
    span = trace.get_current_span()
    span_context = span.get_span_context()
    extra = {
        'trace_id': '{:032x}'.format(span_context.trace_id) if span_context.is_valid else "N/A",
        'span_id': '{:016x}'.format(span_context.span_id) if span_context.is_valid else "N/A"
    }
    if level == logging.ERROR:
        logger.error(msg, extra=extra, exc_info=exc_info)
    elif level == logging.WARNING:
        logger.warning(msg, extra=extra)
    elif level == logging.DEBUG:
        logger.debug(msg, extra=extra)
    else:
        logger.info(msg, extra=extra)

# OpenTelemetry Setup
def initialize_tracer():
    if os.getenv('ENABLE_TRACING', 'true').lower() == 'true':
        otlp_endpoint = os.getenv('OTLP_ENDPOINT', 'localhost:4317')
        resource = Resource.create({"service.name": "data_processor"})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

# Kafka Setup
kafka_broker = os.getenv('KAFKA_BROKER', 'localhost:9092')
topics = ['data_requests', 'data_responses']

# Ensure Kafka topics exist
def ensure_kafka_topics():
    admin_client = KafkaAdminClient(bootstrap_servers=kafka_broker)
    existing_topics = admin_client.list_topics()
    for topic in topics:
        if topic not in existing_topics:
            try:
                admin_client.create_topics([NewTopic(name=topic, num_partitions=1, replication_factor=1)])
                custom_logger(f"Created Kafka topic: {topic}")
            except TopicAlreadyExistsError:
                custom_logger(f"Kafka topic {topic} already exists")

ensure_kafka_topics()

KafkaInstrumentor().instrument()
PymongoInstrumentor().instrument()

producer = KafkaProducer(bootstrap_servers=kafka_broker, value_serializer=lambda v: json.dumps(v).encode('utf-8'))
consumer = KafkaConsumer('data_requests', bootstrap_servers=kafka_broker, auto_offset_reset='earliest', enable_auto_commit=False, group_id='data_processor_group', value_deserializer=lambda v: json.loads(v.decode('utf-8')))

# MongoDB connection
disconnect(alias='default')
connect(host=MONGO_URI)

# Process message function
def process_message(message, headers):
    try:
        # Extract context from Kafka message headers
        custom_logger(f"Original headers: {headers}")
        carrier = {key: value.decode('utf-8') if isinstance(value, bytes) else value for key, value in headers}
        custom_logger(f"Carrier for context extraction: {carrier}")
        extracted_context = extract(carrier)
        custom_logger(f"Extracted trace context from headers: {headers}")

        # Use the extracted context for the new span
        with trace.use_span(trace.get_current_span(), end_on_exit=True):
            with trace.get_tracer(__name__).start_as_current_span(f"process_{message['type']}_request", context=extracted_context):
                custom_logger(f"Started span for processing request: {message['type']} with ID {message['id']}")

                data = None

                # MongoDB operations
                with trace.get_tracer(__name__).start_as_current_span("mongodb_operation") as mongo_span:
                    custom_logger(f"Current MongoDB operation span: Trace ID: {mongo_span.get_span_context().trace_id}, Span ID: {mongo_span.get_span_context().span_id}")
                    mongo_span.set_attribute("db.system", "mongodb")
                    mongo_span.set_attribute("db.name", "testapp")

                    if message["type"] == "GET":
                        try:
                            custom_logger(f"Attempting to GET document with ID: {message['id']}")
                            result = Car.objects.get(id=message["id"])
                            data = result.to_mongo().to_dict()
                            custom_logger(f"Data for GET request: {data}")
                        except DoesNotExist:
                            custom_logger(f"No data found for ID {message['id']}")

                    elif message["type"] == "PUT":
                        try:
                            custom_logger(f"Attempting to PUT document with data: {message['data']}")
                            new_car = Car(**message["data"])
                            new_car.save()
                            data = new_car.to_mongo().to_dict()
                            custom_logger(f"Data for PUT request: {data}")
                        except Exception as e:
                            custom_logger(f"Error during PUT operation: {e}", level=logging.ERROR)

                    elif message["type"] == "PATCH":
                        try:
                            custom_logger(f"Attempting to PATCH document with ID: {message['id']} and data: {message['data']}")
                            car = Car.objects.get(id=message["id"])
                            for key, value in message["data"].items():
                                setattr(car, key, value)
                            car.save()
                            data = car.to_mongo().to_dict()
                            custom_logger(f"Data for PATCH request: {data}")
                        except DoesNotExist:
                            custom_logger(f"No data found for ID {message['id']}")
                        except Exception as e:
                            custom_logger(f"Error during PATCH operation: {e}", level=logging.ERROR)

                    elif message["type"] == "DELETE":
                        try:
                            custom_logger(f"Attempting to DELETE document with ID: {message['id']}")
                            car = Car.objects.get(id=message["id"])
                            car.delete()
                            data = {'status': 'deleted'}
                            custom_logger(f"DELETE request processed for ID {message['id']}")
                        except DoesNotExist:
                            custom_logger(f"No data found for ID {message['id']}")
                        except Exception as e:
                            custom_logger(f"Error during DELETE operation: {e}", level=logging.ERROR)

                response_message = {
                    'id': message['id'],
                    'data': data,
                    'context': {}
                }

                # Inject context into response
                TraceContextTextMapPropagator().inject(response_message['context'])
                custom_logger(f"Carrier after context injection: {response_message['context']}")

                # Ensure headers are in the correct format
                kafka_headers = [(key, value.encode('utf-8')) for key, value in response_message['context'].items()]
                producer.send('data_responses', value=response_message, headers=kafka_headers)
                producer.flush()
                custom_logger("Response message sent to Kafka")
    except Exception as e:
        custom_logger(f"Error processing message: {e}", level=logging.ERROR, exc_info=True)

# Main loop to consume Kafka messages
if __name__ == "__main__":
    initialize_tracer()
    try:
        custom_logger("Starting to consume messages from Kafka")
        while True:
            for msg in consumer:
                process_message(msg.value, msg.headers)
                consumer.commit()
                custom_logger(f"Processed and committed message for ID {msg.value['id']}")
    except KeyboardInterrupt:
        custom_logger("Shutting down gracefully")
    except Exception as e:
        custom_logger(f"Unexpected error: {e}", level=logging.ERROR, exc_info=True)
    finally:
        producer.close()
        disconnect(alias='default')