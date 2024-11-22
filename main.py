import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Dict
from datetime import datetime, timedelta
import uvicorn
import logging
import tools
import httpx
import os

from bedrock_llm import Agent, ModelName, StopReason
from bedrock_llm.schema import MessageBlock
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tokens = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the agent when the server starts
    global agent
    agent = Agent(
        region_name="us-east-1",
        model_name=ModelName.CLAUDE_3_5_SONNET,
        auto_update_memory=False,
    ) 
    await agent._get_async_client()
    # Open the agent connection
    print("Agent initialized and opened")
    
    yield  # Server runs here
    
    # Cleanup when the server shuts down
    await agent.close()
    print("Agent closed")


app = FastAPI(title="LLM API Backend", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:5173", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for chat history (replace with database in production)
chat_history_store: Dict[str, List[MessageBlock]] = {}

# Add a helper function to manage chat history
async def manage_chat_history(conversation_id: str, message: MessageBlock) -> List[MessageBlock]:
    if conversation_id not in chat_history_store:
        chat_history_store[conversation_id] = []
    
    # Ensure proper message structure
    if not hasattr(message, 'role'):
        message.role = 'user'
    
    chat_history_store[conversation_id].append(message)
    
    # Optionally limit history length to prevent token limits
    max_history = 16  # Adjust as needed
    if len(chat_history_store[conversation_id]) > max_history:
        chat_history_store[conversation_id] = chat_history_store[conversation_id][-max_history-1:]
    
    return chat_history_store[conversation_id]


@app.get("/")
async def root():
    """Root endpoint to check if API is running"""
    return {"status": "API is running", "timestamp": datetime.now().isoformat()}


@app.post("/chat/{conversation_id}")
async def chat(conversation_id: str, request: MessageBlock):
    try:
        history = await manage_chat_history(conversation_id, request)

        async def generate():
            try:
                while True:
                    async for (token, 
                            stop_reason, 
                            response, 
                            tool_result
                    ) in agent.generate_and_action_async(
                        prompt=history,
                        system=f"You have realtime access. Current time is: {(datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')}",
                        tools=["get_stock_price",
                            "get_stock_intraday",
                            "search_stocks_by_groups",
                            "retrieve_hr_policy",
                            "retrieve_office365_document",
                            "web_suffing",
                            "send_email",
                            "raise_problems_to_IT"],
                    ):
                        if token:
                            yield token
                        if stop_reason == StopReason.END_TURN:
                            yield stop_reason.name
                            await manage_chat_history(conversation_id, response)
                            break
                        elif stop_reason == StopReason.TOOL_USE:
                            yield stop_reason.name
                            await manage_chat_history(conversation_id, response)
                        if tool_result:
                            message = MessageBlock(role='user', content=tool_result)
                            await manage_chat_history(conversation_id, message)
                            yield "DONE"
                    if stop_reason == StopReason.END_TURN:
                        break

            except Exception as e:
                logger.error(f"Streaming error: {str(e)}")
                yield f"Error: {str(e)}\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )

    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/{conversation_id}")
async def get_chat_history(conversation_id: str):
    """Get chat history for a specific conversation"""
    if conversation_id not in chat_history_store:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return chat_history_store[conversation_id]


@app.delete("/chat/{conversation_id}")
async def delete_chat(conversation_id: str):
    """Delete a specific chat conversation"""
    if conversation_id not in chat_history_store:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del chat_history_store[conversation_id]
    return {"status": "deleted", "conversation_id": conversation_id}


@app.get("/send-email-tool/authentication")
async def login():
    """Redirects user to Microsoft login."""
    return RedirectResponse(
        f"{os.environ.get('AUTH_URL')}?client_id={os.environ.get('CLIENT_ID')}&response_type=code&redirect_uri={os.environ.get('REDIRECT_URI')}&scope={os.environ.get('SCOPES')}"
    )


@app.get("/send-email-tool/authentication/callback")
async def callback(code: str):
    """Handles OAuth2 callback and exchanges the authorization code for an access token."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            os.environ.get("TOKEN_URL"),
            data={
                "client_id": os.environ.get("CLIENT_ID"),
                "redirect_uri": os.environ.get("REDIRECT_URI"),
                "code": code,
                "grant_type": "authorization_code",
            },
        ) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=response.status, detail=await response.text()
                )
            token_data = await response.json()
            tokens["access_token"] = token_data["access_token"]
            tokens["refresh_token"] = token_data.get("refresh_token")
            return {"message": "Authentication successful", "access_token": tokens["access_token"]}


@app.post("/send-email-tool/send")
async def send_email(
    to_email: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    attachment_path: str = Form(None),
):
    """Sends an email with optional attachment using Microsoft Graph."""
    if "access_token" not in tokens:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")

    message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body,
            },
            "toRecipients": [{"emailAddress": {"address": to_email}}],
            "attachments": [],
        }
    }

    # Add attachment if provided
    if attachment_path:
        try:
            filename = os.path.basename(attachment_path)
            async with aiofiles.open(attachment_path, "rb") as file:
                file_content = await file.read()
            message["message"]["attachments"].append(
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": filename,
                    "contentBytes": file_content.decode("latin1"),
                }
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading attachment: {e}")

    # Send email using Microsoft Graph API
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            json=message,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        ) as response:
            if response.status != 202:
                raise HTTPException(
                    status_code=response.status, detail=await response.text()
                )
            return {"message": "Email sent successfully"}


@app.get("/chat-history")
async def get_all_chat_history_endpoint():
    """Endpoint to get chat history for all conversations"""
    return chat_history_store


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
