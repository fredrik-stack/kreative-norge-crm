FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/lab/storage_pipeline:/lab/image_pipeline \
    DJANGO_SETTINGS_MODULE=test_settings \
    PHASE3B1_STATIC_ROOT=/lab/image_pipeline/static \
    PHASE3B2_S3_ENDPOINT=http://moto:5000 \
    PHASE3B2_LAB_ROOT=/tmp/phase3b2-storage-lab

WORKDIR /lab

COPY spikes/storage_pipeline/requirements.txt /lab/storage_pipeline/requirements.txt
RUN pip install --no-cache-dir -r /lab/storage_pipeline/requirements.txt

COPY spikes/storage_pipeline /lab/storage_pipeline
COPY spikes/image_pipeline/image_lab /lab/image_pipeline/image_lab
COPY spikes/image_pipeline/static /lab/image_pipeline/static

CMD ["python", "-m", "unittest", "discover", "-s", "/lab/storage_pipeline/tests", "-v"]
