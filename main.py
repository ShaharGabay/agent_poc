import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Set via env var or k8s secret
MCP_WEATHER_URL = os.getenv("MCP_WEATHER_URL", "http://weather-service:8001/mcp")
MCP_PACKING_URL = os.getenv("MCP_PACKING_URL", "http://packing-service:8002/mcp")
LLM_TIMEOUT = 5

# Global state
llm = None
mcp_tools = []

print("Initializing Gemini LLM...")
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=GEMINI_API_KEY,
        temperature=0,
        max_retries=0  # Disable retries to fail fast on quota errors
    )
    print("✅ Gemini LLM initialized")
except Exception as e:
    print(f"❌ Failed to initialize Gemini: {e}")


class TravelQuery(BaseModel):
    query: str


async def load_mcp_tools_from_server(server_url: str) -> list:
    """Load tools from an MCP server using streamable HTTP"""
    tools = []
    try:
        print(f"Connecting to {server_url}...")
        async with streamablehttp_client(server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                server_tools = await load_mcp_tools(session)
                tools.extend(server_tools)
                print(f"✅ Loaded {len(server_tools)} tools from {server_url}")
    except Exception as e:
        print(f"⚠️  Could not load tools from {server_url}: {e}")
    return tools


async def initialize_tools():
    """Load all MCP tools"""
    global mcp_tools
    print("Loading MCP tools...")
=    
    # Load from weather service
    weather_tools = await load_mcp_tools_from_server(MCP_WEATHER_URL)
    mcp_tools.extend(weather_tools)
    
    # Load from packing service
    packing_tools = await load_mcp_tools_from_server(MCP_PACKING_URL)
    mcp_tools.extend(packing_tools)
    
    print(f"Total {len(mcp_tools)} MCP tools loaded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_tools()
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="LangChain Travel Assistant with MCP Tools",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LangChain Travel Assistant with MCP Tools",
        "tools": [t.name for t in mcp_tools]
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_ready": llm is not None,
        "mcp_tools_loaded": len(mcp_tools),
        "tools": [
            {
                "name": tool.name,
                "description": tool.description if hasattr(tool, 'description') else "N/A"
            }
            for tool in mcp_tools
        ]
    }


@app.post("/ask")
async def ask(query: TravelQuery):
    """Ask a question using MCP tools"""
    if not llm:
        return {
            "error": "LLM not initialized",
            "query": query.query
        }
    
    if not mcp_tools:
        return {
            "error": "No MCP tools loaded",
            "query": query.query
        }
    
    try:
        llm_with_tools = llm.bind_tools(mcp_tools)
        response = await asyncio.wait_for(
            llm_with_tools.ainvoke(query.query),
            timeout=LLM_TIMEOUT
        )
        
        return {
            "query": query.query,
            "answer": response.content if hasattr(response, 'content') else str(response),
            "tool_calls": response.tool_calls if hasattr(response, 'tool_calls') else [],
            "tools_available": [t.name for t in mcp_tools]
        }
    except asyncio.TimeoutError:
        return {
            "error": "Request timed out. This might be due to API quota limits or slow response.",
            "query": query.query,
            "suggestion": "Check Gemini API quotas at https://ai.google.dev/"
        }
    except Exception as e:
        return {
            "error": str(e),
            "query": query.query
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
