from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uagents import Agent, Context, Model
import asyncio
from fastapi.middleware.cors import CORSMiddleware

# Model definitions
class FinancialNewsSentimentRequest(Model):
    ticker: str

class NewsSentiment(Model):
    title: str
    url: str
    summary: str
    overall_sentiment_label: str

class FinancialNewsSentimentResponse(Model):
    summary: List[NewsSentiment]

# FastAPI models
class APIFinancialNewsRequest(BaseModel):
    ticker: str

class APINewsSentiment(BaseModel):
    title: str
    url: str
    summary: str
    overall_sentiment_label: str

class APIFinancialNewsResponse(BaseModel):
    summary: List[APINewsSentiment]
    status: str = "success"

# Initialize FastAPI
app = FastAPI(title="Financial News Sentiment API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a minimal agent that won't start a server
agent = Agent(
    name="newsagent",
    seed="testing",
    port=None,  # Explicitly disable HTTP server
    endpoint=["http://localhost:8000/agent"]  # Use FastAPI endpoint
)

AI_AGENT_ADDRESS = "agent1qdcnxjrr5u5jkqqtcaeqdxxpxne47nvcrm4k3krsprwwgnx50hg96txxjuf"
response_store = {}

@agent.on_message(FinancialNewsSentimentResponse)
async def handle_response(ctx: Context, sender: str, msg: FinancialNewsSentimentResponse):
    response_store[ctx.message.reply_to] = msg

@app.post("/agent")
async def agent_endpoint(request: dict):
    """Endpoint for agent communication"""
    return {"status": "received"}

@app.post("/get-sentiment", response_model=APIFinancialNewsResponse)
async def get_sentiment(request: APIFinancialNewsRequest):
    try:
        request_id = str(hash(f"{request.ticker}{asyncio.get_event_loop().time()}"))
        
        await agent._ctx.send(
            AI_AGENT_ADDRESS,
            FinancialNewsSentimentRequest(ticker=request.ticker),
            reply_to=request_id
        )
        
        max_retries = 10
        for _ in range(max_retries):
            if request_id in response_store:
                response = response_store.pop(request_id)
                return {
                    "summary": [
                        {
                            "title": item.title,
                            "url": item.url,
                            "summary": item.summary,
                            "overall_sentiment_label": item.overall_sentiment_label
                        } for item in response.summary
                    ]
                }
            await asyncio.sleep(1)
        
        raise HTTPException(status_code=504, detail="Agent response timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    async def initialize_agent():
        try:
            # Initialize agent components without starting server
            await agent._database.connect()
            await agent._message_queue.start()
            print("Agent initialized successfully")
        except Exception as e:
            print(f"Agent initialization error: {e}")

    asyncio.create_task(initialize_agent())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, lifespan="on")