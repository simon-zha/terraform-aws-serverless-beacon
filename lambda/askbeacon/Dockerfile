FROM --platform=x86_64 public.ecr.aws/lambda/python:3.12 AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=1

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .

# TODO remove after replacing pyorc with PyArrow
RUN dnf install -y gcc gcc-c++ make cmake \
    && python -m pip install --upgrade pip==24.2 \
    && pip install --no-cache-dir -r requirements.txt -t /opt/python \
    && dnf clean all && rm -rf /var/cache/dnf

FROM --platform=x86_64 public.ecr.aws/lambda/python:3.12

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=1 \
    PYTHONPATH="/opt/python:${PYTHONPATH}"

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=build /opt/python /opt/python

COPY *.py ${LAMBDA_TASK_ROOT}/
COPY shared ${LAMBDA_TASK_ROOT}/shared
COPY analytics_utils ${LAMBDA_TASK_ROOT}/analytics_utils
COPY utils ${LAMBDA_TASK_ROOT}/utils

# (Deactivated) Pre-warm libraries (a little prayer to improve load times)
# RUN python -c "import pandas as pd, numpy as np, matplotlib.pyplot as plt, langchain; print('Libraries loaded')"

# Lambda handler
CMD [ "lambda_function.lambda_handler" ]

# DOCS: https://docs.aws.amazon.com/lambda/latest/dg/python-image.html#python-image-instructions
# build: docker build -t docker-image:test .
# run  : docker run --rm -p 9000:8080 docker-image:test
# test : curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{<BODY>}'
