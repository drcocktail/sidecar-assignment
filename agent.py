# agent.py

import os
import json
import logging
from google import genai
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from playwright.sync_api import Page

import tools

# Configure Gemini API Key
# genai.configure(api_key=os.environ["GEMINI_API_KEY"]) # Recommended to use environment variables

class AgentState(TypedDict):
    """Defines the state for our LangGraph agent."""
    page: Page
    objective: str
    interactive_elements: List[dict]
    past_steps: List[dict]
    final_data: dict

class Agent:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("scanner", self._scanner_node)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("executor", self._executor_node)
        workflow.set_entry_point("scanner")

        workflow.add_conditional_edges(
            "planner",
            self._should_continue,
            {"continue": "executor", "end": END}
        )
        workflow.add_edge("executor", "scanner") # Loop back to see results of action
        return workflow.compile()

    def _scanner_node(self, state: AgentState):
        """Node that "sees" the page by scanning for interactive elements."""
        logging.info("Scanning page...")
        elements = tools.get_interactive_elements_with_context(state['page'])
        return {"interactive_elements": elements}

    def _planner_node(self, state: AgentState):
        """The 'brain' node. Decides the next action using Gemini."""
        logging.info("Planning next action...")
        
        prompt = f"""
        You are a web automation agent. Your high-level objective is: "{state['objective']}".
        You have already taken these steps: {json.dumps(state['past_steps'], indent=2)}

        Here is a JSON list of all interactive elements on the current page:
        ---
        {json.dumps(state['interactive_elements'], indent=2)}
        ---

        Based on your objective and the elements available, what is the single next action to take?
        Respond in a valid JSON format with a "tool" and "args".
        Valid tools are: "click", "type", "extract", "finish".
        - For "click" and "type", the 'args' should be a dictionary with "agent_id" and "description" of the target. For "type", also include "text".
        - For "extract", args should be a list of items to extract.
        - If the objective is complete and you have the data, use the "finish" tool.
        """
        
        try:
            response = self.model.generate_content(prompt)
            decision = json.loads(response.text)
            logging.info(f"Gemini decision: {decision}")
            return {"decision": decision}
        except (json.JSONDecodeError, Exception) as e:
            logging.error(f"Error parsing Gemini response or in API call: {e}")
            # Simple error handling: decide to finish on failure
            return {"decision": {"tool": "finish", "args": {"error": str(e)}}}


    def _executor_node(self, state: AgentState):
        """The 'hands' node. Executes the decided action."""
        decision = state.get("decision", {})
        tool = decision.get("tool")
        args = decision.get("args", {})
        page = state['page']

        try:
            if tool == "click":
                tools.perform_click(page, args['agent_id'])
            elif tool == "type":
                tools.perform_type(page, args['agent_id'], args['text'])
            elif tool == "extract":
                data = tools.extract_page_data(page, args)
                return {"final_data": data}

            # Log the successful step for the plan
            step_log = {
                "action": tool,
                "target_description": args.get('description'),
                "selector": f"[data-agent-id='{args.get('agent_id')}']",
            }
            if 'text' in args:
                # In a real plan, you'd replace the actual ID with a placeholder
                step_log["is_dynamic_value"] = True 

            return {"past_steps": state["past_steps"] + [step_log]}

        except Exception as e:
            logging.error(f"Tool execution failed: {e}")
            # On failure, we could add the error to the state and re-plan
            # For now, we'll just stop.
            return {"final_data": {"error": f"Execution failed at tool {tool}"}}


    def _should_continue(self, state: AgentState):
        """Determines whether to continue the loop or end."""
        if state.get("decision", {}).get("tool") == "finish":
            return "end"
        if state.get("final_data"): # If data was extracted
            return "end"
        return "continue"

    def run(self, page, objective):
        initial_state = AgentState(
            page=page,
            objective=objective,
            interactive_elements=[],
            past_steps=[],
            final_data={}
        )
        return self.graph.invoke(initial_state)