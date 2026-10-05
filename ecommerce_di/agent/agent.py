"""
AI Business Agent using Google Gemini with function calling.
Multi-step investigation → evidence-based response.
"""
import json
import logging
from datetime import datetime
from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from agent.tools import TOOL_FUNCTIONS, GEMINI_TOOLS
from database.connection import db_cursor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert e-commerce business intelligence analyst and advisor.

You have access to analytical tools that query a real e-commerce database.
You must ALWAYS use these tools to get actual data before answering.
NEVER invent business numbers or make up statistics.

Your role:
1. Understand the business question
2. Select the most appropriate analytical tool(s)
3. Execute them to get real data
4. Analyse the results
5. Provide a structured response

Response format for complex questions:
**Answer**: Direct answer to the question
**Evidence**: Key metrics from the data (use actual numbers)
**Possible Causes**: Factors supported by the analysis
**Recommendation**: Specific, actionable business suggestions

Rules:
- Always distinguish between what the data shows (evidence) vs interpretation (analysis)
- Recommendations must be grounded in the evidence
- Clearly label forecasts as estimates
- If data is insufficient, say so clearly
- Use Indian number formatting where appropriate (₹, lakhs, crores)
- Be concise but thorough
"""

MAX_TOOL_CALLS = 5  # prevent infinite loops


class BusinessAgent:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not set. Please add it to your .env file."
            )
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        self._genai = genai
        self._model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            tools=GEMINI_TOOLS,
        )

    def investigate(self, user_query: str) -> dict:
        """
        Run a multi-step investigation and return structured result.
        Returns: {
            "answer": str,
            "tools_used": list,
            "tool_results": dict,
            "raw_response": str,
            "error": str | None,
        }
        """
        tools_used   = []
        tool_results = {}

        chat = self._model.start_chat(enable_automatic_function_calling=False)

        # Initial message
        response = chat.send_message(user_query)
        call_count = 0

        while call_count < MAX_TOOL_CALLS:
            # Check if model wants to call tools
            has_tool_call = False
            tool_responses = []

            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    has_tool_call = True
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)

                    tools_used.append(fn_name)
                    logger.info("AI calling tool: %s(%s)", fn_name, fn_args)

                    # Execute the tool
                    if fn_name in TOOL_FUNCTIONS:
                        try:
                            result_str = TOOL_FUNCTIONS[fn_name](**fn_args)
                        except TypeError as e:
                            result_str = json.dumps({"error": f"Bad arguments: {e}"})
                    else:
                        result_str = json.dumps({"error": f"Unknown tool: {fn_name}"})

                    tool_results[fn_name] = result_str

                    tool_responses.append(
                        self._genai.protos.Part(
                            function_response=self._genai.protos.FunctionResponse(
                                name=fn_name,
                                response={"result": result_str},
                            )
                        )
                    )

            if not has_tool_call:
                break

            # Send tool results back
            response = chat.send_message(tool_responses)
            call_count += 1

        # Extract final text response
        final_text = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                final_text += part.text

        # Log the interaction
        self._log_interaction(user_query, tools_used, final_text[:500])

        return {
            "answer":       final_text,
            "tools_used":   list(set(tools_used)),
            "tool_results": tool_results,
            "raw_response": final_text,
            "error":        None,
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
