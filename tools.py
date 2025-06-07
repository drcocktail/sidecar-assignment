# browser_tools.py

import logging
from playwright.sync_api import Page
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_interactive_elements_with_context(page: Page) -> List[Dict[str, Any]]:
    """
    Finds all interactive elements on the page and annotates them with a unique ID.
    Returns a list of dictionaries, each representing an element.
    """
    page.wait_for_load_state('networkidle')

    interactive_elements = page.query_selector_all(
        "a, button, input, textarea, [role='button'], [onclick]"
    )

    elements_with_context = []
    for i, element in enumerate(interactive_elements):
        agent_id = f"agent-id-{i}"
        element.evaluate('(element, agentId) => element.setAttribute("data-agent-id", agentId)', agent_id)

        # Get context around the element
        outer_html = element.evaluate("el => el.outerHTML")

        element_info = {
            "agent_id": agent_id,
            "tag": element.evaluate("el => el.tagName.toLowerCase()"),
            "attributes": element.evaluate("el => Array.from(el.attributes).reduce((acc, attr) => { acc[attr.name] = attr.value; return acc; }, {})"),
            "outer_html": outer_html,
            "text": element.evaluate("el => el.innerText")
        }
        elements_with_context.append(element_info)

    return elements_with_context

def perform_click(page: Page, agent_id: str):
    """Clicks an element with the given agent_id."""
    selector = f"[data-agent-id='{agent_id}']"
    element = page.query_selector(selector)
    if element:
        element.click()
    else:
        raise ValueError(f"Could not find element with agent_id: {agent_id}")

def perform_type(page: Page, agent_id: str, text: str):
    """Types text into an element with the given agent_id."""
    selector = f"[data-agent-id='{agent_id}']"
    element = page.query_selector(selector)
    if element:
        element.type(text)
    else:
        raise ValueError(f"Could not find element with agent_id: {agent_id}")

def extract_page_data(page: Page, selectors: List[str]) -> Dict[str, str]:
    """Extracts data from the page based on a list of CSS selectors."""
    data = {}
    for selector in selectors:
        element = page.query_selector(selector)
        if element:
            data[selector] = element.inner_text()
        else:
            data[selector] = "Not found"
    return data

def get_page_content_summary(page: Page) -> str:
    """
    Gets a summary of the page's text content, cleaned for the LLM.
    """
    soup = BeautifulSoup(page.content(), "html.parser")
    
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)
    
    # Truncate for brevity
    max_length = 5000 
    return cleaned_text[:max_length] if len(cleaned_text) > max_length else cleaned_text