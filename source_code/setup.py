from setuptools import find_packages, setup

setup(
    name="example-app",
    version="0.1.0",
    author="Majid",
    author_email="majidnik@gmail.com",
    description="An example app",
    keywords="FastAPI example",
    include_package_data=True,
    python_requires='>=3.9',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    zip_safe=False,
    install_requires=[
        "fastapi",
        "uvicorn",
        "kafka-python",
        "redis",
        "mongoengine",
        "opentelemetry-api",
        "opentelemetry-sdk",
        "opentelemetry-instrumentation",
        "opentelemetry-instrumentation-fastapi",
        "opentelemetry-instrumentation-kafka-python",
        "opentelemetry-instrumentation-pymongo",
        "opentelemetry-instrumentation-redis",
        "opentelemetry-instrumentation-logging",
        "opentelemetry-exporter-otlp",
        "opentelemetry-exporter-otlp-proto-grpc"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)
