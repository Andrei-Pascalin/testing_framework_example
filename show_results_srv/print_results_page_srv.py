from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from utils.my_logger import get_logger

log = get_logger()

# Initialize Flask application
app = Flask(__name__)

# Store results in memory (can be replaced with database)
results_store = []

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
 
    try:
        # Validate request has JSON content
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json",
                "status": "FAILED"
            }), 400

        # Get JSON data
        data = request.get_json()

        # Validate required fields
        required_fields = ['test_name', 'success', 'text']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "status": "FAILED"
            }), 400

        # Create result record with timestamp
        result_record = {
            "timestamp": datetime.now().isoformat(),
            "test_name": data.get("test_name"),
            "success": data.get("success"),
            "text": data.get("text")
        }

        # Store result
        results_store.append(result_record)
        

        # Log the received result
        status = "✅  SUCCESS" if data["success"] else "❌  FAILED"
        log.info(f"Received result: {data['test_name']} | {status}")
        log.debug(f"Full payload: {result_record}")

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
        # Generate HTML with styles and result data
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Test Results Dashboard</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }

                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }

                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                }

                .header {
                    background: white;
                    padding: 30px;
                    border-radius: 8px 8px 0 0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    margin-bottom: 0px;
                }
                .header h1 {
                    color: #333;
                    margin-bottom: 10px;
                }

                .header p {
                    color: #678;
                    font-size: 14px;
                }

                .stats {
                    display: flex;
                    gap: 20px;
                    margin-top: 20px;
                    flex-wrap: wrap;
                }

                .stat-box {
                    flex: 1;
                    min-width: 150px;
                    background: #f5f5f5;
                    padding: 15px;
                    border-radius: 5px;
                    text-align: center;
                }

                .stat-box h3 {
                    color: #667eea;
                    font-size: 18px;
                }
                
                .results-container {
                    background: white;
                    padding: 20px;
                    border-radius: 0 0 8px 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .result-item {
                    border-left: 4px solid #ddd;
                    padding: 15px 0;
                    margin-bottom: 15px;
                    background: #f9f9f9;
                    border-radius: 5px;
                    transition: all 0.3s ease;
                }
                
                .result-item.hover {
                    background: #f0f0f0;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .result-item.success {
                    border-left-color: #4caf50;
                    background: #f1f8f6;
                }
                .result-item.failed {
                    border-left-color: #f44336;
                    background: #fef5f5;
                }
                .result-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .result-name {
                    font-weight: bold;
                    color: #333;
                    font-size: 16px;
                }
                .result-status {
                    padding: 5px 10px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                }
                .result-status.success {
                    background: #4caf50;
                    color: white;
                }
                .result-status.failed {
                    background: #f44336;
                    color: white;
                }
                .result-timestamp {
                    color: #999;
                    font-size: 12px;
                    margin-bottom: 10px;
                }
                .result-text {
                    color: #555;
                    font-size: 14px;
                    margin-top: 10px;
                    padding: 10px;
                    background: white;
                    border-radius: 5px;
                    border-left: 4px solid #667eea;
                }
                .empty-state {
                    text-align: center;
                    padding: 40px 20px;
                    color: #999;
                }
                .empty-state svg {
                    width: 80px;
                    height: 80px;
                    margin-bottom: 20px;
                    opacity: 0.5;
                }
                .refresh-btn {
                    display: inline-block;
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background 0.3s ease;
                }
                .refresh-btn:hover {
                    background: #5a67d8;
                }
                </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Test Results Dashboard</h1>
                    <p>Overview of all test results received from remote servers.</p>
                    <div class="stats">
                        <div class="stat-box">
                            <h3>{{ total_tests }}</h3>
                            <p>Total Tests</p>
                        </div>
                        <div class="stat-box">
                        <h3 style="color: #4caf50;">{{ success_tests }}</h3>
                            <p>Passed Tests</p>
                        </div>
                        <div class="stat-box">
                            <h3 style="color: #f44336;">{{ failed_tests }}</h3>
                            <p>Failed Tests</p>
                        </div>
                        {% if total_tests > 0 %}
                            <div class="stat-box">
                                <h3 style="color: #667eea;">{{ pass_rate }}%</h3>
                                <p>Pass Rate</p>
                            </div>
                        {% endif %}
                    </div>
                </div>
                <div class="results-container">
                    {% if results %}
                    <h2 style="margin-bottom: 20px; color: #333;">Test Results</h2>
                    {% for result in results %}
                    <div class="result-item {% if result.success %}success{% else %}failed{% endif %}">
                        <div class="result-header">
                            <span class="result-name">#{{ loop.index }}. {{ result.test_name }}</span>
                            <span class="result-status {% if result.success %}success{% else %}failed{% endif %}">   
                                {% if result.success %}
                                    ✅ SUCCESS
                                {% else %}
                                    ❌ FAILED
                                {% endif %}
                            </span>
                        </div>
                        <div class="result-timestamp">{{ result.timestamp }}</div>
                        <div class="result-text">{{ result.text }}</div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <h2>No Test Results Yet</h2>
                        <p>Waiting for test results to be received from remote servers.</p>
                        <p style="font-size: 12px; color: #666;">Tip: Run some tests to see results appear here.</p>
                    </div>
                {% endif %}
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <button class="refresh-btn" onclick="location.reload()">  --Refresh--  </button>
            </div>
        </body>
        </html>
        """
        # Calculate statistics
        total_tests = len(results_store)
        success_tests = sum(1 for r in results_store if r["success"])
        failed_tests = total_tests - success_tests
        pass_rate = round((success_tests / total_tests) * 100, 2) if total_tests > 0 else 0

        # Render HTML with results and statistics
        return render_template_string(
            html_template,
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
        
        
        
        
        
        
        
        
        
        
        
        