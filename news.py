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
agent = Agent()
AI_AGENT_ADDRESS = "agent1qdcnxjrr5u5jkqqtcaeqdxxpxne47nvcrm4k3krsprwwgnx50hg96txxjuf"

# Store for responses
response_store = {}

@agent.on_message(FinancialNewsSentimentResponse)
async def handle_response(ctx: Context, sender: str, msg: FinancialNewsSentimentResponse):
    ctx.logger.info(f"Received response from {sender}:")
    ctx.logger.info(msg.summary)
    response_store[ctx.message.reply_to] = msg

# FastAPI Endpoints
@app.post("/get-sentiment", response_model=APIFinancialNewsResponse)
async def get_sentiment(request: APIFinancialNewsRequest):
    """
    Get financial news sentiment for a given ticker
    
    Parameters:
    - ticker: Stock ticker symbol (e.g., AAPL, MSFT)
    
    Returns:
    - List of news articles with sentiment analysis
    """
    try:
        # Create a unique ID for this request
        request_id = str(hash(f"{request.ticker}{asyncio.get_event_loop().time()}"))
        
        # Send the request to the agent
        await agent._ctx.send(
            AI_AGENT_ADDRESS,
            FinancialNewsSentimentRequest(ticker=request.ticker),
            reply_to=request_id
        )
        
        # Wait for response (with timeout)
        max_retries = 10
        retry_count = 0
        while request_id not in response_store and retry_count < max_retries:
            await asyncio.sleep(1)
            retry_count += 1
        
        if request_id not in response_store:
            raise HTTPException(status_code=504, detail="Agent response timeout")
        
        # Get and format the response
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Run the agent in the background
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(agent.run())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)