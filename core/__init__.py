# core/__init__.py
# Import core modules for LDLE framework

from .LLM import LLM
from .manager import Manager
from .parallel_detector import ParallelDetector, start_detector_process
from .Universal_LLM_Client import UniversalLLMClient

__all__ = ['LLM', 'Manager', 'ParallelDetector', 'start_detector_process', 'UniversalLLMClient']
