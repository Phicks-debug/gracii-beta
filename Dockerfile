FROM python:3.10-slim

# Install Node.js and build essentials
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package files and install Node dependencies 
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Expose ports
EXPOSE 8000
EXPOSE 5173

VOLUME [".:/app", "/app/node_modules"]

ENV AWS_ACCESS_KEY_ID = ${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY = ${AWS_SECRET_ACCESS_KEY}
ENV AWS_DEFAULT_REGION = ${AWS_DEFAULT_REGION}

ENV GOOGLE_API_KEY=AIzaSyAc-V6nxMeFzNYHABDaPEQyQVShvaQ5tlo
ENV MAX_PARALLEL_PROCESSES=10

ENV CLIENT_ID = 9007134e-1403-4ce6-af0d-968728835d53
ENV REDIRECT_URI = http://localhost:8000/callback
ENV TOKEN_URL = https://login.microsoftonline.com/common/oauth2/v2.0/token
ENV AUTH_URL = https://login.microsoftonline.com/common/oauth2/v2.0/authorize
ENV SCOPES = https://graph.microsoft.com/Mail.Send offline_access

ENV GROQ_API_KEY = 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

ENV KNOWLEDGE_BASE_REGION = us-east-1
ENV HR_KNOWLEDEG_BASE_ID = 20GE0TB6RJ
ENV 365OFFICE_KNOWLEDEG_BASE_ID = OC9MWRVCVM

ENV MAIN_MODEL_REGION = us-east-1
ENV MAIN_MODEL_TEMP = 0.6
ENV MAIN_MODEL_TOP_P = 0.9
ENV MAIN_MODEL_TOP_K = 60
ENV MAIN_MODEL_MAXTK = 8196

ENV SUMMARY_MODEL_REGION = us-east-1
ENV SUMMARY_MODEL_TEMP = 0
ENV SUMMARY_MODEL_TOP_P = 0.9
ENV SUMMARY_MODEL_TOP_K = 40
ENV SUMMARY_MODEL_MAXTK = 2048


ENV DYNAMO_DB_TICKET_TABLE_REGION = us-east-1
ENV DYNAMO_DB_TICKET_TABLE_NAME = IT_Support_Tickets
ENV REACT_APP_API_BASE_URL = https://gracii.dev.kalliopedata.io

# The actual command will be overridden by docker-compose.yml
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

