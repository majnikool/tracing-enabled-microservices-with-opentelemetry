# Use Python 3.9 Debian Bullseye image as the base image
FROM python:3.9-slim-bullseye as base

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    rustc \
    cargo \
    gcc \
    vim \
    netcat \
    net-tools \
    curl \
    procps && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --upgrade pip wheel

# Use pip to build wheels for cryptography
RUN pip wheel --wheel-dir=/root/wheels cryptography

# Start a new stage from the Python 3.9 Debian Bullseye image
FROM python:3.9-slim-bullseye as release

# Ensure we are running as root for installations
USER root

# Install system libraries
RUN apt-get update && apt-get install -y \
    gcc \
    vim \
    netcat \
    net-tools \
    curl \
    procps && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Expose port for the Gunicorn server
EXPOSE 80

# Add directories where debugging tools are installed to the PATH
ENV PATH="/usr/sbin:/sbin:${PATH}"

# Copy pre-built wheels from the base stage
COPY --from=base /root/wheels /root/wheels

# Copy the requirements.txt file
COPY requirements.txt .

# Install packages from wheels and the local dist folder
RUN pip install --no-index --find-links=/root/wheels /root/wheels/* && \
    pip install -r requirements.txt && \
    rm -rf /root/wheels

# Copy static files and templates
COPY src/example/static/ ./static/
COPY src/example/templates ./templates/

# Copy the application code
COPY src/example /app

# Copy startup script and make it executable
COPY start.sh ./
RUN chmod +x start.sh

# Ensure we are running as root
USER root

# Define the command to run on container start
CMD ["./start.sh"]
