import sys
import asyncio
import json
import aiohttp
from playwright.async_api import async_playwright
import re
from fastapi import FastAPI
from pydantic import BaseModel
import multiprocessing
import subprocess
import time

API_KEY = "sk-spgw-api01-93e548ba90c413ff7b390e743d9b3a24"
GEMINI_API_URL = "https://register.hackrx.in/llm/openai"

app = FastAPI()

# ---------------- AI Function ----------------
async def ask_ai(dom_html, last_action=None, scraped_data=None, question=""):
    """Send the filtered DOM to the AI and get the next action."""
    prompt = f"""
You are an autonomous web agent. Your task is to interact with the given webpage
step by step until you can answer the user's question.

QUESTION: "{question}"

---
RULES:
1. Allowed actions (always return exactly one of these in JSON):
    - SCRAPE(selector)
    - CLICK(selector)
    - FILL(selector, value)
    - STOP → only use when final answer, completion code, or “Challenge Completed” message is clearly visible

2. Completion Condition:
    - Stop if:
      - Final answer or "completion code" is visible in DOM or in Scraped Data
      - OR any visible text clearly indicates the challenge is completed (e.g., “Challenge Completed”, “All Done”)
    - Do NOT repeat actions with the same selector/value combination unless new data appears

3. Continuity:
    - Track all previously scraped secrets or filled values in Scraped Data
    - If a previously scraped secret is about to be filled again, STOP unless new info is present

4. Efficiency:
    - Prefer SCRAPE first
    - Avoid repeating identical actions
    - If stuck in a loop for 5 consecutive actions without new scraped data, STOP and return partial data

5. Formatting:
    - Reply ONLY in valid JSON
    - Example: {{"action": "SCRAPE", "selector": "div span.kbd"}}

---
CONTEXT:
DOM (only <div> elements):
{dom_html}

Last Action: {last_action}
Scraped Data: {scraped_data}
"""





    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4.1-mini",  # or whatever model the endpoint supports
        "messages": [{"role": "user", "content": prompt}],
    }

    retries, delay = 3, 1
    for i in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(GEMINI_API_URL, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    result = await resp.json()

            if "choices" in result and result["choices"]:
                text_response = result["choices"][0]["message"]["content"]

                # cleanup code block if wrapped in ```json
                if text_response.strip().startswith("```json"):
                    text_response = text_response.strip().removeprefix("```json\n").removesuffix("```")

                match = re.search(r"\{.*\}", text_response, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                return {"action": "STOP"}
            else:
                return {"action": "STOP"}
        except Exception as e:
            print(f"Error on attempt {i+1}: {e}")
            if i < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                return {"action": "STOP"}



# ---------------- Core Playwright Logic ----------------
async def _run_playwright_agent(url: str, question: str):
    """The core logic for the web agent."""
    last_scraped_result = None
    try:
        async with async_playwright() as p:
            # Use a different approach to launch browser on Windows
            browser = await p.chromium.launch(
                headless=True,
                # Additional options to help with Windows compatibility
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.goto(url, wait_until='domcontentloaded')

            last_action = None
            scraped_data = None
            max_iterations = 10  # Safety limit to prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                
                divs_html = await page.evaluate(
                    """() => {
                        const divs = document.querySelectorAll('div');
                        return Array.from(divs).map(d => d.outerHTML).join('\\n');
                    }"""
                )

                decision = await ask_ai(divs_html, last_action, scraped_data, question)
                action = decision.get("action")
                selector = decision.get("selector")
                value = decision.get("value")

                print(f"AI decided: {action} | Selector: {selector} | Value: {value}")

                if action == "STOP":
                    if "answer" in decision:
                        last_scraped_result = decision["answer"]
                    break
                elif action == "SCRAPE":
                    try:
                        scraped_data = await page.text_content(selector)
                        if scraped_data:
                            last_scraped_result = scraped_data
                        print("Scraped:", scraped_data)
                    except Exception as e:
                        print(f"Scrape failed: {e}")
                        break
                elif action == "CLICK":
                    try:
                        await page.click(selector)
                        print(f"Clicked {selector}")
                    except Exception as e:
                        print(f"Click failed: {e}")
                        break
                elif action == "FILL":
                    fill_value = value if value else scraped_data
                    if fill_value:
                        try:
                            await page.fill(selector, fill_value)
                            print(f"Filled {selector} with {fill_value}")
                        except Exception as e:
                            print(f"Fill failed: {e}")
                            break
                else:
                    break

                last_action = decision
                await asyncio.sleep(1)

            await context.close()
            await browser.close()
            return last_scraped_result if last_scraped_result else "No data found."
    except Exception as e:
        print(f"An error occurred during Playwright execution: {e}")
        return f"An error occurred: {str(e)}"


# ---------------- Process-based execution for Windows compatibility ----------------
def run_playwright_in_process(url: str, question: str):
    """Run playwright in a separate process to avoid event loop conflicts"""
    import asyncio
    from playwright.async_api import async_playwright
    
    async def run_agent():
        return await _run_playwright_agent(url, question)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_agent())
        return result
    except Exception as e:
        return f"Error in agent execution: {str(e)}"
    finally:
        loop.close()


# ---------------- Main Agent ----------------
async def run_agent(url: str, question: str):
    """Run the autonomous agent for a given URL and question."""
    # Use process-based execution for better Windows compatibility
    with multiprocessing.Pool(1) as pool:
        result = pool.apply(run_playwright_in_process, (url, question))
    return result


# ---------------- FastAPI Endpoint ----------------
class RequestBody(BaseModel):
    url: str
    question: str


@app.post("/run-agent")
async def run_agent_api(body: RequestBody):
    try:
        result = await run_agent(body.url, body.question)
        return {"answer": result}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
async def root():
    return {"message": "Autonomous Web Agent API is running"}


# Alternative: Simple version without Playwright for testing
@app.post("/test-agent")
async def test_agent(body: RequestBody):
    """Test endpoint that doesn't use Playwright"""
    return {"answer": f"Test response for URL: {body.url}, Question: {body.question}"}


if __name__ == "__main__":
    import uvicorn
    # Use the correct way to run uvicorn with reload
    uvicorn.run("Final_Agent:app", host="0.0.0.0", port=8000, reload=True)