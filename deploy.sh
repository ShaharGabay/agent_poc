#!/bin/bash
set -e

# Check for required argument
if [ -z "$1" ]; then
    echo "Usage: $0 <langchain|crewai>"
    echo "  langchain - Deploy with LangChain agent"
    echo "  crewai    - Deploy with CrewAI agent"
    exit 1
fi

AGENT_TYPE="$1"

if [ "$AGENT_TYPE" != "langchain" ] && [ "$AGENT_TYPE" != "crewai" ]; then
    echo "Error: Invalid agent type '$AGENT_TYPE'"
    echo "Usage: $0 <langchain|crewai>"
    exit 1
fi

AGENT_FILE="${AGENT_TYPE}_agent.py"
echo "Deploying with $AGENT_TYPE agent ($AGENT_FILE)..."

echo "Building Docker images..."
docker build -f Dockerfile.weather -t weather-service:latest .
docker build -f Dockerfile.travel -t travel-service:latest .
docker build -f Dockerfile.agent -t travel-agent:latest --build-arg AGENT_FILE="$AGENT_FILE" .

echo "Loading images into KIND..."
kind load docker-image weather-service:latest --name local-cluster
kind load docker-image travel-service:latest --name local-cluster
kind load docker-image travel-agent:latest --name local-cluster

echo "Deleting existing deployments..."
kubectl delete deployment weather-service travel-service travel-agent --ignore-not-found=true

echo "Deploying MCP services..."
kubectl apply -f k8s-manifests.yaml

echo "Waiting for MCP services to be ready..."
kubectl rollout status deployment/weather-service --timeout=60s
kubectl rollout status deployment/travel-service --timeout=60s

# Wait for MCP endpoints to be accessible before starting the agent
echo "Waiting for MCP endpoints to respond..."
kubectl wait --for=condition=ready pod -l app=weather-service --timeout=60s
kubectl wait --for=condition=ready pod -l app=travel-service --timeout=60s
sleep 2  # Give services a moment to start accepting connections

echo "Deploying travel agent..."
kubectl rollout status deployment/travel-agent --timeout=60s

echo ""
echo "Deployment complete! (using $AGENT_TYPE)"
kubectl get pods

echo ""
echo "Test with:"
echo '  curl -X POST http://localhost:30080/ask -H "Content-Type: application/json" -d '\''{"query":"What is the weather in Tokyo?"}'\'''
echo '  curl -X POST http://localhost:30080/ask -H "Content-Type: application/json" -d '\''{"query":"What should I see in Paris?"}'\'''
echo '  curl -X POST http://localhost:30080/ask -H "Content-Type: application/json" -d '\''{"query":"What food should I try in London?"}'\'''

