FROM python:3.12-slim

WORKDIR /lab

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY image_lab ./image_lab
COPY tests ./tests
COPY run_lab.py .

ENV PYTHONPATH=/lab

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
