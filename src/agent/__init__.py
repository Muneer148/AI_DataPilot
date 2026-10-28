"""AI_DataPilot's deterministic, evidence-grounded agent MVP.

This module deliberately uses no LLM by default: supported questions are routed
to allow-listed analytics functions and unsupported/ambiguous requests abstain.
"""
from .orchestrator import ask, AgentResponse
from .planner import plan_question, AnalysisPlan

__all__ = ["ask", "AgentResponse", "plan_question", "AnalysisPlan"]
