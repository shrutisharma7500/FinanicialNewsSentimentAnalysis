from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
import asyncio
from tavilyAgent import agent, WebSearchRequest, WebSearchResponse

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

class SearchResult(BaseModel):
    title: str
    url: str
    content: str

class QueryResponse(BaseModel):
    query: str
    results: list[SearchResult]

async def run_agent_query(query: str) -> QueryResponse:
    # Create a response queue
    response_queue = asyncio.Queue()
    
    # Register a temporary message handler
    @agent.on_message(WebSearchResponse)
    async def temp_handler(ctx, sender, msg):
        await response_queue.put(msg)
        agent._remove_message_handler(temp_handler)
    
    # Send the query
    await agent.send(agent.AI_AGENT_ADDRESS, WebSearchRequest(query=query))
    
    # Wait for response
    response = await response_queue.get()
    
    # Convert to our response model
    return QueryResponse(
        query=response.query,
        results=[SearchResult(**result.dict()) for result in response.results]
    )

@app.post("/search", response_model=QueryResponse)
async def search(request: QueryRequest):
    """
    Perform a web search using the Tavily agent.
    """
    return await run_agent_query(request.query)

@app.on_event("startup")
async def startup_event():
    # Start the agent in the background
    asyncio.create_task(agent.run())