
import aiohttp
import aiofiles
from asyncio import Event, create_task, gather
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uvicorn
import logging
import tools
import os

from utils import render_template
from bedrock_llm import Agent, ModelName, StopReason, ModelConfig
from bedrock_llm.schema import MessageBlock
from groq import AsyncGroq
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tokens = {}
main_region = os.environ.get("MAIN_MODEL_REGION")
main_temp = os.environ.get("MAIN_MODEL_TEMP")
main_topk = os.environ.get("MAIN_MODEL_TOP_K")
main_topp = os.environ.get("MAIN_MODEL_TOP_P")
main_mxtk = os.environ.get("MAIN_MODEL_MAXTK")
groq_api_key = os.environ.get("GROQ_API_KEY")

main_config = ModelConfig(
    temperature=float(main_temp),
    top_k=main_topk,
    top_p=float(main_topp),
    max_tokens=main_mxtk,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the agent when the server starts
    global agent
    agent = Agent(
        region_name=main_region,
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


async def delete_chat_history(conversation_id: str, position: Optional[int]=None):
    if conversation_id in chat_history_store and not position:
        chat_history_store[conversation_id].clear()
    else:
        chat_history_store[conversation_id].pop(position)


@app.get("/")
async def root():
    """Root endpoint to check if API is running"""
    return {"status": "API is running", "timestamp": (datetime.now() + timedelta(hours=7)).isoformat()}


@app.post("/chat/{conversation_id}")
async def chat(conversation_id: str, request: MessageBlock):
    try:
        history = await manage_chat_history(conversation_id, request)

        stop_event = Event()

        async def validate_and_control():
            async with AsyncGroq(
                api_key=groq_api_key,
            ) as guard_model:
                completion = await guard_model.chat.completions.create(
                    model="llama-3.2-11b-text-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": render_template("guardrail.j2", {
                                "input": request.content,
                            })
                        }
                    ],
                    temperature=0,
                    max_tokens=1024,
                    top_p=1,
                    stream=False,
                    stop=None,
                )
            if completion.choices[0].message.content.strip() == "NOT OK":
                stop_event.set()
                await delete_chat_history(conversation_id, -1)
                logger.info(history)
                return False, "Your input contain potential harmful content or violated our policy, and has been blocked for safety reasons."
            return True, None

        async def generate():
            try:
                while True:
                    async for (token, 
                            stop_reason, 
                            response, 
                            tool_result
                    ) in agent.generate_and_action_async(
                        prompt=history,
                        system=render_template("main.j2", {
                            "current_date": (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
                        }),
                        tools=["get_stock_price",
                            "get_stock_intraday",
                            "search_stocks_by_groups",
                            "retrieve_hr_policy",
                            "retrieve_office365_document",
                            "web_suffing",
                            "send_email",
                            "raise_problems_to_IT"],
                        config=main_config,
                    ):
                        # Check for any stop from guardrail
                        if stop_event.is_set():
                            return

                        if token:
                            yield token
                        if stop_reason == StopReason.END_TURN:
                            yield stop_reason.name
                            await manage_chat_history(conversation_id, response)
                            logger.info(f"Response: {response}")
                            break
                        elif stop_reason == StopReason.TOOL_USE:
                            yield stop_reason.name
                            await manage_chat_history(conversation_id, response)
                            logger.info(f"Response: {response}")
                        if tool_result:
                            message = MessageBlock(role='user', content=tool_result)
                            await manage_chat_history(conversation_id, message)
                            logger.info(f"Tool result: {tool_result}")
                            yield "DONE"
                    if stop_reason == StopReason.END_TURN:
                        break

            except Exception as e:
                logger.error(f"Streaming error: {str(e)}")
                yield f"Error: {str(e)}\n"

        async def invoke_model():
            is_safe, error_message = await validate_and_control()
            if not is_safe:
                yield "INVALID_INPUT"
                yield error_message
                return

            async for token in generate():
                yield token

        return StreamingResponse(
            invoke_model(),
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
