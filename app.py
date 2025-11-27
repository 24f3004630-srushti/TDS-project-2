from flask import Flask, request, jsonify
from quiz_solver import QuizSolver
import logging
import threading
import time
import os

app = Flask(__name__)

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------- STATIC CREDENTIALS (TEMPORARY) ----------------
STUDENT_EMAIL = "24f3004630@ds.study.iitm.ac.in"
SECRET = "tds_secret"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY")

solver = QuizSolver(OPENAI_API_KEY)

# ---------------- LIMITS ----------------
MAX_RUNTIME = 170  # seconds

# ---------------- WORKER ----------------
def solve_chain_worker(start_url):
    start_time = time.time()
    current_url = start_url
    attempt = 0

    logger.info(f"Starting quiz chain at {current_url}")

    while current_url:
        if time.time() - start_time > MAX_RUNTIME:
            logger.error("Time limit exceeded. Stopping execution.")
            return

        attempt += 1
        logger.info(f"Attempt {attempt} on {current_url}")

        try:
            # Step 1: Solve current quiz page
            answer_payload, submit_url = solver.solve_one_quiz(current_url)

            if not submit_url:
                logger.error("Submit URL not found.")
                return

            # Step 2: Inject required fields
            answer_payload["email"] = STUDENT_EMAIL
            answer_payload["secret"] = SECRET
            answer_payload["url"] = current_url

            # Step 3: Enforce payload size < 1MB
            payload_size = len(str(answer_payload).encode("utf-8"))
            if payload_size > 1_000_000:
                logger.error("Payload exceeds 1MB limit.")
                return

            # Step 4: Submit answer
            response = solver.submit_answer(submit_url, answer_payload)

            if not response:
                logger.error("No response from submit endpoint.")
                return

            # Step 5: Handle response logic
            if response.get("correct") is True:
                logger.info("Answer is correct.")

                next_url = response.get("url")
                if next_url:
                    current_url = next_url
                    continue
                else:
                    logger.info("Quiz chain completed successfully.")
                    return
            else:
                logger.warning(f"Wrong answer: {response.get('reason')}")

                next_url = response.get("url")
                if next_url:
                    current_url = next_url
                    continue
                else:
                    logger.info("Retrying same quiz within time limit.")
                    continue

        except Exception as e:
            logger.exception(f"Fatal error in solver: {e}")
            return


# ---------------- MAIN API ----------------
@app.route("/solve", methods=["POST"])
def solve_quiz():
    try:
        # JSON validation
        if not request.is_json:
            return jsonify({"error": "Invalid JSON"}), 400

        data = request.json

        # Field validation
        if not all(k in data for k in ("email", "secret", "url")):
            return jsonify({"error": "Missing required fields"}), 400

        # Secret validation
        if data["secret"] != SECRET:
            return jsonify({"error": "Invalid secret"}), 403

        # Start background solver
        t = threading.Thread(
            target=solve_chain_worker,
            args=(data["url"],),
            daemon=True
        )
        t.start()

        return jsonify({
            "status": "accepted",
            "message": "Quiz solving started"
        }), 200

    except Exception as e:
        logger.exception("Unexpected API crash")
        return jsonify({"error": str(e)}), 500


# ---------------- HEALTH ----------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "LLM Quiz Solver",
        "status": "running",
        "endpoints": {
            "/solve": "POST",
            "/health": "GET"
        }
    }), 200


# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
