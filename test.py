import aiohttp
import secrets
import asyncio
import aiofiles
import logging
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import quote
import uvicorn
import httpx
import os

# Application details from Microsoft Azure App Registration
CLIENT_ID = "9007134e-1403-4ce6-af0d-968728835d53"
REDIRECT_URI = "http://localhost:5000/callback"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
SCOPES = "https://graph.microsoft.com/Mail.Send offline_access"

# In-memory storage for access tokens (use a database for production)
tokens = {}

logger = logging.getLogger(__name__)

app = FastAPI()

async def send_email(recipient: str, subject: str, body: str, attachment_path: list[str] = []):
    try:
        async with aiohttp.ClientSession() as session:
            # Check if we have valid tokens
            if not tokens.get("access_token"):

                state = secrets.token_urlsafe(16)
                
                # Store the email details for after authentication
                app.state.pending_emails = getattr(app.state, 'pending_emails', {})
                app.state.pending_emails[state] = {
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                    "attachment_path": attachment_path
                }

                auth_url = (f"{AUTH_URL}"
                           f"?client_id={CLIENT_ID}"
                           f"&response_type=code"
                           f"&redirect_uri={quote(REDIRECT_URI)}"
                           f"&scope={quote(SCOPES)}"
                           f"&response_mode=query"
                           f"&state={state}")
            
                # Return special response that frontend will recognize
                return {
                    "status": "authentication_required",
                    "auth_url": auth_url,
                    "message": "Please authenticate in the opened window. The email will be sent automatically after authentication."
                }

            # If we have a token, proceed with sending email
            return await send_email_with_token(recipient, subject, body, attachment_path, tokens["access_token"])

    except Exception as e:
        return f"Unexpected error: {str(e)}"

async def send_email_with_token(recipient: str, subject: str, body: str, attachment_path: list[str], access_token: str):
    """Helper function to send email once we have a valid token"""
    async with aiohttp.ClientSession() as session:
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body,
                },
                "toRecipients": [{"emailAddress": {"address": recipient}}],
                "attachments": []
            }
        }

        # Handle attachments if provided
        if attachment_path and len(attachment_path) > 0:
            try:
                async with aiofiles.open(attachment_path[0], "rb") as file:
                    file_content = await file.read()
                    message["message"]["attachments"].append({
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": os.path.basename(attachment_path[0]),
                        "contentBytes": file_content.decode("latin1")
                    })
            except Exception as e:
                return f"Error processing attachment: {str(e)}"

        # Send email using Microsoft Graph API
        async with session.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            json=message,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        ) as response:
            if response.status != 202:
                error_text = await response.text()
                if response.status == 401:
                    return {
                        "status": "authentication_required",
                        "message": "Session expired. Please re-authenticate."
                    }
                return f"Failed to send email: {error_text}"
            
            return {
                "status": "success",
                "message": f"Email sent successfully to {recipient}"
            }

# Modify your callback endpoint in main.py:
@app.get("/callback")
async def callback(code: str, state: str = None):
    """Handles OAuth2 callback and exchanges the authorization code for an access token."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                TOKEN_URL,
                data={
                    "client_id": CLIENT_ID,
                    "redirect_uri": REDIRECT_URI,
                    "code": code,
                    "grant_type": "authorization_code",
                    "scope": SCOPES
                },
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status, detail=await response.text()
                    )
                token_data = await response.json()
                tokens["access_token"] = token_data["access_token"]
                tokens["refresh_token"] = token_data.get("refresh_token")

                # If there's a pending email, send it
                pending_emails = getattr(app.state, 'pending_emails', {})
                if state and state in pending_emails:
                    email_data = pending_emails[state]
                    
                    # Send the email
                    result = await send_email_with_token(
                        email_data["recipient"],
                        email_data["subject"],
                        email_data["body"],
                        email_data["attachment_path"],
                        tokens["access_token"]
                    )

                    # Clean up
                    del pending_emails[state]

                    # Return success page that will auto-close
                    return HTMLResponse(content="""
                        <html>
                            <body>
                                <h2>Authentication successful!</h2>
                                <p>Email has been sent. This window will close automatically.</p>
                                <script>
                                    setTimeout(function() {
                                        window.close();
                                    }, 2000);
                                </script>
                            </body>
                        </html>
                    """)

                return {"message": "Authentication successful", "access_token": tokens["access_token"]}
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this route to serve the HTML form
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>Email Sender</title>
        </head>
        <body>
            <h1>Send Email</h1>
            <form action="/send" method="post">
                <p>
                    <label>Recipient:</label><br>
                    <input type="email" name="recipient" required>
                </p>
                <p>
                    <label>Subject:</label><br>
                    <input type="text" name="subject" required>
                </p>
                <p>
                    <label>Body:</label><br>
                    <textarea name="body" required></textarea>
                </p>
                <button type="submit">Send Email</button>
            </form>
        </body>
    </html>
    """

# Add this route to handle the form submission
@app.post("/send")
async def handle_send(
    recipient: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...)
):
    result = await send_email(recipient, subject, body)
    if isinstance(result, dict) and result.get("status") == "authentication_required":
        return HTMLResponse(content=f"""
            <html>
                <body>
                    <h2>Authentication Required</h2>
                    <p>{result['message']}</p>
                    <script>
                        window.addEventListener('message', function(event) {{
                            if (event.data === 'email_sent') {{
                                window.location.href = '/?success=true';
                            }}
                        }});
                        window.open('{result['auth_url']}', '_blank', 'width=600,height=600');
                    </script>
                </body>
            </html>
        """)
    return HTMLResponse(content=f"""
        <html>
            <body>
                <h2>Result</h2>
                <p>{str(result)}</p>
                <p><a href="/">Back to Form</a></p>
            </body>
        </html>
    """)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
