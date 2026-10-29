"""Static files: WhiteNoise's compressed files with content hashes in their names."""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class StaticStorage(CompressedManifestStaticFilesStorage):
    # js/route/main.js imports './map.js' and friends. Without this those imports keep the plain names, so
    # after a deploy a browser could combine a new main.js with old modules from its cache.
    support_js_module_import_aggregation = True
