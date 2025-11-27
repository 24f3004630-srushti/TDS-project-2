'''
# Detailed Setup Guide

## Local Development

1. **Install Python 3.9+**

2. **Install Chrome/Chromium**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install chromium-browser
   
   # macOS
   brew install --cask google-chrome
   ```

3. **Clone and Setup**
   ```bash
   git clone https://github.com/YOUR_USERNAME/llm-quiz-solver.git
   cd llm-quiz-solver
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

5. **Run**
   ```bash
   python app.py
   ```

## Deployment (Render)

1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect your repository
4. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add environment variables:
   - `QUIZ_SECRET`
   - `ANTHROPIC_API_KEY`
6. Deploy!

## Troubleshooting

**Chrome driver issues:**
```bash
pip install --upgrade webdriver-manager
```

**Port already in use:**
```bash
# Change PORT in .env
PORT=8000
'''