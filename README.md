# LangChain Agent with MCP Services in Kubernetes

A proof-of-concept demonstrating a LangChain agent using FastMCP services running as microservices in a KIND (Kubernetes in Docker) cluster.

## Architecture

```
┌─────────────────┐
│  Travel Agent   │  (LangChain + Gemini)
│    (Port 8000)  │
└────────┬────────┘
         │
         ├──MCP──► Weather Service (Port 8001)
         │
         └──MCP──► Packing Service (Port 8002)
```

- **Agent**: LangChain ReAct agent using Google Gemini
- **MCP Services**: FastMCP servers exposing tools via streamable HTTP
- **Integration**: `langchain-mcp-adapters` for auto-discovery of MCP tools
- **Platform**: Kubernetes (KIND) with standard Deployments and Services

## Key Components

1. **`main.py`** - LangChain agent that connects to MCP services
2. **`weather_service.py`** - FastMCP service with `get_weather` tool
3. **`packing_service.py`** - FastMCP service with `suggest_packing_items` tool
4. **`k8s-manifests.yaml`** - Kubernetes deployments and services
5. **`deploy-langchain.sh`** - Build, load, and deploy script

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [KIND](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Google Gemini API key](https://ai.google.dev/)

## Quick Start

### 1. Create KIND cluster

```bash
kind create cluster --name local-cluster
```

### 2. Set your Gemini API key

```bash
export GEMINI_API_KEY='your-api-key-here'
```

### 3. Deploy

```bash
chmod +x deploy-langchain.sh
./deploy-langchain.sh
```

The script will:
- Build Docker images for all services
- Load them into KIND
- Create Kubernetes secret for API key
- Deploy all services
- Wait for pods to be ready

### 4. Test

```bash
# Health check
curl http://localhost:30080/health | jq

# Ask a question
curl -X POST http://localhost:30080/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What should I pack for Tokyo in winter?"}' | jq
```

## API Endpoints

- `GET /` - Welcome message with loaded tools
- `GET /health` - Health check with MCP tool status
- `POST /ask` - Ask a question (body: `{"query": "your question"}`)

## How It Works

1. **Startup**: Agent connects to MCP services using `streamablehttp_client`
2. **Tool Discovery**: `langchain-mcp-adapters` auto-discovers tools from MCP services
3. **Request**: User sends a query to the agent
4. **Execution**: LangChain agent uses Gemini to decide which tools to call
5. **MCP Calls**: Agent calls MCP services over HTTP using the MCP protocol
6. **Response**: Agent synthesizes results and returns answer

## MCP Protocol

FastMCP services expose tools via the MCP (Model Context Protocol):
- Transport: Streamable HTTP
- Endpoint: `/mcp` (POST)
- Discovery: Automatic via `tools/list` method
- Execution: Tools called via `tools/call` method

## Environment Variables

- `GEMINI_API_KEY` - Your Google Gemini API key (required)
- `MCP_WEATHER_URL` - Weather service URL (default: `http://weather-service:8001/mcp`)
- `MCP_PACKING_URL` - Packing service URL (default: `http://packing-service:8002/mcp`)

## Cleanup

```bash
kubectl delete -f k8s-manifests.yaml
kind delete cluster --name local-cluster
```

## Key Learnings

### MCP in Kubernetes

✅ **Works well**: MCP services can run as independent microservices  
✅ **Auto-discovery**: Tools are discovered at startup via the MCP protocol  
✅ **Service mesh ready**: Standard Kubernetes DNS and networking  

⚠️ **Considerations**:
- MCP clients need to connect at startup (lifespan events)
- Quota/rate limits should fail fast (`max_retries=0`)
- MCP services must bind to `0.0.0.0` (not `127.0.0.1`) in containers

### Architecture Benefits

- **Scalability**: Each MCP service can scale independently
- **Reusability**: Any agent in the cluster can use the MCP services
- **Isolation**: Services can crash/restart independently
- **Flexibility**: Easy to add new MCP tools without changing the agent

## License

MIT
