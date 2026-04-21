import requests

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from starlette import status
from utils.my_logger import get_logger
from utils.database import DatabaseHandler

log = get_logger(log_filename="db_results_receiver_FASTAPI.log")

app = FastAPI()
FLASK_SERVER_RESULT_URL = "http://localhost:8200/result"
FLASK_SERVER_NEW_RESULT_PING_URL = "http://localhost:8200/new-result-ping"  # New endpoint to notify Flask of new results

# Initialize database handler
db_handler = DatabaseHandler(database_url="sqlite:///./test_results.db")
db_handler.init_db()

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

    status_text = "✅ SUCCESS" if data.success else "❌ FAILED"

    # Store result in database
    result_id = db_handler.store_result(data.model_dump())
    if result_id:
        log.info(f"Test result stored in database with ID: {result_id}")

    # Forward results to another server on localhost:8200
    try:
        # replacing the actual sending of results with a notification ping to 
        # instruct Flask server to fetch the latest results from the database
        response = requests.post(FLASK_SERVER_NEW_RESULT_PING_URL, json={"db_id": result_id})
        # response = requests.post(FLASK_SERVER_RESULT_URL,
                                #  json=data.model_dump())

        log.info(f"Forwarded to localhost:8200 - status: {response.reason}, response: {response.text}")
    except Exception as e:
        log.error(f"Error forwarding to localhost:8200: {e}")
        return {
            "message": "Result received",
            "status": status_text,
            "database_id": result_id
        }

    return {
        "message": "Result received and stored",
        "status": status_text,
        "database_id": result_id
    }


# GET endpoints for retrieving test results

@app.get("/results/{result_id}")
async def get_result(result_id: int):
    """Retrieve a specific test result by ID."""
    result = db_handler.get_result_by_id(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Test result not found")
    return result


@app.get("/results/test-name/{test_name}")
async def get_results_by_name(test_name: str):
    """Retrieve all results for a specific test name."""
    results = db_handler.get_results_by_test_name(test_name)
    return {
        "test_name": test_name,
        "count": len(results),
        "results": results
    }


@app.get("/results")
async def get_all_results(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    """Retrieve all test results with pagination."""
    results = db_handler.get_all_results(limit=limit, offset=offset)
    return {
        "limit": limit,
        "offset": offset,
        "count": len(results),
        "results": results
    }


@app.get("/results/status/{status_filter}")
async def get_results_by_status(
    status_filter: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Retrieve test results filtered by status.
    status_filter: 'passed' for successful tests, 'failed' for failed tests
    """
    if status_filter.lower() == "passed":
        success = True
    elif status_filter.lower() == "failed":
        success = False
    else:
        raise HTTPException(status_code=400, detail="status_filter must be 'passed' or 'failed'")

    results = db_handler.get_results_by_status(success=success, limit=limit, offset=offset)
    return {
        "status_filter": status_filter,
        "limit": limit,
        "offset": offset,
        "count": len(results),
        "results": results
    }


@app.get("/statistics")
async def get_statistics():
    """Get overall test statistics."""
    stats = db_handler.get_test_statistics()
    return stats


@app.delete("/results/{result_id}")
async def delete_result(result_id: int):
    """Delete a specific test result by ID."""
    success = db_handler.delete_result_by_id(result_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test result not found or already deleted")
    return {"message": f"Test result {result_id} deleted successfully"}


@app.post("/results/clear")
async def clear_all_results():
    """
    Clear all test results from the database.
    WARNING: This action cannot be undone!
    """
    log.warning("Clear all test results requested!")
    success = db_handler.clear_all_results()
    if success:
        return {"message": "All test results cleared successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear test results")
