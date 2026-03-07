"""
True agentic orchestrator.

Instead of a hardcoded pipeline (step1 → step2 → step3 ...),
Nova Lite itself decides which tools to call and in what order
based on the signal content. This is the "agentic" part.

Flow:
  1. We describe all available tools to Nova
  2. Nova returns a list of tool calls it wants to make
  3. We execute those tools and feed results back to Nova
  4. Nova decides if it needs more tools or is ready to compose the alert
  5. Repeat until Nova says "done"
"""

import json
import asyncio
from typing import Any

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger
from app.utils.ticker_resolver import resolve_ticker

# ── Tool definitions (sent to Nova so it knows what it can call) ──────────────

TOOLS = [
    {
        "toolSpec": {
            "name": "run_sentiment",
            "description": "Classify the sentiment of the signal text as positive, negative, or neutral with a confidence score.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The text to classify"}
                    },
                    "required": ["text"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "run_anomaly_detection",
            "description": "Score how anomalous the signal is using volume, price change, and sentiment intensity.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "volume_zscore": {"type": "number"},
                        "price_change_pct": {"type": "number"},
                        "sentiment_intensity": {"type": "number"},
                        "has_breaking_keywords": {"type": "boolean"}
                    },
                    "required": ["volume_zscore", "price_change_pct", "sentiment_intensity", "has_breaking_keywords"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "check_credibility",
            "description": "Score how credible and reliable the signal source is (0.0 to 1.0).",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source name: reddit, news, market, sec, mock"},
                        "url": {"type": "string", "description": "Article/post URL if available"}
                    },
                    "required": ["source"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "find_similar_historical_events",
            "description": "Search for similar past market events to provide historical context.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Signal text to find similar events for"},
                        "k": {"type": "integer", "description": "Number of similar events to return", "default": 3}
                    },
                    "required": ["text"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_target_users",
            "description": "Find users who have this ticker in their watchlist and should receive this alert.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "confidence_level": {"type": "number", "description": "Alert confidence 0-1, used to filter by user sensitivity"}
                    },
                    "required": ["ticker", "confidence_level"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "compose_alert",
            "description": "Compose and dispatch the final alert to target users. Call this last when you have all the information you need.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "event_summary": {"type": "string"},
                        "primary_driver": {"type": "string"},
                        "sector_impact": {"type": "string"},
                        "confidence_level": {"type": "number"},
                        "risk_factors": {"type": "array", "items": {"type": "string"}},
                        "time_horizon": {"type": "string", "enum": ["intraday", "short-term", "long-term"]},
                        "recommended_actions": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["ticker", "event_summary", "confidence_level"]
                }
            }
        }
    }
]

SYSTEM_PROMPT = """You are an autonomous market intelligence agent.

When given a market signal, you must:
1. Use the available tools to gather evidence before making any judgement
2. Always run sentiment analysis and anomaly detection first
3. Check source credibility
4. Find similar historical events for context
5. Only call compose_alert when you have enough evidence to make a confident assessment
6. If the signal is not anomalous or credible enough (credibility < 0.3 or not anomalous), do NOT call compose_alert — just stop

Be selective. Most signals are noise. Only escalate genuine anomalies."""


# ── Tool executor — maps tool names to actual implementations ─────────────────

async def _execute_tool(tool_name: str, tool_input: dict, signal: RawSignal, state: dict) -> Any:
    if tool_name == "run_sentiment":
        if settings.mock_mode:
            from app.ml.sentiment.mock_sentiment import mock_analyze
            result = mock_analyze(tool_input["text"])
        else:
            from app.ml.sentiment.finbert_classifier import get_finbert
            result = await get_finbert().analyze(tool_input["text"])
        state["sentiment"] = result
        return result

    elif tool_name == "run_anomaly_detection":
        features = [
            tool_input.get("volume_zscore", 0.0),
            tool_input.get("price_change_pct", 0.0),
            tool_input.get("sentiment_intensity", 0.0),
            1.0 if tool_input.get("has_breaking_keywords") else 0.0,
            0.5,  # novelty
        ]
        if settings.mock_mode:
            from app.ml.anomaly.mock_anomaly import mock_score
            result = mock_score(features)
        else:
            from app.ml.anomaly.isolation_forest import get_anomaly_detector
            result = await get_anomaly_detector().score(features)
        state["anomaly"] = result
        return result

    elif tool_name == "check_credibility":
        from app.agents.credibility_checker import _SOURCE_SCORES
        source = tool_input.get("source", "unknown")
        url = tool_input.get("url", "")
        score = _SOURCE_SCORES.get(source, 0.3)
        for domain, domain_score in _SOURCE_SCORES.items():
            if domain in url:
                score = domain_score
                break
        state["credibility_score"] = score
        return {"credibility_score": score, "source": source}

    elif tool_name == "find_similar_historical_events":
        k = tool_input.get("k", 3)
        if settings.mock_mode:
            from app.ml.embeddings.mock_embeddings import mock_search
            result = mock_search(tool_input["text"], k=k)
        else:
            from app.ml.embeddings.nova_embeddings import embed_text
            from app.ml.embeddings.faiss_store import search
            vec = await embed_text(tool_input["text"])
            result = search(vec, k=k)
        state["similar_events"] = result
        return result

    elif tool_name == "get_target_users":
        from app.agents.personalization_agent import PersonalizationAgent
        agent = PersonalizationAgent()
        users = await agent._get_matching_users(
            tool_input["ticker"],
            tool_input.get("confidence_level", 0.5)
        )
        state["target_users"] = users
        return {"target_users": users, "count": len(users)}

    elif tool_name == "compose_alert":
        import uuid
        from datetime import datetime, timezone
        from app.schemas.alert import ActionCard

        action_card = ActionCard(
            alert_id=str(uuid.uuid4()),
            ticker=tool_input.get("ticker", state.get("ticker", "UNKNOWN")),
            event_summary=tool_input.get("event_summary", "Anomalous market signal detected"),
            sentiment=state.get("sentiment", {}),
            anomaly=state.get("anomaly", {}),
            nova_analysis={
                "event_summary": tool_input.get("event_summary", ""),
                "primary_driver": tool_input.get("primary_driver", ""),
                "sector_impact": tool_input.get("sector_impact", ""),
                "confidence_level": tool_input.get("confidence_level", 0.5),
                "risk_factors": tool_input.get("risk_factors", []),
                "time_horizon": tool_input.get("time_horizon", "intraday"),
                "recommended_actions": tool_input.get("recommended_actions", []),
                "affected_tickers": [tool_input.get("ticker", "UNKNOWN")],
            },
            similar_events=state.get("similar_events", []),
            credibility_score=state.get("credibility_score", 0.5),
            source_links=[signal.metadata.get("url", "")] if signal.metadata.get("url") else [],
            target_users=state.get("target_users", []),
            timestamp=datetime.now(timezone.utc).isoformat(),
            voice_ready=True,
        )
        state["action_card"] = action_card
        return {"status": "alert_composed", "alert_id": action_card.alert_id}

    return {"error": f"Unknown tool: {tool_name}"}


# ── Mock agentic loop (used when MOCK_MODE=true or Bedrock unavailable) ───────

async def _mock_agentic_process(signal: RawSignal, state: dict, tracer) -> None:
    """
    Simulates the agentic tool-calling loop deterministically.
    Nova would normally decide this sequence; here we replicate likely behavior.
    """
    ticker = state["ticker"]
    logger.info("agentic_mock_loop_start", ticker=ticker)

    async def traced_tool(name: str, inp: dict):
        result = await _execute_tool(name, inp, signal, state)
        tracer.record_tool(name, inp, result)
        return result

    # Nova would always start with these two
    await traced_tool("run_sentiment", {"text": signal.raw_text})
    sentiment = state.get("sentiment", {})

    await traced_tool("run_anomaly_detection", {
        "volume_zscore": signal.metadata.get("volume_zscore", 0.0),
        "price_change_pct": signal.metadata.get("change_pct", 0.0),
        "sentiment_intensity": abs(sentiment.get("intensity", 0.3)),
        "has_breaking_keywords": any(
            kw in signal.raw_text.lower()
            for kw in ["breaking", "surge", "crash", "soar", "plunge", "beat", "miss", "crushed"]
        ),
    })

    anomaly = state.get("anomaly", {})
    if not anomaly.get("is_anomaly"):
        logger.info("mock_agent_decision_drop", reason="not_anomalous", ticker=ticker)
        tracer.record_outcome(None, dropped_reason="not_anomalous")
        return

    await traced_tool("check_credibility", {
        "source": signal.source,
        "url": signal.metadata.get("url", ""),
    })

    if state.get("credibility_score", 0) < 0.3:
        logger.info("mock_agent_decision_drop", reason="low_credibility", ticker=ticker)
        tracer.record_outcome(None, dropped_reason="low_credibility")
        return

    await traced_tool("find_similar_historical_events", {"text": signal.raw_text, "k": 3})

    confidence = 0.75
    await traced_tool("get_target_users", {"ticker": ticker, "confidence_level": confidence})

    if not state.get("target_users"):
        logger.info("mock_agent_decision_drop", reason="no_target_users", ticker=ticker)
        tracer.record_outcome(None, dropped_reason="no_target_users")
        return

    sentiment_label = sentiment.get("label", "neutral")
    impact_map = {
        "positive": ("Strong positive market signal", "Potential upward momentum"),
        "negative": ("Negative market signal detected", "Potential downward pressure"),
        "neutral": ("Mixed market signal", "Monitor for direction"),
    }
    driver, impact = impact_map.get(sentiment_label, impact_map["neutral"])

    await traced_tool("compose_alert", {
        "ticker": ticker,
        "event_summary": f"Anomalous {sentiment_label} signal detected for {ticker} with {sentiment.get('confidence', 0.5):.0%} confidence.",
        "primary_driver": driver,
        "sector_impact": impact,
        "confidence_level": round(sentiment.get("confidence", 0.5) * 0.9, 2),
        "risk_factors": ["Market volatility", "Sentiment reversal risk", "Information uncertainty"],
        "time_horizon": "intraday",
        "recommended_actions": ["Monitor closely", "Review position size", "Set price alert"],
    })

    logger.info("mock_agent_decision_compose", ticker=ticker)


# ── Nova rate limiter: max 1 call per NOVA_INTERVAL seconds ──────────────────
import time as _time
_nova_lock = asyncio.Lock()
_last_nova_call: float = 0.0
NOVA_INTERVAL = 10  # seconds between Nova calls (Nova Lite allows ~60 RPM; 10s gives demo speed)


async def _acquire_nova_slot() -> None:
    """Wait until at least NOVA_INTERVAL seconds have passed since last Nova call."""
    global _last_nova_call
    async with _nova_lock:
        now = _time.monotonic()
        wait = NOVA_INTERVAL - (now - _last_nova_call)
        if wait > 0:
            logger.info("nova_rate_limit_wait", seconds=round(wait, 1))
            await asyncio.sleep(wait)
        _last_nova_call = _time.monotonic()


# ── Real agentic loop (Nova Lite decides tool calls) ──────────────────────────

async def _nova_agentic_process(signal: RawSignal, state: dict, tracer) -> None:
    """
    True agentic loop: Nova Lite receives the signal + tool definitions,
    then iteratively decides which tools to call until it's done.
    Max 10 rounds to prevent infinite loops.
    """
    await _acquire_nova_slot()  # enforce 1 Nova call per minute

    from app.services.bedrock_client import get_bedrock_client

    client = get_bedrock_client()
    loop = asyncio.get_event_loop()

    messages = [
        {
            "role": "user",
            "content": [{
                "text": (
                    f"Analyze this market signal and use the available tools to assess it:\n\n"
                    f"Ticker: {state['ticker']}\n"
                    f"Source: {signal.source}\n"
                    f"Text: \"{signal.raw_text[:500]}\"\n"
                    f"Metadata: {json.dumps(signal.metadata)}\n\n"
                    f"Use tools to gather evidence, then call compose_alert if the signal warrants an alert."
                )
            }]
        }
    ]

    for round_num in range(10):  # max 10 agentic rounds
        def _converse(msgs=messages):
            return client.converse(
                modelId=settings.bedrock_nova_lite_model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=msgs,
                toolConfig={"tools": TOOLS},
            )

        try:
            response = await loop.run_in_executor(None, _converse)
        except Exception as e:
            err = str(e)
            if "ModelErrorException" in err or "invalid sequence" in err.lower():
                # Transient Nova Lite tool-use malformation — retry once with fresh messages
                logger.warning("nova_tool_use_malformed_retry", ticker=state["ticker"], round=round_num + 1)
                messages = messages[:-1] if len(messages) > 1 else messages  # drop last assistant turn
                await asyncio.sleep(2)
                try:
                    response = await loop.run_in_executor(None, _converse)
                except Exception:
                    logger.warning("nova_retry_failed_skipping", ticker=state["ticker"])
                    break
            else:
                raise
        stop_reason = response.get("stopReason")
        output_message = response["output"]["message"]
        messages.append(output_message)

        # ── Trace this Nova LLM call ──────────────────────────────────
        tracer.record_llm(round_num + 1, messages, response)

        logger.info("nova_agentic_round", round=round_num + 1, stop_reason=stop_reason, ticker=state["ticker"])

        if stop_reason == "end_turn":
            break

        if stop_reason != "tool_use":
            break

        # Execute every tool Nova requested in this round
        # Bedrock Converse API returns tool use blocks as {"toolUse": {...}}
        tool_results = []
        for block in output_message.get("content", []):
            tool_use = block.get("toolUse")
            if not tool_use:
                continue

            tool_name = tool_use["name"]
            tool_input = tool_use["input"]
            tool_use_id = tool_use["toolUseId"]

            logger.info("nova_tool_call", tool=tool_name, ticker=state["ticker"])

            try:
                result = await _execute_tool(tool_name, tool_input, signal, state)
                tracer.record_tool(tool_name, tool_input, result)
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"json": result if isinstance(result, dict) else {"value": str(result)}}],
                    }
                })
            except Exception as e:
                logger.error("tool_execution_error", tool=tool_name, error=str(e))
                tracer.record_tool(tool_name, tool_input, None, error=str(e))
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"text": f"Error: {str(e)}"}],
                        "status": "error",
                    }
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})


# ── Public interface ──────────────────────────────────────────────────────────

class AgentOrchestrator:
    async def process(self, signal: RawSignal) -> None:
        ticker = resolve_ticker(signal.raw_text) or signal.ticker or "UNKNOWN"
        signal.ticker = ticker

        if ticker == "UNKNOWN":
            logger.debug("signal_skipped_no_ticker", text_preview=signal.raw_text[:80])
            return

        state: dict = {"ticker": ticker, "signal": signal}

        from app.services.observability import SignalTracer
        with SignalTracer(signal) as tracer:
            try:
                if settings.mock_mode:
                    await _mock_agentic_process(signal, state, tracer)
                else:
                    await _nova_agentic_process(signal, state, tracer)
            except Exception as e:
                logger.error("orchestrator_error", error=str(e), ticker=ticker)
                tracer.record_outcome(None, dropped_reason=f"exception: {e}")
                return

            action_card = state.get("action_card")
            if action_card and action_card.target_users:
                tracer.record_outcome(action_card)
                from app.services.alert_dispatcher import dispatch
                await dispatch(action_card)
                logger.info("alert_dispatched", ticker=ticker, users=len(action_card.target_users))
            else:
                if not state.get("action_card"):  # wasn't already recorded inside mock loop
                    tracer.record_outcome(None, dropped_reason="no_action_card_or_users")
                logger.info("signal_not_escalated", ticker=ticker)
