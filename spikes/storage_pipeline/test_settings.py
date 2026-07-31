from __future__ import annotations

import os
from pathlib import Path


LAB_ROOT = Path(os.environ.get("PHASE3B2_LAB_ROOT", "/tmp/phase3b2-storage-lab"))
S3_ENDPOINT = os.environ.get("PHASE3B2_S3_ENDPOINT", "http://localhost:5000")
AWS_ACCESS_KEY_ID = os.environ.get("PHASE3B2_ACCESS_KEY", "phase3b2-test")
AWS_SECRET_ACCESS_KEY = os.environ.get("PHASE3B2_SECRET_KEY", "phase3b2-test")
AWS_REGION = os.environ.get("PHASE3B2_REGION", "us-east-1")
PRIVATE_BUCKET = os.environ.get("PHASE3B2_PRIVATE_BUCKET", "phase3b2-private")
PUBLIC_BUCKET = os.environ.get("PHASE3B2_PUBLIC_BUCKET", "phase3b2-public")

SECRET_KEY = "phase3b2-isolated-lab-only"
DEBUG = False
USE_TZ = True
INSTALLED_APPS = ["django.contrib.staticfiles"]
STATIC_URL = "/static/"
STATIC_ROOT = LAB_ROOT / "staticfiles"

# STORAGES replaces Django's whole default dictionary. The sentinel depends on
# all four aliases being declared here; this file is never imported by config/.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": LAB_ROOT / "default-files",
            "base_url": "/lab-default/",
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "image_originals_private": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "bucket_name": PRIVATE_BUCKET,
            "endpoint_url": S3_ENDPOINT,
            "region_name": AWS_REGION,
            "addressing_style": "path",
            "querystring_auth": True,
            "default_acl": None,
            "file_overwrite": False,
            "object_parameters": {"CacheControl": "private, no-store"},
        },
    },
    "image_renditions_public": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "bucket_name": PUBLIC_BUCKET,
            "endpoint_url": S3_ENDPOINT,
            "region_name": AWS_REGION,
            "addressing_style": "path",
            "querystring_auth": False,
            "default_acl": None,
            "file_overwrite": False,
            "object_parameters": {
                "CacheControl": "public, max-age=31536000, immutable",
            },
        },
    },
}
