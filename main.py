# main.py

import logging
from playwright.sync_api import sync_playwright
from agent import Agent

# --- Configuration ---
URL = "http://www.seacargotracking.net/"
OBJECTIVE = "Find the tracking details for the HMM ID 'HMMU2048983'." # Example ID
LOG_LEVEL = logging.INFO
# ---

def setup_logging():
    """Configures logging for the application."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def main():
    """Main function to run the web automation agent."""
    setup_logging()
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False) # Set headless=True for background execution
            page = browser.new_page(ignore_https_errors=True)
            page.set_default_timeout(60000)  # 60 seconds
            page.goto(URL)

            agent = Agent()
            result = agent.run(page, OBJECTIVE)
            
            logging.info("Agent run finished. Final State:")
            logging.info(result)

        except Exception as e:
            logging.error(f"An error occurred during the agent run: {e}")
        finally:
            if 'browser' in locals() and browser.is_connected():
                browser.close()
            logging.info("Browser closed. Run complete.")

if __name__ == "__main__":
    main() 