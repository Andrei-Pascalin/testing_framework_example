from flask import Flask, request, jsonify, render_template_string, render_template
from utils.my_logger import get_logger

log = get_logger(log_filename="results_server_webpage_FLASK.log")

# Initialize Flask application
app = Flask(__name__)

# Store results in memory (can be replaced with database)
results_store = []

@app.route('/alive', methods=['GET'])
def check_alive():
    """Health check endpoint to verify server is running."""
    return jsonify({
        "message": "FLASK Server is alive",
        "status": "SUCCESS"
    }), 200

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
        return render_template_string(
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
    app.run(
        host='localhost',
        port=8200,
        debug=False,
        threaded=True
    )











