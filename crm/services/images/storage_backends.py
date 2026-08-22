from django.core.files.storage import FileSystemStorage


class NoPublicUrlFileSystemStorage(FileSystemStorage):
    """Filesystem-only storage that cannot manufacture a public URL."""

    @property
    def base_url(self):
        return None

    def url(self, name):
        raise NotImplementedError(
            "Public image delivery URLs are not available through Django storage."
        )
