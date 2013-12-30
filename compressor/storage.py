from __future__ import unicode_literals
import errno
import gzip
import os
from datetime import datetime
import time

from django.core.cache import get_cache
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.functional import LazyObject, SimpleLazyObject
from cloudydict.django_storage import StorageFromSettings

from hashlib import md5
from compressor.conf import settings

storage_cache = get_cache(getattr(settings, 'COMPRESSOR_CACHE_NAME', 'default'))

class CompressorFileStorage(StorageFromSettings):
    """
    Standard file system storage for files handled by django-compressor.

    The defaults for ``location`` and ``base_url`` are ``COMPRESS_ROOT`` and
    ``COMPRESS_URL``.

    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.COMPRESS_ROOT
        if base_url is None:
            base_url = settings.COMPRESS_URL
        super(CompressorFileStorage, self).__init__(# location, base_url,
                                                    *args, **kwargs)

    def get_available_name(self, name):
        """
        Deletes the given file if it exists.
        """
        if self.exists(name):
            self.delete(name)
        return name

    def delete(self, name):
        """
        Handle deletion race condition present in Django prior to 1.4
        https://code.djangoproject.com/ticket/16108
        """
        try:
            super(CompressorFileStorage, self).delete(name)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        finally:
            storage_cache.delete('django_compressor:%s' % md5(name).hexdigest())

    def modified_time(self, name):
        mt = storage_cache.get('django_compressor:%s' % md5(name).hexdigest())
        if mt is None:
            mt = StorageFromSettings.modified_time(self, name)
            storage_cache.set('django_compressor:%s' % md5(name).hexdigest(), mt)
        return mt


compressor_file_storage = SimpleLazyObject(
    lambda: get_storage_class('compressor.storage.CompressorFileStorage')())


class GzipCompressorFileStorage(CompressorFileStorage):
    """
    The standard compressor file system storage that gzips storage files
    additionally to the usual files.
    """
    def save(self, filename, content):
        filename = super(GzipCompressorFileStorage, self).save(filename, content)
        orig_path = self.path(filename)
        compressed_path = '%s.gz' % orig_path

        f_in = open(orig_path, 'rb')
        f_out = open(compressed_path, 'wb')
        try:
            f_out = gzip.GzipFile(fileobj=f_out)
            f_out.write(f_in.read())
        finally:
            f_out.close()
            f_in.close()
            # Ensure the file timestamps match.
            # os.stat() returns nanosecond resolution on Linux, but os.utime()
            # only sets microsecond resolution.  Set times on both files to
            # ensure they are equal.
            stamp = time.time()
            os.utime(orig_path, (stamp, stamp))
            os.utime(compressed_path, (stamp, stamp))

        return filename


class DefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(settings.COMPRESS_STORAGE)()

default_storage = DefaultStorage()
