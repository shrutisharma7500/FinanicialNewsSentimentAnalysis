from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uagents import Agent, Context, Model
import asyncio
from fastapi.middleware.cors import CORSMiddleware

# Original Agent Code
class FinancialNewsSentimentRequest(Model):
    ticker: str

class NewsSentiment(Model):
    title: str
    url: str
    summary: str
    overall_sentiment_label: str

class FinancialNewsSentimentResponse(Model):
    summary: List[NewsSentiment]

# FastAPI Models
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

# Initialize FastAPI app
app = FastAPI(title="Financial News Sentiment API",
              description="API wrapper for Financial News Sentiment Agent")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent setup - Disable HTTP server and use FastAPI's endpoint
agent = Agent(
    name="newsagent",
    seed="testing",
    port=None,  # Disable agent's HTTP server
    endpoint=["http://localhost:8000/submit"],  # Use FastAPI endpoint
    use_mailbox=False
)

AI_AGENT_ADDRESS = "agent1qdcnxjrr5u5jkqqtcaeqdxxpxne47nvcrm4k3krsprwwgnx50hg96txxjuf"
response_store = {}

# Agent handlers
@agent.on_event("startup")
async def agent_startup(ctx: Context):
    ctx.logger.info("Agent started")

@agent.on_message(FinancialNewsSentimentResponse)
async def handle_response(ctx: Context, sender: str, msg: FinancialNewsSentimentResponse):
    ctx.logger.info(f"Received response from {sender}")
    response_store[ctx.message.reply_to] = msg

# FastAPI endpoints
@app.post("/submit")
async def agent_submit(request: dict):
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

# Proper agent initialization
@app.on_event("startup")
async def startup_event():
    async def run_agent():
        try:
            # Correct way to run the agent without starting HTTP server
            await agent.run_async()
        except Exception as e:
            print(f"Agent initialization error: {e}")

    asyncio.create_task(run_agent())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, lifespan="on")