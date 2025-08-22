import asyncio
import json
import aiohttp
from playwright.async_api import async_playwright
import re

API_KEY = "AIzaSyAzthcdc26drgtw8CzKMtcCGgPqs48yJDw"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

async def ask_ai(dom_html, last_action=None, scraped_data=None):
    """Send the filtered DOM to the AI and get the next action."""
    Question = "Go to the website and start the challenge. Complete the challenge and return the answers for the following question? What is the completion code? "
    print(dom_html)
    prompt = f"""
You are an autonomous web agent. Your task is to interact with the given webpage
to answer the user’s question:

QUESTION: "{Question}"

---
RULES:
1. Allowed actions (always return exactly one of these in JSON):
   - SCRAPE(selector) → extract text from the given selector
   - CLICK(selector) → click the given element
   - FILL(selector, value) → fill an input with the given value
   - STOP → stop execution, return when the answer is found
   - If Challenge or Task Is Completed and data is Found For The Given Question Then Stop the Agent

2. Completion Condition:
   - If the "completion code" or final answer is visible in the DOM or already scraped,
     immediately return:
     {{"action": "STOP", "answer": "<the code>"}}

3. Efficiency:
   - Do NOT repeat actions unnecessarily (don’t scrape/click/fill the same element twice).
   - If the next logical step is unclear, prefer SCRAPE over random CLICK.

4. Formatting:
   - Reply ONLY in valid JSON.
   - Example: {{"action": "SCRAPE", "selector": "div span.kbd"}}
   - Never include explanations, markdown, or extra text.

---
CONTEXT:
DOM (only <div> elements):
{dom_html}

Last Action: {last_action}
Scraped Data: {scraped_data}

Your job:
- Identify the hidden secret (completion code).
- Fill it into 'input.input' and CLICK 'button.success'.
- After Fill Values Submit and Try The Next Step Like Wise Do Until The Answer get If Answer Found for The Question Then Stop The Process
- Stop as soon as the completion code or final answer is confirmed.
"""


    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

    retries = 3
    delay = 1
    for i in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{GEMINI_API_URL}?key={API_KEY}', headers=headers, data=json.dumps(payload)) as resp:
                    resp.raise_for_status()
                    result = await resp.json()

                    if result and 'candidates' in result and result['candidates']:
                        text_response = result['candidates'][0]['content']['parts'][0]['text']
                        # Remove ```json code block if present
                        if text_response.strip().startswith('```json') and text_response.strip().endswith('```'):
                            text_response = text_response.strip().removeprefix('```json\n').removesuffix('```')
                        # Extract JSON
                        json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group(0))
                        else:
                            print(f"Could not find JSON in response: {text_response}")
                            return {"action": "STOP"}
                    else:
                        print(f"API response missing candidates: {result}")
                        return {"action": "STOP"}
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            print(f"Error on attempt {i+1}: {e}")
            if i < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                return {"action": "STOP"}
    return {"action": "STOP"}

async def run_agent():
    """Main agent loop."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://register.hackrx.in/showdown/startChallenge/ZXlKaGJHY2lPaUpJVXpJMU5pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SmpiMjlzUjNWNUlqb2lUVlZCV2xwQlRTSXNJbU5vWVd4c1pXNW5aVWxFSWpvaWFHbGtaR1Z1SWl3aWRYTmxja2xrSWpvaWRYTmxjbDl0ZFdGNmVtRnRJaXdpWlcxaGFXd2lPaUp0ZFdGNmVtRnRRR0poYW1GcVptbHVjMlZ5ZG1obFlXeDBhQzVwYmlJc0luSnZiR1VpT2lKamIyOXNYMmQxZVNJc0ltbGhkQ0k2TVRjMU5UZzFPVGswTVN3aVpYaHdJam94TnpVMU9UUTJNelF4ZlEuc2dYeVdWVUlVdFE1T2NpbHRabnNWUmI1NjE0MVBPU2ZYaENMTXliMUN2QQ==")

        last_action = None
        scraped_data = None

        while True:
            # Get only div elements to reduce DOM size
            divs_html = await page.evaluate("""
                () => {
                    const divs = document.querySelectorAll('div');
                    return Array.from(divs).map(d => d.outerHTML).join('\\n');
                }
            """)

            decision = await ask_ai(divs_html, last_action, scraped_data)
            action = decision.get("action")
            selector = decision.get("selector")
            value = decision.get("value")

            print(f"AI decided: {action} | Selector: {selector} | Value: {value}")

            if action == "STOP":
                break
            elif action == "SCRAPE":
                if not selector:
                    print("SCRAPE failed: No selector provided")
                    break
                try:
                    scraped_data = await page.text_content(selector)
                    print("Scraped:", scraped_data)

                except Exception as e:
                    print(f"Scrape failed: {e}")
                    break
            elif action == "CLICK":
                if not selector:
                    print("CLICK failed: No selector provided")
                    break
                try:
                    await page.click(selector)
                    print(f"Clicked {selector}")
                except Exception as e:
                    print(f"Click failed: {e}")
                    break
            elif action == "FILL":
                if not selector:
                    print("FILL failed: No selector provided")
                    break
                fill_value = value if value else scraped_data
                if not fill_value:
                    print(f"FILL failed: No value to fill for {selector}")
                    break
                try:
                    await page.fill(selector, fill_value)
                    print(f"Filled {selector} with {fill_value}")
                except Exception as e:
                    print(f"Fill failed: {e}")
                    break
            else:
                print(f"Unknown action: {action}")
                break

            last_action = decision
            await page.wait_for_timeout(1000)

        await browser.close()
        print("Agent finished.")

if __name__ == "__main__":
    asyncio.run(run_agent())
