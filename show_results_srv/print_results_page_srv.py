import os
import time
import requests
import threading
from queue import Queue
from flask import Flask, request, jsonify, render_template
from utils.my_logger import get_logger

log = get_logger(log_filename="results_server_webpage_FLASK.log")

# Initialize Flask application with explicit template folder
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

# Store results in memory (can be replaced with database)
results_store = []

# FastAPI server URL
FASTAPI_SERVER_URL = "http://localhost:8100"

# Thread-safe queue for pending result fetches
pending_results_queue = Queue()

# Flag to control background worker thread
worker_thread_stop_event = threading.Event()


def fetch_and_store_result(db_id: int) -> bool:
    """
    Fetch a result from FastAPI server and store it locally.

    Args:
        db_id: Database ID of the result to fetch

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        fetch_url = f"{FASTAPI_SERVER_URL}/results/{db_id}"
        log.debug(f"Worker thread: Fetching result from: {fetch_url}")

        response = requests.get(fetch_url, timeout=10)
        log.debug(f"Worker thread: Received response - Status {response.status_code}")

        if response.status_code == 200:
            result_data = response.json()
            log.info(f"Worker thread: Successfully fetched result for db_id {db_id}")

            # Store result in local results_store
            results_store.append(result_data)
            return True
        else:
            log.error(f"Worker thread: Failed to fetch result - Status {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        log.error(f"Worker thread: Timeout while fetching result for db_id {db_id}")
        return False
    except requests.exceptions.RequestException as e:
        log.error(f"Worker thread: Error communicating with FastAPI server: {str(e)}")
        return False
    except Exception as e:
        log.error(f"Worker thread: Unexpected error fetching result: {str(e)}")
        return False


def background_result_worker(check_interval: int = 2):
    """
    Background worker thread that periodically checks the queue for pending results
    and fetches them from the FastAPI server.

    Args:
        check_interval: Time in seconds between queue checks
    """
    log.info(f"Starting background result worker thread (check interval: {check_interval}s)")

    while not worker_thread_stop_event.is_set():
        try:
            # Check queue with timeout to allow graceful shutdown
            db_id = pending_results_queue.get(timeout=1)
            log.debug(f"Worker thread: Got db_id {db_id} from queue (queue size: {pending_results_queue.qsize()})")

            # Fetch and store the result
            fetch_and_store_result(db_id)

        except:
            # Queue timeout - this is expected, just continue
            pass

    log.info("Background result worker thread stopped")


def start_background_worker():
    """Start the background worker thread."""
    worker_thread = threading.Thread(
        target=background_result_worker,
        daemon=True,
        name="FlaskResultFetcher"
    )
    worker_thread.start()
    log.info("Background worker thread started")
    return worker_thread

@app.route('/alive', methods=['GET'])
def check_alive():
    """Health check endpoint to verify server is running."""
    return jsonify({
        "message": "FLASK Server is alive",
        "status": "SUCCESS"
    }), 200

@app.route('/new-result-ping', methods=['POST'])
def new_result_ping():
    """
    Endpoint to receive notification of new results from FastAPI server.
    Simply enqueues the db_id for the background worker thread to process.

    Expected JSON payload:
    {
        "db_id": "int"
    }
    """
    log.debug("Received new result ping from FASTAPI server.")
    try:
        data = request.get_json()
        db_id = data.get("db_id")
        log.debug(f"Received ping for db_id: {db_id}")

        if not db_id:
            return jsonify({
                "error": "Missing db_id in request",
                "status": "FAILED"
            }), 400

        # Enqueue the db_id for background processing
        pending_results_queue.put(db_id)
        log.info(f"Enqueued db_id {db_id} for result fetching (queue size: {pending_results_queue.qsize()})")

        return jsonify({
            "message": "Result notification received. Queued for processing.",
            "status": "SUCCESS",
            "db_id": db_id,
            "queue_size": pending_results_queue.qsize()
        }), 200

    except Exception as e:
        log.error(f"Error processing new result ping: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "FAILED"
        }), 500

@app.route('/result', methods=['POST'])
def receive_result():
    """
    Receive test results from remote servers.
    Expected JSON payload:
    {
        "test_name": "str",
        ...
    }
    """
    log.debug("====>(FLASK) Received POST request to /result endpoint")
    try:
        # Validate request has JSON content
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json",
                "status": "FAILED"
            }), 400

        # Get JSON data
        data = request.get_json()
        log.debug("Received POST request to /result endpoint with data: %s", data)

        # Validate required fields
        required_fields = ['test_name', 'success', 'text', 'start_time', 'runtime']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "status": "FAILED"
            }), 400

        # Create result record with start_time and runtime if provided
        result_record = {
            "test_name": data.get("test_name"),
            "success": data.get("success"),
            "text": data.get("text"),
            "start_time": data.get("start_time"),
            "runtime": data.get("runtime")
        }

        # Store result
        results_store.append(result_record)


        # Log the received result
        # status = "✅  SUCCESS" if data["success"] else "❌  FAILED"
        # log.info(f"==============> Received result: {data['test_name']} | {status}")
        # log.info(f"==============> Full payload: {result_record}")

        return jsonify({
            "message": "Result received and stored successfully.",
            "status": "SUCCESS",
            "result_id": len(results_store) - 1
        }), 200

    except Exception as e:
        log.error(f"Error processing result: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "FAILED"
        }), 500

@app.route('/dashboard', methods=['GET'])
def show_results_dashboard():

    # Display all test results in a dynamically generated HTML page.

    try:
        # below line was the old way of showing of the results page
        # now we use an html template to showcase the results page...
        # hope this works ... :)

        # Generate HTML with styles and result data
        # html_template = """
        # """

        # Calculate statistics
        total_tests = len(results_store)
        success_tests = sum(1 for r in results_store if r["success"])
        failed_tests = total_tests - success_tests
        pass_rate = round((success_tests / total_tests) * 100, 2) if total_tests > 0 else 0

        # Render HTML with results and statistics
        return render_template(
            "dashboard.html",
            results=results_store,
            total_tests=total_tests,
            success_tests=success_tests,
            failed_tests=failed_tests,
            pass_rate=pass_rate
        )

    except Exception as e:
        log.error(f"Error rendering dashboard: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "FAILED"
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "status": "FAILED"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    log.error(f"Internal server error: {str(error)}")
    return jsonify({
        "error": "Internal server error",
        "status": "FAILED"
    }), 500

if __name__ == '__main__':
    log.info("Starting Flask Results Server on localhost:8200")

    # Start background worker thread
    worker_thread = start_background_worker()

    try:
        app.run(
            host='localhost',
            port=8200,
            debug=False,
            threaded=True
        )
    finally:
        # Gracefully shutdown the worker thread
        log.info("Shutting down background worker thread...")
        worker_thread_stop_event.set()
        worker_thread.join(timeout=5)
        log.info("Flask Results Server stopped")











