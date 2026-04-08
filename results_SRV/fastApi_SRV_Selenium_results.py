from fastapi import FastAPI
from pydantic import BaseModel
import requests
from starlette import status
from utils.my_logger import get_logger

log = get_logger(log_filename="db_results_receiver_FASTAPI.log")

app = FastAPI()
FLASK_SERVER_URL = "http://localhost:8200/result"

# Define request body structure
class TestResult(BaseModel):
    test_name: str
    success: bool
    text: str
    start_time: str
    runtime: float

@app.get("/alive")
async def check_alive():
    return {"status": status.HTTP_200_OK, "message": "FASTApi Server is alive"}

# POST endpoint
@app.post("/result")
async def receive_result(data: TestResult):
    log.debug("-----------> Received test result:\n%s\n" % data)

    status = "✅ SUCCESS" if data.success else "❌ FAILED"


    # Forward results to another server on localhost:8200
    try:
        response = requests.post(FLASK_SERVER_URL,
                                 json=data.model_dump())

        log.info(f"Forwarded to localhost:8200 - status: {response.status_code}")
    except Exception as e:
        log.error(f"Error forwarding to localhost:8200: {e}")
        return {
            "message": "Result received",
            "status": status
        }
