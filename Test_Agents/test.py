import requests

url = "http://127.0.0.1:5005/solve-challenge"
data = {
    "url": "https://register.hackrx.in/showdown/startChallenge/ZXlKaGJHY2lPaUpJVXpJMU5pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SmpiMjlzUjNWNUlqb2lRVVpNUVVnaUxDSmphR0ZzYkdWdVoyVkpSQ0k2SW1ocFpHUmxiaUlzSW5WelpYSkpaQ0k2SW5WelpYSmZZV1pzWVdnaUxDSmxiV0ZwYkNJNkltRm1iR0ZvUUdKaGFtRnFabWx1YzJWeWRtaGxZV3gwYUM1cGJpSXNJbkp2YkdVaU9pSmpiMjlzWDJkMWVTSXNJbWxoZENJNk1UYzFOVGcxTlRJNU1pd2laWGh3SWpveE56VTFPVFF4TmpreWZRLi1ySHRmZ2JnQnF0QTdmS09rYm9tTDFvR29HX0R1YV9WNUZyZWZ6U1B0THM=",
    "question": "What is the challenge ID?"
}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("Raw Response:", response.text)   # 👈 check what’s really coming back
