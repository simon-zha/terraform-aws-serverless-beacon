FROM --platform=x86_64 public.ecr.aws/sam/build-python3.12:latest-x86_64 as builder

RUN dnf update -y \
&& dnf install -y git tar make openssl-devel libcurl-devel wget bzip2-devel xz-devel libffi-devel zlib-devel autoconf intltool \
&& dnf install -y gcc gcc-c++ cmake \
&& dnf install -y docker 

RUN wget https://releases.hashicorp.com/terraform/1.9.4/terraform_1.9.4_linux_amd64.zip \
&& unzip terraform_1.9.4_linux_amd64.zip -d /usr/bin/ \
&& pip install --upgrade pip

COPY requirements.txt ./
RUN pip install -r requirements.txt
