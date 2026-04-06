from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()
FLASK_SERVER_URL = "http://localhost:8200/result"
# Define request body structure
class TestResult(BaseModel):
    test_name: str
    success: bool
    text: str

# POST endpoint
@app.post("/result")
async def receive_result(data: TestResult):
    print("--> Received test result:\n%s\n" % data)
    status = "✅ SUCCESS" if data.success else "❌ FAILED"
    # Forward results to another server on localhost:8200
    try:
        response = requests.post(FLASK_SERVER_URL,
                                 json=data.model_dump())
        print(f"Forwarded to localhost:8200 - status: {response.status_code}")
    except Exception as e:
        print(f"Error forwarding to localhost:8200: {e}")
        return {
            "message": "Result received",
            "status": status
        }