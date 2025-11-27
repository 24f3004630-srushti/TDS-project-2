import requests
import pandas as pd
from io import BytesIO
import PyPDF2

class DataProcessor:
    def download_file(self, url):
        """Download file from URL"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    
    def process_csv(self, data):
        """Process CSV data"""
        return pd.read_csv(BytesIO(data))
    
    def process_pdf(self, data):
        """Extract text from PDF"""
        pdf_reader = PyPDF2.PdfReader(BytesIO(data))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    
    def process_json(self, data):
        """Process JSON data"""
        import json
        return json.loads(data)
```

## 11. tests/test_endpoint.py

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_endpoint():
    """Test the quiz endpoint"""
    url = "http://localhost:5000/solve"
    
    payload = {
        "email": "test@example.com",
        "secret": os.getenv('QUIZ_SECRET'),
        "url": "https://tds-llm-analysis.s-anand.net/demo"
    }
    
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_endpoint()