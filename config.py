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

# Get OpenAI API Key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Default LLM model
MODEL_NAME = "gpt-4o"

# System prompt for AI Agent identity (if needed)
SYSTEM_PROMPT = "You are an AI programmer. Your job is to complete tasks assigned by your project manager and provide a text-based report. You must only return the report, without any preamble or extra conversation." 