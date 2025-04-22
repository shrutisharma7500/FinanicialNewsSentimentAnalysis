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

# Agent setup
agent = Agent(name="newsagent" ,seed="testing", port=8000, endpoint=["http://localhost:8000/submit"])

AI_AGENT_ADDRESS = "agent1qdcnxjrr5u5jkqqtcaeqdxxpxne47nvcrm4k3krsprwwgnx50hg96txxjuf"

response_store = {}

@agent.on_message(FinancialNewsSentimentResponse)
async def handle_response(ctx: Context, sender: str, msg: FinancialNewsSentimentResponse):
    response_store[ctx.message.reply_to] = msg

@app.post("/submit")
async def agent_submit(request: dict):
    """Endpoint for agent communication"""
    # Process agent messages here if needed
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

@app.on_event("startup")
async def startup_event():
    # Start agent without HTTP server
    async def run_agent():
        try:
            await agent.start()
        except Exception as e:
            print(f"Agent startup error: {e}")

    asyncio.create_task(run_agent())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, lifespan="on")