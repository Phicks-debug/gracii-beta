# Tên image và tag
IMAGE_NAME = gracii
TAG = 1.0.0
REGION = ap-southeast-1
ACCOUNT_ID = 130506138320
ECR_REGISTRY = $(ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com
ECR_IMAGE = $(ECR_REGISTRY)/$(IMAGE_NAME):$(TAG)

# Define all targets
.PHONY: all build run push login logout clean

# Default target
all: build run

# Build Docker image
build:
	docker build -t $(IMAGE_NAME):$(TAG) .

# Run Docker Container
run:
	docker run -d -p 8052:8052 --name $(IMAGE_NAME) $(IMAGE_NAME):$(TAG)

# Push image to ECR
push: login
	docker tag $(IMAGE_NAME):$(TAG) $(ECR_IMAGE)
	docker push $(ECR_IMAGE)

# Login to ECR
login:
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)

# Logout of ECR
logout:
	docker logout $(ECR_REGISTRY)

# Clean docker containers and images
clean:
	docker rm -f $(IMAGE_NAME) || true
	docker rmi -f $(IMAGE_NAME):$(TAG) || true