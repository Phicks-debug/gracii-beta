import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import os

# Application details from Microsoft Azure App Registration
CLIENT_ID = "9007134e-1403-4ce6-af0d-968728835d53"
REDIRECT_URI = "http://localhost:8000/callback"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
SCOPES = "https://graph.microsoft.com/Mail.Send offline_access"

app = FastAPI()

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for access tokens (use a database for production)
tokens = {}

@app.get("/")
async def login():
    """Redirects user to Microsoft login."""
    return RedirectResponse(
        f"{AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPES}"
    )

@app.get("/callback")
async def callback(code: str):
    """Handles OAuth2 callback and exchanges the authorization code for an access token."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
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

@app.post("/send-email")
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
