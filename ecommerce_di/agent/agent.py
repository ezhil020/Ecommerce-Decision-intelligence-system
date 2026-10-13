"""
AI Business Agent using Ollama with function/tool calling.
Local private LLM execution (default: Qwen2.5:3b).
Multi-step investigation → evidence-based response.
"""
import json
import logging
from datetime import datetime
import requests

from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL
from agent.tools import TOOL_FUNCTIONS, OLLAMA_TOOLS
from database.connection import db_cursor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert e-commerce business intelligence analyst and strategic advisor.

You have access to a complete set of analytical tools that query a live SQLite data warehouse:
- Pre-built analytical tools: `get_sales_kpis`, `get_sales_trend`, `get_category_performance`, `get_product_performance`, `get_inventory_risk`, `get_overstock`, `get_high_demand_low_stock`, `get_customer_analysis`, `get_geographic_analysis`, `get_payment_analysis`, `get_refund_analysis`, `get_order_status_analysis`, `get_profitability_analysis`, `get_anomalies`, `get_forecast`, `compare_periods`.
- General Analytical SQL tool: `execute_sql(query)` — use this for ANY ad-hoc question, custom breakdown, or whenever pre-built tools lack the specific breakdown (e.g. by gender, specific dates, customer names, rankings, product specs). Tables available: `dim_customer`, `dim_product`, `fact_orders`, `fact_payments`, `dim_date`.

IMPORTANT: If a pre-built tool returns results that do not directly answer the specific question (for example, if spend by gender or a specific column was asked for and not present in the tool output), immediately use `execute_sql` to query the exact answer from the database!
NEVER say numbers are missing without running `execute_sql` to check the database.
NEVER fabricate metrics or numbers.

Your workflow:
1. Understand the user's business question.
2. Select the most relevant analytical tool(s), or execute an analytical SQL query with `execute_sql` if a custom aggregation or filter is needed.
3. Review the returned numbers.
4. Synthesize a structured, executive-grade answer.

Response format for business questions:
**Answer**: Direct answer to the question with the primary metric.
**Evidence**: Key figures from the database results (with exact amounts, counts, percentages, and currencies).
**Possible Causes / Insights**: Deep-dive analytical explanation supported by the data patterns.
**Recommendation**: Specific, high-priority, actionable commercial steps to take.

Rules:
- Format currency in Indian Rupees (₹) where appropriate.
- Be concise, direct, professional, and well-structured.
"""

MAX_TOOL_CALLS = 5  # prevent infinite loops


class BusinessAgent:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL

    def check_connection(self) -> tuple[bool, str]:
        """Verify Ollama server is reachable and target model is present."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=4)
            if resp.status_code != 200:
                return False, f"Ollama HTTP error {resp.status_code}"
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            # Match model name or model prefix (e.g. qwen2.5:3b)
            has_model = any(self.model in m or m.startswith(self.model.split(":")[0]) for m in models)
            if not has_model:
                return False, f"Model '{self.model}' not found in Ollama. Available: {', '.join(models)}"
            return True, f"Connected to Ollama ({self.model})"
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running (`ollama serve`)."
        except Exception as e:
            return False, f"Ollama connection check failed: {e}"

    def investigate(self, user_query: str) -> dict:
        """
        Run a multi-step tool-augmented investigation using Ollama /api/chat.
        Returns: {
            "answer": str,
            "tools_used": list,
            "tool_results": dict,
            "raw_response": str,
            "error": str | None,
        }
        """
        tools_used = []
        tool_results = {}

        # Check connectivity
        is_ok, msg = self.check_connection()
        if not is_ok:
            return {
                "answer": "",
                "tools_used": [],
                "tool_results": {},
                "raw_response": "",
                "error": msg,
            }

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ]

        call_count = 0
        final_text = ""

        try:
            while call_count < MAX_TOOL_CALLS:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "tools": OLLAMA_TOOLS,
                    "stream": False,
                }

                resp = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=60,
                )

                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama chat error {resp.status_code}: {resp.text}")

                resp_data = resp.json()
                assistant_msg = resp_data.get("message", {})
                messages.append(assistant_msg)

                tool_calls = assistant_msg.get("tool_calls", [])
                if not tool_calls:
                    # Model provided text answer without further tool calls
                    final_text = assistant_msg.get("content", "")
                    break

                # Execute requested tools
                for tc in tool_calls:
                    fn_info = tc.get("function", {})
                    fn_name = fn_info.get("name")
                    raw_args = fn_info.get("arguments", {})

                    if isinstance(raw_args, str):
                        try:
                            fn_args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            fn_args = {}
                    elif isinstance(raw_args, dict):
                        fn_args = raw_args
                    else:
                        fn_args = {}

                    tools_used.append(fn_name)
                    logger.info("Ollama AI calling tool: %s(%s)", fn_name, fn_args)

                    if fn_name in TOOL_FUNCTIONS:
                        try:
                            result_str = TOOL_FUNCTIONS[fn_name](**fn_args)
                        except TypeError as e:
                            # Try calling without unexpected arguments if schema mismatch
                            try:
                                result_str = TOOL_FUNCTIONS[fn_name]()
                            except Exception:
                                result_str = json.dumps({"error": f"Bad arguments: {e}"})
                        except Exception as e:
                            result_str = json.dumps({"error": f"Tool execution failed: {e}"})
                    else:
                        result_str = json.dumps({"error": f"Unknown tool: {fn_name}"})

                    tool_results[fn_name] = result_str

                    # Append tool result message for Ollama
                    messages.append({
                        "role": "tool",
                        "content": str(result_str),
                        "name": fn_name,
                    })

                call_count += 1

            # If loop finished on tool call, request final synthesis if no final text
            if not final_text and len(messages) > 2:
                synth_payload = {
                    "model": self.model,
                    "messages": messages + [
                        {"role": "user", "content": "Please synthesize the evidence from the analytical tool results and answer the business question."}
                    ],
                    "stream": False,
                }
                synth_resp = requests.post(f"{self.base_url}/api/chat", json=synth_payload, timeout=60)
                if synth_resp.status_code == 200:
                    final_text = synth_resp.json().get("message", {}).get("content", "")

            # Log interaction to database
            self._log_interaction(user_query, tools_used, final_text[:500])

            return {
                "answer": final_text.strip(),
                "tools_used": list(set(tools_used)),
                "tool_results": tool_results,
                "raw_response": final_text,
                "error": None,
            }

        except Exception as exc:
            logger.error("AI Investigation error: %s", exc)
            return {
                "answer": "",
                "tools_used": list(set(tools_used)),
                "tool_results": tool_results,
                "raw_response": "",
                "error": f"Investigation failed: {exc}",
            }

    def _log_interaction(self, query: str, tools: list, summary: str):
        try:
            with db_cursor() as cur:
                cur.execute(
                    "INSERT INTO ai_interaction_log(logged_at,user_query,tools_used,response_summary) "
                    "VALUES(?,?,?,?)",
                    (datetime.now().isoformat(), query, ",".join(tools), summary)
                )
        except Exception as exc:
            logger.warning("Could not log AI interaction: %s", exc)


_agent_instance: BusinessAgent | None = None


def get_agent() -> BusinessAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BusinessAgent()
    return _agent_instance
