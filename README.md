# LangChain Agent with MCP Services in Kubernetes

A proof-of-concept demonstrating a LangChain agent using FastMCP services running as microservices in a KIND (Kubernetes in Docker) cluster.

## Architecture

```
┌─────────────────┐
│  Travel Agent   │  (LangChain + Ollama/Gemini)
│    (Port 8000)  │
└────────┬────────┘
         │
         ├──MCP──► Weather Service (Port 8001)
         │
         └──MCP──► Travel Service (Port 8002)
```

- **Agent**: LangChain ReAct agent using Ollama (local) or Google Gemini
- **MCP Services**: FastMCP servers exposing tools via streamable HTTP
- **Integration**: `langchain-mcp-adapters` for auto-discovery of MCP tools
- **Platform**: Kubernetes (KIND) with standard Deployments and Services

## Key Components

1. **`main.py`** - LangChain agent that connects to MCP services
2. **`weather_service.py`** - FastMCP service with `get_weather` tool
3. **`travel_service.py`** - FastMCP service with `get_tourist_attractions` and `get_local_food` tools
4. **`k8s-manifests.yaml`** - Kubernetes deployments and services
5. **`deploy-langchain.sh`** - Build, load, and deploy script

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [KIND](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Ollama](https://ollama.ai/) (for local LLM) or [Google Gemini API key](https://ai.google.dev/)

## Quick Start

### 1. Install and Run Ollama

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama server on a specific port
export OLLAMA_HOST=127.0.0.1:11435
ollama serve
```

In another terminal, pull the model:
```bash
OLLAMA_HOST=127.0.0.1:11435 ollama pull llama3.2
```

### 2. Create KIND cluster

```bash
kind create cluster --name local-cluster
```

### 3. Deploy

```bash
chmod +x deploy-langchain.sh
./deploy-langchain.sh
```

The script will:
- Build Docker images for all services
- Load them into KIND
- Deploy all services
- Wait for pods to be ready

### 4. Test

```bash
# Health check
curl http://localhost:30080/health

# Ask about weather
curl -X POST http://localhost:30080/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the weather in Tokyo?"}'

# Ask about attractions
curl -X POST http://localhost:30080/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What should I see in Paris?"}'

# Ask about food
curl -X POST http://localhost:30080/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What food should I try in London?"}'
```

## Using Gemini Instead of Ollama

Edit `main.py` and change:
```python
LLM_PROVIDER = "gemini"
GEMINI_API_KEY = "your-api-key-here"
```

## API Endpoints

- `GET /health` - Health check with MCP tool status
- `POST /ask` - Ask a question (body: `{"query": "your question"}`)

## How It Works

1. **Startup**: Agent connects to MCP services and discovers available tools
2. **Request**: User sends a query to the agent
3. **Execution**: LangChain agent uses the LLM to decide which tool to call
4. **MCP Calls**: Agent calls MCP services over HTTP using the MCP protocol
5. **Response**: Agent returns the tool result

## Available Tools

- `get_weather(location)` - Get current weather for a city
- `get_tourist_attractions(location)` - Get top tourist attractions
- `get_local_food(location)` - Get local food recommendations

Supported locations: New York, San Francisco, Seattle, London, Paris, Tokyo

## Cleanup

```bash
kubectl delete -f k8s-manifests.yaml
kind delete cluster --name local-cluster
```

## License

MIT
