import os
import time
import json
import requests
import random
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

# Load environment variables from .env file
load_dotenv()
GEMINI_API_KEY = "AIzaSyApG8F4UIy371ryJ8bsSHT6xftHmplm21M"

app = Flask(__name__)

# The correct base URL for the Gemini API's generateContent method
GEMINI_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# The specific Gemini model to use
# Corrected from "gemini-2.5-flash-lite" to a valid model
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

def call_gemini(messages, max_retries=5):
    """
    Calls the Gemini API to generate content with a retry mechanism and
    exponential backoff for rate limit errors.

    Args:
        messages: A list of messages in the format [{"role": "user", "content": "..."}].
        max_retries: The maximum number of times to retry the request.

    Returns:
        The generated text content from the Gemini model.
    """
    full_url = f"{GEMINI_URL_BASE}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    # Convert the messages to the Gemini API's 'contents' format
    contents = []
    for message in messages:
        contents.append({
            "role": message["role"],
            "parts": [{"text": message["content"]}]
        })

    data = {
        "contents": contents
    }

    headers = {
        "Content-Type": "application/json"
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(full_url, headers=headers, data=json.dumps(data))
            response.raise_for_status()

            response_json = response.json()
            if 'candidates' in response_json and response_json['candidates']:
                candidate = response_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                    return candidate['content']['parts'][0]['text'].strip()
            
            # If the expected structure is not found, raise an error
            raise ValueError("Unexpected response format from Gemini API.")

        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 429:
                # Calculate exponential backoff with a bit of random jitter
                backoff_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Attempt {attempt + 1}: API rate limit exceeded (429). Retrying in {backoff_time:.2f} seconds.")
                time.sleep(backoff_time)
            else:
                # For other HTTP errors, re-raise immediately
                raise
        except Exception as e:
            # For other non-HTTP errors, re-raise immediately
            raise
    
    # If all retries fail, re-raise the last exception
    raise Exception(f"Failed to get a response from Gemini API after {max_retries} attempts.")


# AI decides which element to click
def ai_decide_click(dom_html):
    """
    Prompts the AI to decide which element to click based on the DOM HTML.

    Args:
        dom_html: The HTML of the current page.

    Returns:
        A CSS selector for the clickable element or "NO_ACTION".
    """
    prompt = f"""
You are an AI web agent. Here is the page DOM:
{dom_html}

Decide the next clickable element (button, link, etc.) to progress the challenge.
Return ONLY a CSS selector. If no action is needed, return "NO_ACTION".
"""
    return call_gemini([{"role": "user", "content": prompt}])

# AI finds answer to a question in the DOM
def ai_find_answer(dom_html, question):
    """
    Prompts the AI to find the answer to a question within the DOM HTML.

    Args:
        dom_html: The HTML of the current page.
        question: The question to answer.

    Returns:
        The answer text found in the DOM.
    """
    prompt = f"""
You are an AI web agent. Here is the page DOM:
{dom_html}

Find the answer to the following question: "{question}"
Return only the answer. Do not include any extra text or explanation.
"""
    return call_gemini([{"role": "user", "content": prompt}])

# AI decides which input box to fill
def ai_find_input(dom_html):
    """
    Prompts the AI to identify the correct input box for the answer.

    Args:
        dom_html: The HTML of the current page.

    Returns:
        A CSS selector for the input box or "NO_INPUT".
    """
    prompt = f"""
You are an AI web agent. Here is the page DOM:
{dom_html}

Identify the input box where the answer should be typed. Return only a CSS selector. 
If no input box is found, return "NO_INPUT". Do not include any extra text or explanation.
"""
    return call_gemini([{"role": "user", "content": prompt}])

@app.route("/solve-challenge", methods=["POST"])
def solve_challenge():
    """
    Endpoint to solve a web challenge using an AI agent.
    """
    data = request.json
    url = data.get("url")
    question = data.get("question")
    if not url or not question:
        return jsonify({"error": "URL and question are required"}), 400

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        try:
            solved = False
            attempts = 0
            while not solved and attempts < 10:
                attempts += 1
                
                # Wait for the page to be in a stable state before getting the DOM
                page.wait_for_load_state('networkidle')
                dom_html = page.content()

                # Step 1: AI decides which element to click
                selector = ai_decide_click(dom_html)
                if selector != "NO_ACTION":
                    try:
                        print(f"Attempt {attempts}: Clicking on selector '{selector}'")
                        page.wait_for_selector(selector, timeout=10000) # Wait for the element to be visible
                        page.click(selector)
                        
                        continue  # check updated DOM after click
                    except Exception as e:
                        print(f"Could not click selector '{selector}': {e}")
                        pass

                # Step 2: AI finds the input box
                input_selector = ai_find_input(dom_html)
                if input_selector != "NO_INPUT":
                    # Wait for the input field to be ready
                    page.wait_for_selector(input_selector, timeout=10000)
                    
                    # Step 3: AI finds answer
                    answer = ai_find_answer(dom_html, question)
                    print(f"Attempt {attempts}: Found answer '{answer}' and input selector '{input_selector}'")
                    
                    page.fill(input_selector, answer)
                    
                    # Add a small delay to ensure the text is fully entered
                    page.wait_for_timeout(500)
                    
                    page.press(input_selector, "Enter")
                    
                    # Wait for the page to navigate or for new content to appear after submission
                    page.wait_for_load_state('networkidle')
                    
                    # Step 4: Capture response
                    response_text = page.evaluate("document.body.innerText")
                    solved = True
                    browser.close()
                    return jsonify({"answer": answer, "response": response_text})

            browser.close()
            return jsonify({"error": "Unable to solve challenge after multiple attempts"}), 500

        except Exception as e:
            print(f"An error occurred: {e}")
            browser.close()
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = 5005
    app.run(host="0.0.0.0", port=port)
