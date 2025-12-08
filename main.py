import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

# Configuration
LLM_PROVIDER = "ollama"  # "ollama" or "gemini"
OLLAMA_MODEL = "llama3.2"
OLLAMA_URL = "http://host.docker.internal:11435"
GEMINI_API_KEY = ""  # Set your key here if using Gemini
GEMINI_MODEL = "gemini-2.0-flash-lite"
MCP_WEATHER_URL = "http://weather-service:8001/mcp"
MCP_TRAVEL_URL = "http://travel-service:8002/mcp"
LLM_TIMEOUT = 60

SYSTEM_PROMPT = (
    "You are a travel assistant with no knowledge of your own. "
    "You can ONLY answer using the provided tools. "
    "If no tool can answer the question, say 'I don't know'. "
    "Never make up information. Only return what the tools give you."
)

# Global state (initialized on startup)
agent = None
tools = []


class TravelQuery(BaseModel):
    query: str


def create_llm():
    """Create LLM based on configured provider."""
    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        print(f"Using Ollama ({OLLAMA_MODEL}) at {OLLAMA_URL}")
        return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_URL, temperature=0)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print(f"Using Gemini ({GEMINI_MODEL})")
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0,
            max_retries=0,
        )


async def initialize():
    """Initialize LLM, load MCP tools, and create the ReAct agent."""
    global agent, tools
    
    # 1. Initialize LLM
    llm = create_llm()
    
    # 2. Connect to MCP servers and load tools
    mcp_client = MultiServerMCPClient({
        "weather": {"url": MCP_WEATHER_URL, "transport": "streamable_http"},
        "travel": {"url": MCP_TRAVEL_URL, "transport": "streamable_http"},
    })
    tools = await mcp_client.get_tools()
    print(f"Loaded MCP tools: {[t.name for t in tools]}")
    
    # 3. Create ReAct agent with rate limiting hook
    agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)
    print("Agent ready")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize()
    yield


app = FastAPI(title="Travel Assistant", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "tools": [t.name for t in tools]
    }


@app.post("/ask")
async def ask(query: TravelQuery):
    try:
        result = await asyncio.wait_for(
            agent.ainvoke({"messages": [("user", query.query)]}),
            timeout=LLM_TIMEOUT
        )
        
        messages = result["messages"]
        answer = messages[-1].content if messages else ""
        
        # Extract tool calls for visibility
        tool_calls = [
            {"name": tc["name"], "args": tc["args"]}
            for msg in messages
            if hasattr(msg, 'tool_calls') and msg.tool_calls
            for tc in msg.tool_calls
        ]
        
        return {"query": query.query, "answer": answer, "tool_calls": tool_calls}
    
    except asyncio.TimeoutError:
        return {"error": "Request timed out", "query": query.query}
    except Exception as e:
        return {"error": str(e), "query": query.query}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
