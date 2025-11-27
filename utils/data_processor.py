import requests
import pandas as pd
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
            text += page.extract_text() or ''
        return text
    
    def process_json(self, data):
        """Process JSON data"""
        import json
        return json.loads(data)