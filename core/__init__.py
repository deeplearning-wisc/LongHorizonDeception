# core/__init__.py
# Import core modules for LDLE framework

from .LLM import LLM
from .manager import Manager
from .detector import DeceptionDetector
from .Universal_LLM_Client import UniversalLLMClient

__all__ = ['LLM', 'Manager', 'DeceptionDetector', 'UniversalLLMClient']
