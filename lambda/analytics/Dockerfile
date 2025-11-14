FROM --platform=x86_64 public.ecr.aws/lambda/python:3.12 AS build

# Lambda workdir：/var/task（$LAMBDA_TASK_ROOT）
WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .


RUN dnf install -y gcc gcc-c++ cmake \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -t /opt/python

FROM --platform=x86_64 public.ecr.aws/lambda/python:3.12

COPY --from=build /opt/python /opt/python
ENV PYTHONPATH="/opt/python:${PYTHONPATH}"

COPY *.py ${LAMBDA_TASK_ROOT}/
ADD shared ${LAMBDA_TASK_ROOT}/shared

# Lambda handler
CMD [ "lambda_function.lambda_handler" ]

# DOCS: https://docs.aws.amazon.com/lambda/latest/dg/python-image.html#python-image-instructions
# build : docker build -t docker-image:test .
# run   : docker run --rm -p 9000:8080 docker-image:test
# test  : curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{<BODY>}'
