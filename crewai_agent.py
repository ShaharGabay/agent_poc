import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Configuration
OLLAMA_MODEL = "llama3.2"
OLLAMA_URL = "http://host.docker.internal:11435"

# Set Ollama base URL for litellm (used by CrewAI)
os.environ["OLLAMA_API_BASE"] = OLLAMA_URL
MCP_WEATHER_URL = "http://weather-service:8001/mcp"
MCP_TRAVEL_URL = "http://travel-service:8002/mcp"
LLM_TIMEOUT = 60

# Global state
crew_agent = None
mcp_tools = []


class TravelQuery(BaseModel):
    query: str


class MCPToolWrapper(BaseTool):
    """Wrapper to convert MCP tools to CrewAI tools."""
    name: str
    description: str
    mcp_url: str
    mcp_tool_name: str

    def _run(self, location: str) -> str:
        """Get information for a location. Args: location (str) - the city name."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_run(location))
            loop.close()
            return result
        except Exception as e:
            return f"Error calling tool: {e}"

    async def _async_run(self, location: str) -> str:
        """Call the MCP tool asynchronously."""
        async with streamablehttp_client(self.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    self.mcp_tool_name,
                    arguments={"location": location}
                )
                return result.content[0].text if result.content else "No result"


async def load_mcp_tools():
    """Load tools from MCP servers and wrap them for CrewAI."""
    tools = []
    
    mcp_servers = [
        ("weather", MCP_WEATHER_URL),
        ("travel", MCP_TRAVEL_URL),
    ]
    
    for server_name, url in mcp_servers:
        try:
            async with streamablehttp_client(url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    
                    for tool in result.tools:
                        wrapped_tool = MCPToolWrapper(
                            name=tool.name,
                            description=tool.description or f"Tool: {tool.name}",
                            mcp_url=url,
                            mcp_tool_name=tool.name,
                        )
                        tools.append(wrapped_tool)
                        print(f"Loaded tool: {tool.name} from {server_name}")
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")
    
    return tools


async def initialize():
    """Initialize CrewAI agent with MCP tools."""
    global crew_agent, mcp_tools
    
    # Load MCP tools
    mcp_tools = await load_mcp_tools()
    print(f"Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")
    
    # Configure LLM
    llm = f"ollama/{OLLAMA_MODEL}"
    print(f"Using LLM: {llm}")
    
    # Create CrewAI agent
    crew_agent = Agent(
        role="Travel Assistant",
        goal="Help users with travel information using available tools",
        backstory=(
            "You are a travel assistant with no knowledge of your own. "
            "You can ONLY answer using the provided tools. "
            "If no tool can answer the question, say 'I don't know'. "
            "Never make up information. Only return what the tools give you."
        ),
        tools=mcp_tools,
        llm=llm,
        verbose=True,
    )
    
    print("CrewAI Agent ready")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize()
    yield


app = FastAPI(title="Travel Assistant (CrewAI)", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "framework": "crewai",
        "tools": [t.name for t in mcp_tools]
    }


@app.post("/ask")
async def ask(query: TravelQuery):
    try:
        # Create a task for this query
        task = Task(
            description=f"Use your tools to answer: {query.query}",
            expected_output="The exact result from the tool that was called",
            agent=crew_agent,
        )
        
        # Create and run crew
        crew = Crew(
            agents=[crew_agent],
            tasks=[task],
            verbose=True,
        )
        
        result = await asyncio.wait_for(
            asyncio.to_thread(crew.kickoff),
            timeout=LLM_TIMEOUT
        )
        
        return {
            "query": query.query,
            "answer": str(result),
            "framework": "crewai"
        }
    
    except asyncio.TimeoutError:
        return {"error": "Request timed out", "query": query.query}
    except Exception as e:
        return {"error": str(e), "query": query.query}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

