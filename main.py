import uvicorn
from fastapi import FastAPI, Header
from pydantic import BaseModel
from typing import Optional, List
import httpx

app = FastAPI()

UPSTREAM_LLM_URL = "https://register.hackrx.in/llm/openai"
UPSTREAM_KEY = "sk-spgw-api01-93e548ba90c413ff7b390e743d9b3a24"
EXTERNAL_CHALLENGE_URL = "http://localhost:8000/run-agent"  # your 8000-running endpoint

class ChallengeRequest(BaseModel):
    url: str
    questions: List[str]  # multiple questions


@app.post("/challenge/solve")
async def challenge_solve(req: ChallengeRequest, x_subscription_key: Optional[str] = Header(None)):
    try:
        headers = {
            "Content-Type": "application/json",
            "x-subscription-key": x_subscription_key or UPSTREAM_KEY
        }

        # --- Combine questions with clear numbering ---
        combined_question = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(req.questions)])

        async with httpx.AsyncClient(timeout=120.0) as client:

            # --- Send combined questions to external agent ---
            payload = {
                "url": req.url,
                "question": combined_question
            }
            resp = await client.post(EXTERNAL_CHALLENGE_URL, headers=headers, json=payload)
            data = resp.json()
            external_answer = data.get("answer") or data.get("answers") or "No answer"

            # --- Send combined questions + external answer to internal LLM ---
            internal_payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a pro coding assistant. "
                            "You MUST always incorporate the external agent's result when answering. "
                            "Do not say you cannot browse. "
                            "If the external agent provides a completion code, challenge name, or other details, "
                            "use them directly in your answer. "
                            "Give output in format ['answer1','answer2']."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Here is the challenge info:\n"
                            f"- URL: {req.url}\n"
                            f"- Questions:\n{combined_question}\n"
                            f"- External Agent Answer: {external_answer}\n\n"
                            "Using this external knowledge, give me the final solution clearly."
                        )
                    }
                ],
                "model": "gpt-4.1-nano"
            }

            internal_resp = await client.post(UPSTREAM_LLM_URL, headers=headers, json=internal_payload)
            internal_data_json = internal_resp.json()
            internal_answer = internal_data_json.get("choices", [{}])[0].get("message", {}).get("content", "No answer")

        return {
            "answers": [internal_answer]
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
