# browser_tools.py

import logging
from playwright.sync_api import Page
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_interactive_elements_with_context(page: Page) -> list[dict]:
    """
    Scans the live page, finds all interactive elements, and returns them
    with contextual information from their parents.
    """
    logging.info("Scanning page for interactive elements...")
    try:
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        interactive_elements = []
        element_id_counter = 0

        # Find all potential interactive elements
        targets = soup.find_all(['a', 'button', 'input'])

        for element in targets:
            try:
                # Assign a unique ID for the agent to reference
                agent_id = f"agent-element-{element_id_counter}"
                element['data-agent-id'] = agent_id
                element_id_counter += 1

                # Extract basic info
                tag = element.name
                text = element.get_text(strip=True)
                attributes = {k: v for k, v in element.attrs.items() if k in ['id', 'class', 'type', 'placeholder', 'aria-label', 'href']}

                # Find a meaningful parent for context
                parent_context_text = ""
                # A simple strategy: find the closest parent div with some text
                parent = element.find_parent('div')
                if parent:
                    parent_context_text = parent.get_text(separator=' ', strip=True)
                
                interactive_elements.append({
                    "agent_id": agent_id,
                    "tag": tag,
                    "text": text,
                    "attributes": attributes,
                    "context": parent_context_text[:200] # Limit context length
                })
            except Exception as e:
                logging.warning(f"Could not process an element: {e}")

        logging.info(f"Found {len(interactive_elements)} interactive elements.")
        return interactive_elements

    except Exception as e:
        logging.error(f"Failed to get page content or parse HTML: {e}")
        return []

def perform_click(page: Page, agent_id: str):
    """Performs a click on an element identified by its agent_id."""
    logging.info(f"Performing click on element: {agent_id}")
    selector = f"[data-agent-id='{agent_id}']"
    try:
        page.locator(selector).click(timeout=10000)
        # Wait for potential navigation or content load after click
        page.wait_for_load_state('domcontentloaded', timeout=5000)
    except Exception as e:
        logging.error(f"Failed to click element {agent_id}: {e}")
        raise
    return f"Successfully clicked element {agent_id}"

def perform_type(page: Page, agent_id: str, text: str):
    """Types text into an element identified by its agent_id."""
    logging.info(f"Typing into element: {agent_id}")
    selector = f"[data-agent-id='{agent_id}']"
    try:
        page.locator(selector).fill(text, timeout=10000)
    except Exception as e:
        logging.error(f"Failed to type into element {agent_id}: {e}")
        raise
    return f"Successfully typed into element {agent_id}"

def extract_page_data(page: Page, elements_to_extract: list[dict]) -> dict:
    """Extracts text from specified elements."""
    logging.info("Extracting final data from page...")
    extracted_data = {}
    html_content = page.content()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # This part can be enhanced with Gemini as well to find text 'near' a label
    # For simplicity, we'll assume a direct approach for now.
    # A real implementation would be more robust.
    voyage_element = soup.find(lambda tag: 'Voyage' in tag.get_text())
    arrival_element = soup.find(lambda tag: 'Estimated Arrival Date' in tag.get_text())
    
    if voyage_element and voyage_element.find_next_sibling():
         extracted_data['voyage_number'] = voyage_element.find_next_sibling().get_text(strip=True)
    if arrival_element and arrival_element.find_next_sibling():
        extracted_data['arrival_date'] = arrival_element.find_next_sibling().get_text(strip=True)

    return extracted_data