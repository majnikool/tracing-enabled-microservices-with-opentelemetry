#!/bin/sh

if [ "$SERVICE" = "api_gateway" ]; then
    # Start the FastAPI API Gateway with Uvicorn
    export PYTHONPATH=/app
    uvicorn app:app --host 0.0.0.0 --port 80 --log-level info
elif [ "$SERVICE" = "data_processor" ]; then
    # Start the Data Processor service
    python /app/data_processor.py
else
    echo "Invalid service specified. Set the SERVICE environment variable to 'api_gateway' or 'data_processor'."
    exit 1
fi
