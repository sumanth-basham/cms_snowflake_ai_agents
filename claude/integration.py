"""
claude/integration.py — Claude ↔ Cortex Agent integration layer.

Provides a conversation loop that connects Claude to the Snowflake
Cortex Agent API via tool calling.  Claude decides when to call the
`query_medication_adherence` tool, receives the structured results,
and generates a narrative response with insights.

Usage:
    from claude.integration import AdherenceAnalyst
    analyst = AdherenceAnalyst(api_key="...", cortex_api_url="http://localhost:8000")
    result = analyst.ask("Which states have the lowest statin adherence rates?")
    print(result["answer"])
    print(result["data"])
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from claude.tool_definition import CORTEX_AGENT_TOOL, SYSTEM_PROMPT, TOOL_LIST

logger = logging.getLogger(__name__)


class AdherenceAnalyst:
    """
    Orchestrates Claude + Cortex Agent tool-calling for adherence analytics.

    1. Sends the user question to Claude with the tool definition.
    2. When Claude calls `query_medication_adherence`, routes to the Cortex API.
    3. Returns Claude's final narrative response enriched with data and viz hints.
    """

    def __init__(
        self,
        api_key: str,
        cortex_api_url: str = "http://localhost:8000",
        cortex_api_key: Optional[str] = None,
        claude_model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 2048,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.cortex_api_url = cortex_api_url.rstrip("/")
        self.cortex_api_key = cortex_api_key
        self.claude_model = claude_model
        self.max_tokens = max_tokens
        self.timeout = timeout

    def ask(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Submit a question through the Claude + Cortex tool-calling pipeline.

        Returns:
            dict with keys: answer (str), data (list), viz_hint (dict),
                            sql (str), trace_id (str), tool_calls (list)
        """
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("anthropic package required: pip install anthropic") from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": question})

        tool_calls_made: List[Dict[str, Any]] = []
        last_cortex_result: Optional[Dict[str, Any]] = None

        # Agentic loop: Claude may call tools multiple times
        for _iteration in range(5):
            response = client.messages.create(
                model=self.claude_model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                tools=TOOL_LIST,
                messages=messages,
            )

            # Collect Claude's response blocks
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            if not tool_use_blocks:
                # Claude returned a final text response
                answer = " ".join(b.text for b in text_blocks).strip()
                return {
                    "answer": answer,
                    "data": last_cortex_result.get("data", []) if last_cortex_result else [],
                    "viz_hint": last_cortex_result.get("viz_hint", {}) if last_cortex_result else {},
                    "sql": last_cortex_result.get("sql") if last_cortex_result else None,
                    "trace_id": last_cortex_result.get("trace_id") if last_cortex_result else None,
                    "tool_calls": tool_calls_made,
                }

            # Append assistant turn to messages
            messages.append({"role": "assistant", "content": response.content})

            # Process each tool call
            tool_results = []
            for block in tool_use_blocks:
                tool_name = block.name
                tool_input = block.input
                logger.info("Claude tool call: %s(%s)", tool_name, json.dumps(tool_input)[:200])

                if tool_name == "query_medication_adherence":
                    cortex_result = self._call_cortex_api(
                        question=tool_input.get("question", ""),
                        max_rows=tool_input.get("max_rows", 100),
                    )
                    last_cortex_result = cortex_result
                    tool_calls_made.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "trace_id": cortex_result.get("trace_id"),
                    })
                    tool_result_content = json.dumps({
                        "answer": cortex_result.get("answer", ""),
                        "sql": cortex_result.get("sql", ""),
                        "row_count": cortex_result.get("row_count", 0),
                        "data": cortex_result.get("data", [])[:20],  # Limit context size
                        "viz_hint": cortex_result.get("viz_hint", {}),
                        "truncated": cortex_result.get("truncated", False),
                    })
                else:
                    tool_result_content = json.dumps({"error": f"Unknown tool: {tool_name}"})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_result_content,
                })

            messages.append({"role": "user", "content": tool_results})

        # Fallback if loop exhausted
        return {
            "answer": "Analysis complete. See data below.",
            "data": last_cortex_result.get("data", []) if last_cortex_result else [],
            "viz_hint": last_cortex_result.get("viz_hint", {}) if last_cortex_result else {},
            "sql": last_cortex_result.get("sql") if last_cortex_result else None,
            "trace_id": None,
            "tool_calls": tool_calls_made,
        }

    def _call_cortex_api(self, question: str, max_rows: int = 100) -> Dict[str, Any]:
        """Call the Cortex Agent /ask endpoint."""
        headers = {"Content-Type": "application/json"}
        if self.cortex_api_key:
            headers["X-API-Key"] = self.cortex_api_key

        payload = {"question": question, "max_rows": max_rows, "include_sql": True}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.cortex_api_url}/ask",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("Cortex API call failed: %s", exc)
            return {
                "answer": f"API error: {exc}",
                "data": [],
                "viz_hint": {"chart": "table"},
                "sql": None,
                "trace_id": None,
            }
