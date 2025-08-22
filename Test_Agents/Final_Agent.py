import asyncio
import json
import aiohttp
from playwright.async_api import async_playwright
import re
from fastapi import FastAPI, Request
import uvicorn

API_KEY = "AIzaSyAzthcdc26drgtw8CzKMtcCGgPqs48yJDw"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

app = FastAPI()


async def ask_ai(dom_html, last_action=None, scraped_data=None, question=""):
    """Send the filtered DOM to the AI and get the next action."""
    prompt = f"""
You are an autonomous web agent. Your task is to interact with the given webpage
to answer the user’s question:

QUESTION: "{question}"

---
RULES:
1. Allowed actions (always return exactly one of these in JSON):
   - SCRAPE(selector) → extract text from the given selector
   - CLICK(selector) → click the given element
   - FILL(selector, value) → fill an input with the given value
   - STOP → stop execution, return when the answer is found
   - If Challenge or Task Is Completed and data is Found For The Given Question Then Stop the Agent

2. Completion Condition:
   - If the final answer or completion code is visible in the DOM or already scraped,
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


   ### If The Answer is Found For The For The Question And No Need Another Extraction then Stop Until Find If Any Success Like New Div Or Element Thenb Break it 
"""
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

    async with aiohttp.ClientSession() as session:
        async with session.post(f'{GEMINI_API_URL}?key={API_KEY}', headers=headers, data=json.dumps(payload)) as resp:
            resp.raise_for_status()
            result = await resp.json()

            if result and 'candidates' in result and result['candidates']:
                text_response = result['candidates'][0]['content']['parts'][0]['text']
                if text_response.strip().startswith('```json'):
                    text_response = text_response.strip().removeprefix('```json\n').removesuffix('```')
                json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
    return {"action": "STOP"}


async def run_agent(url, question):
    """Main agent loop."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)

        last_action = None
        scraped_data = None
        final_answer = None

        while True:
            divs_html = await page.evaluate("""
                () => {
                    const divs = document.querySelectorAll('div');
                    return Array.from(divs).map(d => d.outerHTML).join('\\n');
                }
            """)

            decision = await ask_ai(divs_html, last_action, scraped_data, question)
            action = decision.get("action")
            selector = decision.get("selector")
            value = decision.get("value")
            answer = decision.get("answer")

            print(f"AI decided: {decision}")

            if action == "STOP":
                final_answer = answer if answer else "No answer found"
                break

            elif action == "SCRAPE":
                scraped_data = await page.text_content(selector) if selector else None

            elif action == "CLICK":
                if selector:
                    await page.click(selector)

            elif action == "FILL":
                fill_value = value if value else scraped_data
                if selector and fill_value:
                    await page.fill(selector, fill_value)

            last_action = decision
            await page.wait_for_timeout(1000)

        await browser.close()
        return final_answer


@app.post("/webhook")
async def webhook(request: Request):
    """Webhook to start agent with given URL and question."""
    data = await request.json()
    url = data.get("url")
    question = data.get("question", "Find the completion code")

    if not url:
        return {"error": "URL is required"}

    answer = await run_agent(url, question)
    return {"url": url, "question": question, "answer": answer}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
