import pytest


@pytest.fixture(autouse=True)
def temporary_media_root(settings, tmp_path):
    """
    Directs media storage to a temporary directory during automated tests,
    preventing test files from cluttering the project media/ directory.
    """
    settings.MEDIA_ROOT = tmp_path
