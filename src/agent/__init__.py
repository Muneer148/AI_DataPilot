"""AI_DataPilot's evidence-grounded agent MVP.

The default planner uses deterministic phrase matching. Local Ollama planning is
an explicit opt-in and its proposed plan is validated before tool execution.
"""
from .orchestrator import ask, AgentResponse
from .planner import plan_question, AnalysisPlan
from .ollama_provider import OllamaProviderError, plan_question_with_ollama

__all__ = [
    "ask", "AgentResponse", "plan_question", "AnalysisPlan",
    "OllamaProviderError", "plan_question_with_ollama",
]
