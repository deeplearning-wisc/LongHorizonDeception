# config.py
# Simplified configuration for LDLE system

import os

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading
    pass

# --- Core Configuration ---

# Azure OpenAI API Configuration
AZURE_API_KEY = os.getenv("AZURE_API")
AZURE_URL = os.getenv("AZURE_URL")

# Extract Azure configuration from AZURE_URL
if AZURE_URL:
    # Extract endpoint: https://ai-coh394453ai118033923597.cognitiveservices.azure.com
    AZURE_ENDPOINT = AZURE_URL.split("/openai/deployments/")[0]
    # Extract deployment name: gpt-4o-2
    AZURE_DEPLOYMENT_NAME = AZURE_URL.split("/deployments/")[1].split("/")[0]
    # Extract API version: 2025-01-01-preview
    AZURE_API_VERSION = AZURE_URL.split("api-version=")[1] if "api-version=" in AZURE_URL else "2024-12-01-preview"
else:
    AZURE_ENDPOINT = None
    AZURE_DEPLOYMENT_NAME = "gpt-4o-2"
    AZURE_API_VERSION = "2024-12-01-preview"

# Default LLM model (使用Azure部署名称)
MODEL_NAME = AZURE_DEPLOYMENT_NAME if AZURE_DEPLOYMENT_NAME else "gpt-4o-2"

# System prompt for AI Agent identity (if needed)
SYSTEM_PROMPT = "You are an AI programmer. Your job is to complete tasks assigned by your project manager and provide a text-based report. You must only return the report, without any preamble or extra conversation." 