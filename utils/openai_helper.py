from openai import OpenAI
import json
import base64
import logging

logger = logging.getLogger(__name__)

class OpenAIHelper:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        # Use the best model for data analysis
        self.model = "gpt-4-turbo-preview"
    
    def solve_question(self, question, files_data=None, html_context=None):
        """Use OpenAI GPT to solve the quiz question with enhanced context"""
        
        # Build comprehensive prompt
        prompt_parts = [
            "You are a data analysis expert solving a quiz. Be precise and concise.",
            "",
            "Question:",
            question,
            ""
        ]
        
        # Add file information
        if files_data:
            prompt_parts.append("Available files:")
            for url, data in files_data.items():
                file_type = url.split('.')[-1].upper()
                prompt_parts.append(f"- {url} ({file_type}, {len(data)} bytes)")
            prompt_parts.append("")
        
        # Add parsing instructions
        prompt_parts.extend([
            "Critical Instructions:",
            "1. Parse the question carefully to understand what's being asked",
            "2. If files need to be analyzed, describe what analysis is needed",
            "3. Return ONLY the final answer in the exact format requested",
            "4. For numbers: return just the number without any text (e.g., 12345)",
            "5. For text: return the exact text without quotes or extra formatting",
            "6. For boolean: return exactly 'true' or 'false' (lowercase)",
            "7. For JSON objects: return valid JSON only",
            "8. For base64 images: return the complete data URI",
            "",
            "Answer (with NO explanation, just the answer):"
        ])
        
        prompt = "\n".join(prompt_parts)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data analyst. Return only the requested answer without explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            answer_text = response.choices[0].message.content.strip()
            logger.info(f"Raw GPT response: {answer_text[:200]}")
            
            return self.parse_answer(answer_text)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def parse_answer(self, answer_text):
        """Parse the answer into appropriate format"""
        # Remove common wrapper text
        answer_text = answer_text.strip()
        
        # Remove markdown code blocks if present
        if answer_text.startswith('```'):
            lines = answer_text.split('\n')
            answer_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else answer_text
        
        # Try to parse as JSON
        if (answer_text.startswith('{') or answer_text.startswith('[')) and \
           (answer_text.endswith('}') or answer_text.endswith(']')):
            try:
                return json.loads(answer_text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed: {e}")
        
        # Try to parse as boolean
        if answer_text.lower() in ['true', 'false']:
            return answer_text.lower() == 'true'
        
        # Try to parse as number
        try:
            # Handle numbers with commas
            clean_num = answer_text.replace(',', '').strip()
            if '.' in clean_num:
                return float(clean_num)
            return int(clean_num)
        except ValueError:
            pass
        
        # Return as string, removing quotes if present
        if (answer_text.startswith('"') and answer_text.endswith('"')) or \
           (answer_text.startswith("'") and answer_text.endswith("'")):
            return answer_text[1:-1]
        
        return answer_text