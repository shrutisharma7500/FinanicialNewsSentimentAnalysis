from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from tavily_agent import agent, WebSearchRequest, WebSearchResponse

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

async def run_agent_query(query: str):
    response_queue = asyncio.Queue()
    
    @agent.on_message(WebSearchResponse)
    async def temp_handler(ctx, sender, msg):
        await response_queue.put(msg)
        agent._remove_message_handler(temp_handler)
    
    await agent.send(agent.AI_AGENT_ADDRESS, WebSearchRequest(query=query))
    response = await response_queue.get()
    
    return QueryResponse(
        query=response.query,
        results=[SearchResult(**result.dict()) for result in response.results]
    )

@app.post("/search")
async def search(request: QueryRequest):
    return await run_agent_query(request.query)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(agent.run())