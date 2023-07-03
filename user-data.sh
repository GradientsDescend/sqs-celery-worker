#!/bin/bash
export AWS_REGION="us-east-1"
export SQS_URL="sqs://"
apt-get update -qq
apt-get -qq -y install python3 python3-pip git
curl -fsSL https://get.docker.com | bash -
curl -L "https://github.com/docker/compose/releases/download/v2.19.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
cd /opt
git clone https://github.com/GradientsDescend/sqs-celery-worker.git celery
cd celery
docker-compose up -d
