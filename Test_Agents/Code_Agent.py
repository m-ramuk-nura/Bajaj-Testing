import uvicorn
from fastapi import FastAPI, Header
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import subprocess
from datetime import datetime
import textwrap

app = FastAPI()

UPSTREAM_LLM_URL = "https://register.hackrx.in/llm/openai"
UPSTREAM_KEY = "sk-spgw-api01-93e548ba90c413ff7b390e743d9b3a24"

# Directory to save generated code
GENERATED_CODE_DIR = "generated_codes"
os.makedirs(GENERATED_CODE_DIR, exist_ok=True)

# Use current folder as Git repo (already mapped)
GIT_REPO_PATH = os.path.abspath(".")

class AgentRequest(BaseModel):
    question: str

@app.post("/run-agent")
async def run_agent(req: AgentRequest, x_subscription_key: Optional[str] = Header(None)):
    try:
        print(f"[INFO] Received question: {req.question}")

        headers = {
            "Content-Type": "application/json",
            "x-subscription-key": x_subscription_key or UPSTREAM_KEY
        }

        # Construct LLM payload
        llm_payload = {
            "messages": [
                {"role": "system", "content": "You are a coding AI that ONLY outputs Python code."},
                {"role": "user", "content": f"Generate a Python program that solves this problem:\n{req.question}\nThe program must produce True/False or the correct output, and be syntax-error free."}
            ],
            "model": "gpt-4.1-nano"
        }

        # Call upstream LLM
        async with httpx.AsyncClient(timeout=120.0) as client:
            llm_resp = await client.post(UPSTREAM_LLM_URL, headers=headers, json=llm_payload)
            llm_data = llm_resp.json()

        generated_code = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "print('No code generated')")

        # Remove Markdown code blocks
        if generated_code.startswith("```") and generated_code.endswith("```"):
            lines = generated_code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            generated_code = "\n".join(lines)

        generated_code = generated_code.strip()
        print(f"[INFO] Cleaned Generated code:\n{generated_code}")

        # Dedent code to avoid syntax errors
        dedented_code = textwrap.dedent(generated_code)

        # Save code
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        code_filename = os.path.join(GENERATED_CODE_DIR, f"generated_{timestamp}.py")
        wrapped_code = f"""try:
{textwrap.indent(dedented_code, '    ')}
except Exception as e:
    print('Error:', e)
"""
        with open(code_filename, "w") as f:
            f.write(wrapped_code)
        print(f"[INFO] Code saved to: {code_filename}")

# Auto commit & push using existing Git mapping
        try:
            subprocess.run(["git", "-C", GIT_REPO_PATH, "add", code_filename], check=True)
            commit_msg = f"Add generated code {timestamp}"
            subprocess.run(["git", "-C", GIT_REPO_PATH, "commit", "-m", commit_msg], check=True)
            
            # Check if branch has upstream, else set it
            try:
                subprocess.run(["git", "-C", GIT_REPO_PATH, "rev-parse", "--abbrev-ref", "@{u}"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Upstream exists, simple push
                subprocess.run(["git", "-C", GIT_REPO_PATH, "push"], check=True)
            except subprocess.CalledProcessError:
                # Upstream not set, push with --set-upstream
                subprocess.run(["git", "-C", GIT_REPO_PATH, "push", "--set-upstream", "origin", "main"], check=True)

            print("[INFO] Code auto-pushed to GitHub successfully")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Git push failed: {e}")


        # Execute code
        python_command = "python3" if os.name != "nt" else "python"
        try:
            result = subprocess.run(
                [python_command, code_filename],
                capture_output=True,
                text=True,
                timeout=20
            )
            output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
            print(f"[INFO] Execution output:\n{output}")
        except subprocess.TimeoutExpired:
            output = "Error: Code execution timed out"
            print("[ERROR] Execution timed out")

        return {
            "answers": [output],
            "question": req.question,
            "generated_code_file": code_filename,
            "generated_code": generated_code
        }

    except Exception as e:
        print(f"[ERROR] {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
