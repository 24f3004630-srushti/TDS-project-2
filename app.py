from flask import Flask, request, jsonify
from quiz_solver import QuizSolver
import os
from dotenv import load_dotenv
import logging
import threading

load_dotenv()

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SECRET = os.getenv('QUIZ_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not SECRET or not OPENAI_API_KEY:
    raise ValueError("Missing required environment variables")

quiz_solver = QuizSolver(OPENAI_API_KEY)

@app.route('/solve', methods=['POST'])
def solve_quiz():
    """Main endpoint to receive and solve quiz"""
    try:
        # Validate JSON
        if not request.is_json:
            return jsonify({"error": "Invalid JSON"}), 400
        
        data = request.json
        
        # Validate required fields
        if not all(key in data for key in ['email', 'secret', 'url']):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Verify secret
        if data['secret'] != SECRET:
            return jsonify({"error": "Invalid secret"}), 403
        
        # Start quiz solving in background thread to return quickly
        logger.info(f"Received quiz request for {data['url']}")
        thread = threading.Thread(
            target=quiz_solver.solve_quiz_chain,
            args=(data['url'], data['email'], data['secret'])
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Quiz processing started"
        }), 200
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "service": "LLM Quiz Solver",
        "status": "running",
        "endpoints": {
            "/solve": "POST - Submit quiz URL",
            "/health": "GET - Health check"
        }
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)