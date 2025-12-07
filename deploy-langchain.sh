#!/bin/bash
set -e

echo "🏗️  Building Docker images..."

# Build images
docker build -f Dockerfile.weather -t weather-service:latest .
docker build -f Dockerfile.packing -t packing-service:latest .
docker build -f Dockerfile.agent -t travel-agent:latest .

echo "📦 Loading images into KIND..."

# Load into KIND
kind load docker-image weather-service:latest --name local-cluster
kind load docker-image packing-service:latest --name local-cluster
kind load docker-image travel-agent:latest --name local-cluster

echo "🔑 Creating Gemini API key secret..."

# Create secret from environment variable
if [ -z "$GEMINI_API_KEY" ]; then
  echo "❌ ERROR: GEMINI_API_KEY environment variable not set!"
  echo "   Set it with: export GEMINI_API_KEY='your-key-here'"
  exit 1
fi

kubectl create secret generic gemini-api-key \
  --from-literal=api-key="$GEMINI_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "🚀 Deploying to Kubernetes..."

kubectl apply -f k8s-manifests.yaml

echo "⏳ Waiting for pods to be ready..."

kubectl wait --for=condition=ready pod -l app=weather-service --timeout=60s
kubectl wait --for=condition=ready pod -l app=packing-service --timeout=60s
kubectl wait --for=condition=ready pod -l app=travel-agent --timeout=60s

echo "✅ Deployment complete!"
echo ""
echo "📊 Pod status:"
kubectl get pods

echo ""
echo "🌐 Services:"
kubectl get services

echo ""
echo "🧪 Test the agent:"
echo "  curl http://localhost:30080/health"
echo "  curl http://localhost:30080/ask/Paris"
echo '  curl -X POST http://localhost:30080/ask -H "Content-Type: application/json" -d '"'"'{"query":"What should I pack for Tokyo in winter?"}'"'"

