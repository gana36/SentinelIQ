"""
LangSmith observability for the SentinelIQ agentic pipeline.

Traces three levels:
  1. signal_run      — parent span for one full signal → alert lifecycle
  2. nova_llm_call   — child span for every Nova Lite Converse API call
  3. tool_call       — child span for every tool Nova invokes

Usage (in orchestrator.py):
    tracer = SignalTracer(signal)
    with tracer:
        # ... agentic loop ...
        tracer.record_llm(messages, response)
        tracer.record_tool(tool_name, tool_input, result)
        tracer.record_outcome(action_card or None)
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.utils.logger import logger

# Set env vars LangSmith SDK reads automatically
if settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
if settings.langchain_tracing_v2:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)

_tracing_enabled = bool(settings.langchain_api_key and settings.langchain_tracing_v2)


class SignalTracer:
    """
    Context manager that creates a LangSmith RunTree for one signal.

    Wraps the entire process() call as a "chain" run, then records
    each Nova LLM call and each tool execution as children.
    """

    def __init__(self, signal):
        self._signal = signal
        self._run = None
        self._round_runs: list = []  # one per Nova Converse round

    # ── Context manager interface ─────────────────────────────────────

    def __enter__(self):
        if not _tracing_enabled:
            return self
        try:
            from langsmith.run_trees import RunTree
            self._run = RunTree(
                name="sentineliq.process_signal",
                run_type="chain",
                inputs={
                    "signal_id": self._signal.signal_id,
                    "ticker": self._signal.ticker,
                    "source": self._signal.source,
                    "text": self._signal.raw_text[:300],
                    "metadata": self._signal.metadata,
                },
                tags=[self._signal.source, self._signal.ticker or "unknown"],
                project_name=settings.langchain_project,
            )
            self._run.post()
        except Exception as e:
            logger.warning("langsmith_init_failed", error=str(e))
            self._run = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._run is None:
            return
        try:
            if exc_type:
                self._run.end(error=str(exc_val))
            self._run.patch()  # flushes final state
        except Exception as e:
            logger.warning("langsmith_close_failed", error=str(e))

    # ── Recording helpers ─────────────────────────────────────────────

    def record_llm(self, round_num: int, messages: list[dict], response: dict) -> None:
        """Record one Nova Lite Converse API call as a child LLM span."""
        if self._run is None:
            return
        try:
            # Extract text output and token usage
            output_content = response.get("output", {}).get("message", {}).get("content", [])
            output_text = " ".join(
                block.get("text", "") for block in output_content if "text" in block
            )
            tool_uses = [
                {"tool": b["name"], "input": b.get("input")}
                for b in output_content if b.get("type") == "toolUse"
            ]
            usage = response.get("usage", {})

            child = self._run.create_child(
                name=f"nova_lite.converse (round {round_num})",
                run_type="llm",
                inputs={
                    "messages": _truncate_messages(messages),
                    "model": settings.bedrock_nova_lite_model_id,
                },
            )
            child.end(outputs={
                "text": output_text,
                "tool_calls": tool_uses,
                "stop_reason": response.get("stopReason"),
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
            })
            child.post()
            self._round_runs.append(child)
        except Exception as e:
            logger.warning("langsmith_record_llm_failed", error=str(e))

    def record_tool(self, tool_name: str, tool_input: dict, result: Any, error: str | None = None) -> None:
        """Record one tool execution as a child tool span."""
        if self._run is None:
            return
        try:
            child = self._run.create_child(
                name=f"tool.{tool_name}",
                run_type="tool",
                inputs=tool_input,
            )
            if error:
                child.end(error=error)
            else:
                child.end(outputs={"result": result})
            child.post()
        except Exception as e:
            logger.warning("langsmith_record_tool_failed", error=str(e))

    def record_outcome(self, action_card, dropped_reason: str | None = None) -> None:
        """Record the final outcome of this signal — alert composed or dropped."""
        if self._run is None:
            return
        try:
            if action_card:
                self._run.end(outputs={
                    "outcome": "alert_dispatched",
                    "alert_id": action_card.alert_id,
                    "ticker": action_card.ticker,
                    "credibility_score": action_card.credibility_score,
                    "confidence_level": action_card.nova_analysis.get("confidence_level"),
                    "target_user_count": len(action_card.target_users),
                    "similar_events_found": len(action_card.similar_events),
                })
            else:
                self._run.end(outputs={
                    "outcome": "dropped",
                    "reason": dropped_reason or "signal_not_anomalous_or_no_users",
                })
            self._run.patch()
        except Exception as e:
            logger.warning("langsmith_record_outcome_failed", error=str(e))

    # ── Mock-mode tracing (records without sending to LangSmith) ──────

    def record_mock_tool(self, tool_name: str, tool_input: dict, result: Any) -> None:
        """Same as record_tool — works whether tracing is on or off."""
        self.record_tool(tool_name, tool_input, result)


def _truncate_messages(messages: list[dict], max_chars: int = 500) -> list[dict]:
    """Truncate message content for LangSmith payload size limits."""
    truncated = []
    for msg in messages:
        content = msg.get("content", [])
        short_content = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text = block["text"]
                short_content.append({"text": text[:max_chars] + ("..." if len(text) > max_chars else "")})
            else:
                short_content.append(block)
        truncated.append({"role": msg.get("role"), "content": short_content})
    return truncated


def is_tracing_enabled() -> bool:
    return _tracing_enabled
