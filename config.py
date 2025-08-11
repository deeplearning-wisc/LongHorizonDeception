# config.py
# Strict configuration for LDLE system - NO FALLBACKS

import os
from pathlib import Path

# 加载 .env 文件
def _load_dotenv():
    """手动加载 .env 文件"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")  # 移除引号
                    if key and value:
                        os.environ[key] = value

# 立即加载环境变量
_load_dotenv()

def _strict_getenv(key: str) -> str:
    """严格获取环境变量，不存在则抛异常"""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' not found")
    if not value.strip():
        raise ValueError(f"Environment variable '{key}' is empty")
    return value.strip()

def _parse_azure_url(azure_url: str) -> tuple:
    """
    严格解析Azure URL，格式错误则抛异常
    
    Expected format: https://endpoint/openai/deployments/deployment-name/...?api-version=version
    
    Returns:
        tuple: (endpoint, deployment_name, api_version)
    """
    if "/openai/deployments/" not in azure_url:
        raise ValueError(f"Invalid AZURE_URL format: missing '/openai/deployments/' in {azure_url}")
    
    # Extract endpoint
    try:
        endpoint = azure_url.split("/openai/deployments/")[0]
        if not endpoint.startswith("https://"):
            raise ValueError(f"Invalid endpoint format in AZURE_URL: {endpoint}")
    except IndexError:
        raise ValueError(f"Failed to extract endpoint from AZURE_URL: {azure_url}")
    
    # Extract deployment name
    try:
        deployment_part = azure_url.split("/deployments/")[1]
        deployment_name = deployment_part.split("/")[0]
        if not deployment_name:
            raise ValueError(f"Empty deployment name in AZURE_URL: {azure_url}")
    except IndexError:
        raise ValueError(f"Failed to extract deployment name from AZURE_URL: {azure_url}")
    
    # Extract API version
    if "api-version=" not in azure_url:
        raise ValueError(f"Missing api-version parameter in AZURE_URL: {azure_url}")
    
    try:
        api_version = azure_url.split("api-version=")[1]
        # Remove any trailing parameters
        api_version = api_version.split("&")[0]
        if not api_version:
            raise ValueError(f"Empty api-version in AZURE_URL: {azure_url}")
    except IndexError:
        raise ValueError(f"Failed to extract api-version from AZURE_URL: {azure_url}")
    
    return endpoint, deployment_name, api_version

# --- Strict Configuration Loading ---

# Step 1: 严格加载必需的环境变量
AZURE_API_KEY = _strict_getenv("AZURE_API")
AZURE_URL = _strict_getenv("AZURE_URL")

# Step 2: 严格解析Azure配置
AZURE_ENDPOINT, AZURE_DEPLOYMENT_NAME, AZURE_API_VERSION = _parse_azure_url(AZURE_URL)

# Step 3: 确定模型名称（使用Azure部署名称）
MODEL_NAME = AZURE_DEPLOYMENT_NAME

# Validation: 确保所有关键配置都不为空
if not AZURE_API_KEY:
    raise ValueError("AZURE_API_KEY cannot be empty")
if not AZURE_ENDPOINT:
    raise ValueError("AZURE_ENDPOINT cannot be empty")
if not AZURE_DEPLOYMENT_NAME:
    raise ValueError("AZURE_DEPLOYMENT_NAME cannot be empty")
if not AZURE_API_VERSION:
    raise ValueError("AZURE_API_VERSION cannot be empty") 