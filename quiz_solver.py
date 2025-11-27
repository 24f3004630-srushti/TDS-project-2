from utils.browser import BrowserAutomation
from utils.openai_helper import OpenAIHelper
from utils.data_processor import DataProcessor
import requests
import time
import logging
import re
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class QuizSolver:
    def __init__(self, api_key):
        self.browser = BrowserAutomation()
        self.openai = OpenAIHelper(api_key)
        self.data_processor = DataProcessor()
        self.max_retries = 2
    
    def extract_quiz_info(self, html_content: str, text_content: str) -> Dict[str, Any]:
        """Extract question and submit URL from quiz page"""
        # Try multiple patterns for submit URL
        patterns = [
            r'Post your answer to (https?://[^\s<]+)',
            r'submit.*?(https?://[^\s<"\']+/submit[^\s<"\']*)',
            r'POST.*?(https?://[^\s<"\']+)',
        ]
        
        submit_url = None
        for pattern in patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                submit_url = match.group(1)
                break
        
        # Extract file download links with multiple extensions
        file_links = re.findall(
            r'href="(https?://[^"]+\.(?:pdf|csv|xlsx?|json|zip|txt|png|jpe?g))"',
            html_content,
            re.IGNORECASE
        )
        
        return {
            'question': text_content,
            'submit_url': submit_url,
            'file_links': [link[0] if isinstance(link, tuple) else link for link in file_links],
            'html': html_content
        }
    
    def solve_quiz_chain(self, initial_url: str, email: str, secret: str):
        """Solve quiz chain with timeout and retry logic"""
        start_time = time.time()
        current_url = initial_url
        max_iterations = 15
        retry_count = 0
        
        for iteration in range(max_iterations):
            # Check timeout (3 minutes = 180 seconds)
            elapsed = time.time() - start_time
            if elapsed > 175:  # 5 second buffer
                logger.warning(f"Approaching timeout after {elapsed:.1f}s, stopping")
                break
            
            try:
                logger.info(f"[{elapsed:.1f}s] Solving quiz {iteration + 1}: {current_url}")
                
                # Fetch quiz page with retry
                html, text = self.fetch_with_retry(current_url)
                quiz_info = self.extract_quiz_info(html, text)
                
                if not quiz_info['submit_url']:
                    logger.error("No submit URL found in quiz page")
                    logger.debug(f"Page content: {text[:500]}")
                    break
                
                logger.info(f"Submit URL: {quiz_info['submit_url']}")
                
                # Download any files mentioned
                files_data = {}
                for file_url in quiz_info['file_links']:
                    try:
                        logger.info(f"Downloading file: {file_url}")
                        files_data[file_url] = self.data_processor.download_file(file_url)
                    except Exception as e:
                        logger.error(f"Error downloading {file_url}: {e}")
                
                # Solve with OpenAI with enhanced context
                answer = self.openai.solve_question(
                    quiz_info['question'],
                    files_data,
                    quiz_info.get('html', '')
                )
                
                logger.info(f"Generated answer: {answer}")
                
                # Submit answer
                response = self.submit_answer(
                    quiz_info['submit_url'],
                    email,
                    secret,
                    current_url,
                    answer
                )
                
                logger.info(f"Submission response: {response}")
                
                # Check if correct and get next URL
                if response.get('correct'):
                    logger.info("✓ Answer correct!")
                    retry_count = 0  # Reset retry count
                    if 'url' in response and response['url']:
                        current_url = response['url']
                        logger.info(f"Moving to next quiz: {current_url}")
                    else:
                        logger.info("🎉 Quiz chain completed!")
                        break
                else:
                    reason = response.get('reason', 'Unknown reason')
                    logger.warning(f"✗ Answer incorrect: {reason}")
                    
                    # Check if we should retry or move on
                    if 'url' in response and response['url']:
                        # New URL provided, move to next question
                        current_url = response['url']
                        retry_count = 0
                        logger.info(f"Skipping to next quiz: {current_url}")
                    elif retry_count < self.max_retries:
                        # Retry same question with different approach
                        retry_count += 1
                        logger.info(f"Retrying same question (attempt {retry_count + 1})")
                        continue
                    else:
                        logger.error(f"Max retries reached, stopping")
                        break
                        
            except Exception as e:
                logger.error(f"Error solving quiz: {str(e)}", exc_info=True)
                retry_count += 1
                if retry_count >= self.max_retries:
                    break
                time.sleep(2)
        
        total_time = time.time() - start_time
        logger.info(f"Quiz solving completed in {total_time:.1f} seconds")
    
    def fetch_with_retry(self, url: str, max_attempts: int = 3):
        """Fetch page with retry logic"""
        for attempt in range(max_attempts):
            try:
                return self.browser.fetch_page(url)
            except Exception as e:
                logger.warning(f"Fetch attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    raise
                time.sleep(1)
    
    def submit_answer(self, url: str, email: str, secret: str, quiz_url: str, answer: Any) -> Dict:
        """Submit answer to the endpoint with retry"""
        payload = {
            "email": email,
            "secret": secret,
            "url": quiz_url,
            "answer": answer
        }
        
        logger.debug(f"Submitting payload: {json.dumps(payload, indent=2)}")
        
        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Submit attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    return {"correct": False, "reason": f"Submission failed: {str(e)}"}
                time.sleep(2)