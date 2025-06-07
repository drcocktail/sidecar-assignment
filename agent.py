# agent.py

import os
import json
import logging
from google import genai
from google.genai.types import GenerateContentResponse
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langgraph.graph.message import add_messages
from playwright.sync_api import Page
from dotenv import load_dotenv

load_dotenv()

import tools

# Configure the client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

class AgentState(TypedDict):
    """Defines the state for our LangGraph agent."""
    page: Page
    objective: str
    page_summary: str
    interactive_elements: List[dict]
    past_steps: List[dict]
    final_data: dict
    plan: List[dict]
    decision: dict

class Agent:
    def __init__(self):
        self.client = client
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("scanner_interactive", self._scanner_interactive_node)
        workflow.add_node("scanner_full", self._scanner_full_node)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("executor", self._executor_node)
        workflow.set_entry_point("scanner_interactive")

        workflow.add_edge("scanner_interactive", "planner")
        workflow.add_edge("scanner_full", "planner")
        workflow.add_edge("executor", "scanner_full") # After action, do a full scan

        workflow.add_conditional_edges(
            "planner", self._should_continue, {"continue": "executor", "end": END}
        )
        return workflow.compile()

    def _scanner_interactive_node(self, state: AgentState):
        """Node that quickly scans only for interactive elements."""
        logging.info("Scanning for interactive elements...")
        elements = tools.get_interactive_elements_with_context(state["page"])
        logging.info(f"Found {len(elements)} interactive elements.")
        return {
            "interactive_elements": elements,
            "page_summary": "", # Ensure summary is cleared
            "past_steps": state["past_steps"]
            + [{"action": "scan_interactive", "status": "success"}],
        }

    def _scanner_full_node(self, state: AgentState):
        """Node that does a full scan of page content and interactive elements."""
        logging.info("Performing full page scan...")
        page_summary = tools.get_page_content_summary(state["page"])
        elements = tools.get_interactive_elements_with_context(state["page"])
        logging.info(f"Full scan found {len(elements)} elements and page content.")
        return {
            "page_summary": page_summary,
            "interactive_elements": elements,
            "past_steps": state["past_steps"]
            + [{"action": "scan_full", "status": "success"}],
        }

    def _planner_node(self, state: AgentState):
        """The 'brain' node. Decides the next action using Gemini."""
        logging.info("Planning next action...")

        # Build a dynamic prompt
        prompt_parts = [
            f"You are a web automation agent. Your high-level objective is: \"{state['objective']}\".",
            f"You have already taken these steps: {json.dumps(state['past_steps'], indent=2)}"
        ]

        if state.get('page_summary'):
            prompt_parts.append(f"\nHere is a summary of the text content on the current page:\n---\n{state['page_summary']}\n---")

        prompt_parts.append(f"\nHere is a JSON list of all interactive elements on the current page:\n---\n{json.dumps(state['interactive_elements'], indent=2)}\n---")
        prompt_parts.append("\nBased on your objective, the page content, and the available elements, what is the single next action to take?")
        prompt_parts.append(
            """
Your response must be a valid JSON object with a "tool" and "args".
- The "tool" must be one of: "click", "type", "extract", "finish".
- For "click", 'args' must contain "agent_id" (string) and a "description" (string).
- For "type", 'args' must contain "agent_id" (string) and "text" (string).
- For "extract", your 'args' should be a list of concise CSS selectors to get the data. Focus on selectors for elements that contain the final answer to the objective.
- Use "finish" when the objective is complete or you are stuck.
            """
        )
        prompt = "\n".join(prompt_parts)

        try:
            response: GenerateContentResponse = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            decision = json.loads(response.text)
            logging.info(f"Gemini decision: {decision}")
            return {"decision": decision}
        except (json.JSONDecodeError, Exception) as e:
            logging.error(f"Error parsing Gemini response or in API call: {e}")
            return {"decision": {"tool": "finish", "args": {"error": str(e)}}}

    def _executor_node(self, state: AgentState):
        """The 'hands' node. Executes the decided action."""
        decision = state.get("decision", {})
        tool_name = decision.get("tool")
        args = decision.get("args", {})
        page = state["page"]

        logging.info(
            f"Executing: {tool_name} with arguments: {json.dumps(args, indent=2)}"
        )

        step_log = {"action": tool_name, "args": args, "status": "pending"}

        try:
            if tool_name == "click":
                tools.perform_click(page, args["agent_id"])
                step_log["status"] = "success"
            elif tool_name == "type":
                tools.perform_type(page, args["agent_id"], args["text"])
                step_log["status"] = "success"
            elif tool_name == "extract":
                data = tools.extract_page_data(page, args)
                step_log["status"] = "success"
                return {
                    "final_data": data,
                    "past_steps": state["past_steps"] + [step_log],
                }

            return {"past_steps": state["past_steps"] + [step_log]}

        except Exception as e:
            logging.error(f"Tool execution failed for {tool_name}: {e}")
            step_log["status"] = "failure"
            step_log["error"] = str(e)
            return {
                "past_steps": state["past_steps"] + [step_log],
                "final_data": {
                    "error": f"Execution failed at tool {tool_name}"
                },
            }

    def _should_continue(self, state: AgentState):
        """Determines whether to continue the loop or end."""
        if (
            state.get("decision", {}).get("tool") == "finish"
            or state.get("final_data")
        ):
            plan = [
                step
                for step in state["past_steps"]
                if step.get("status") == "success"
            ]
            if plan:  # Only save if there are successful steps
                with open("plan.json", "w") as f:
                    json.dump(plan, f, indent=2)
                logging.info("Plan saved to plan.json")
            return "end"
        return "continue"

    def run(self, page, objective):
        initial_state = AgentState(
            page=page,
            objective=objective,
            page_summary="",
            interactive_elements=[],
            past_steps=[],
            final_data={},
            plan=[],
            decision={},
        )
        # Increase recursion limit to allow for more complex tasks
        return self.graph.invoke(initial_state, {"recursion_limit": 50})