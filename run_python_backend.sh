cd back
# Use the virtual environment created in Docker
export PATH="/opt/venv/bin:$PATH"
uvicorn main:app --host 0.0.0.0 --port 8000
