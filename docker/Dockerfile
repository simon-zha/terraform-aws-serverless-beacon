# FROM --platform=x86_64 public.ecr.aws/sam/build-python3.12:latest-x86_64

# RUN dnf update -y \
# && dnf install -y git tar make openssl-devel libcurl-devel wget bzip2-devel xz-devel libffi-devel zlib-devel autoconf intltool \
# && dnf install -y gcc gcc-c++ cmake \
# && dnf install -y docker 

# RUN wget https://releases.hashicorp.com/terraform/1.9.4/terraform_1.9.4_linux_amd64.zip \
# && unzip terraform_1.9.4_linux_amd64.zip -d /usr/bin/ \
# && pip install --upgrade pip

# COPY requirements.txt ./
# RUN pip install -r requirements.txt

FROM --platform=x86_64 public.ecr.aws/sam/build-python3.12:latest-x86_64 AS builder

RUN dnf update -y \
&& dnf install -y git tar make openssl-devel libcurl-devel wget bzip2-devel xz-devel libffi-devel zlib-devel autoconf intltool python3.12-devel \
&& dnf install -y gcc gcc-c++ cmake \
&& dnf install -y docker \
&& dnf clean all


RUN python3.12 -m venv /opt/venv


COPY requirements.txt ./
RUN /opt/venv/bin/pip install --upgrade pip \
&& /opt/venv/bin/pip install -r requirements.txt


RUN wget https://releases.hashicorp.com/terraform/1.9.4/terraform_1.9.4_linux_amd64.zip \
&& unzip terraform_1.9.4_linux_amd64.zip -d /usr/local/bin/


FROM --platform=x86_64 public.ecr.aws/amazonlinux/amazonlinux:2023

RUN dnf update -y \
&& dnf install -y python3.12 docker \
&& dnf clean all \
&& rm -rf /var/cache/dnf

COPY --from=builder /opt/venv /opt/venv

COPY --from=builder /usr/local/bin/terraform /usr/local/bin/terraform


ENV PATH="/opt/venv/bin:$PATH"


WORKDIR /app
COPY . .
