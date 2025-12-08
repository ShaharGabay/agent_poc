import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MCP_WEATHER_URL = os.getenv("MCP_WEATHER_URL", "http://weather-service:8001/mcp")
MCP_PACKING_URL = os.getenv("MCP_PACKING_URL", "http://packing-service:8002/mcp")
LLM_TIMEOUT = 30

SYSTEM_PROMPT = (
    "You are a travel assistant. You MUST use the provided tools to answer questions. "
    "Do NOT use your own knowledge. If you cannot answer using the tools, say so. "
    "Keep responses brief."
)

# Global state
llm = None
mcp_tools = []
mcp_client = None
agent = None

print("Initializing Gemini LLM...")
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=GEMINI_API_KEY,
        temperature=0,
        max_retries=0
    )
    print("Gemini LLM initialized")
except Exception as e:
    print(f"Failed to initialize Gemini: {e}")


class TravelQuery(BaseModel):
    query: str


async def initialize_tools():
    """Load all MCP tools and create the agent"""
    global mcp_tools, mcp_client, agent
    print("Loading MCP tools...")
    
    mcp_client = MultiServerMCPClient({
        "weather": {
            "url": MCP_WEATHER_URL,
            "transport": "streamable_http",
        },
        "packing": {
            "url": MCP_PACKING_URL,
            "transport": "streamable_http",
        }
    })
    
    for attempt in range(5):
        try:
            mcp_tools = await mcp_client.get_tools()
            print(f"Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")
            
            # Create the ReAct agent with LangGraph
            agent = create_react_agent(llm, mcp_tools, prompt=SYSTEM_PROMPT)
            print("ReAct agent created")
            return
        except Exception as e:
            print(f"Attempt {attempt + 1}/5 failed: {e}")
            if attempt < 4:
                await asyncio.sleep(2)
    
    print("Failed to load MCP tools after 5 attempts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_tools()
    yield
    print("Shutting down...")


app = FastAPI(
    title="LangChain Travel Assistant with MCP Tools",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "message": "LangChain Travel Assistant with MCP Tools",
        "tools": [t.name for t in mcp_tools]
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "llm_ready": llm is not None,
        "agent_ready": agent is not None,
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
    if not agent:
        return {"error": "Agent not initialized", "query": query.query}
    
    try:
        result = await asyncio.wait_for(
            agent.ainvoke({"messages": [("user", query.query)]}),
            timeout=LLM_TIMEOUT
        )
        
        # Extract the final answer from the last message
        messages = result["messages"]
        final_answer = messages[-1].content if messages else ""
        
        # Collect tool calls from the conversation
        tool_calls = []
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({"name": tc["name"], "args": tc["args"]})
        
        return {
            "query": query.query,
            "answer": final_answer,
            "tool_calls": tool_calls,
            "tools_available": [t.name for t in mcp_tools]
        }
    except asyncio.TimeoutError:
        return {"error": "Request timed out", "query": query.query}
    except Exception as e:
        return {"error": str(e), "query": query.query}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
