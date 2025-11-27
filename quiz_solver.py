import time
import json
import base64
import logging
import re
import requests
from typing import Any, Dict, Tuple

from utils.browser import BrowserAutomation
from utils.openai_helper import OpenAIHelper
from utils.data_processor import DataProcessor

logger = logging.getLogger(__name__)


class QuizSolver:
    def __init__(self, api_key: str):
        self.browser = BrowserAutomation()   # Must execute JavaScript
        self.openai = OpenAIHelper(api_key)
        self.data_processor = DataProcessor()

    # ---------------------------------------------------------
    # MAIN METHOD USED BY app.py
    # ---------------------------------------------------------
    def solve_one_quiz(self, url: str) -> Tuple[Dict[str, Any], str]:
        """
        Returns:
        - answer_payload (dict with only the 'answer' field)
        - submit_url (str)
        """

        # 1. Load fully rendered page
        html, text = self.browser.fetch_page(url)

        # 2. Decode atob() base64 if present
        text = self._decode_atob_if_present(html, text)

        # 3. Extract submit URL
        submit_url = self._extract_submit_url(html, text)
        if not submit_url:
            raise RuntimeError("Submit URL not found in quiz page")

        # 4. Extract downloadable file links
        file_links = self._extract_file_links(html)

        # 5. Download files
        files_data = {}
        for link in file_links:
            try:
                files_data[link] = self.data_processor.download_file(link)
            except Exception as e:
                logger.warning(f"File download failed: {link} -> {e}")

        # 6. Ask OpenAI to solve the task
        answer = self.openai.solve_question(
            question=text,
            files=files_data,
            html=html
        )

        # 7. Build payload (app.py injects email, secret, url later)
        answer_payload = {
            "answer": answer
        }

        return answer_payload, submit_url

    # ---------------------------------------------------------
    # SUBMIT METHOD USED BY app.py
    # ---------------------------------------------------------
    def submit_answer(self, submit_url: str, payload: Dict[str, Any]) -> Dict:
        """
        Posts final answer JSON to quiz submit endpoint.
        """

        # Enforce < 1MB payload
        if len(json.dumps(payload).encode("utf-8")) > 1_000_000:
            raise ValueError("Submission payload exceeds 1MB limit")

        for attempt in range(3):
            try:
                response = requests.post(
                    submit_url,
                    json=payload,
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                logger.error(f"Submit attempt {attempt + 1} failed: {e}")
                time.sleep(2)

        return {"correct": False, "reason": "Submission failed after retries"}

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------
    def _decode_atob_if_present(self, html: str, text: str) -> str:
        """
        Detects and decodes atob(base64) if used in JS.
        """
        match = re.search(r'atob\(`([^`]*)`\)', html, re.DOTALL)
        if not match:
            return text

        try:
            decoded = base64.b64decode(match.group(1)).decode("utf-8", errors="ignore")
            return decoded
        except Exception as e:
            logger.warning(f"Base64 atob decoding failed: {e}")
            return text

    def _extract_submit_url(self, html: str, text: str) -> str:
        """
        Attempts to find submit URL using multiple safe strategies.
        """
        patterns = [
            r'Post your answer to (https?://[^\s<]+)',
            r'submit.*?(https?://[^\s<"\']+)',
            r'(https?://[^\s<"\']+/submit[^\s<"\']*)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        # Fallback: scan raw HTML
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_file_links(self, html: str):
        """
        Extracts common downloadable file types.
        """
        return re.findall(
            r'href="(https?://[^"]+\.(?:pdf|csv|xlsx?|json|zip|txt|png|jpe?g))"',
            html,
            re.IGNORECASE
        )
