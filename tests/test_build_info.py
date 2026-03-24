from importlib import reload
from unittest.mock import patch

import app.build_info as build_info_module


def test_get_build_info_reads_version_file_by_default():
    module = reload(build_info_module)
    module.get_build_info.cache_clear()

    with patch.dict("os.environ", {"APP_VERSION": "", "APP_GIT_SHA": ""}, clear=False):
        info = module.get_build_info()

    assert info.version == module.VERSION_FILE.read_text(encoding="utf-8").strip()
    assert info.git_sha == module.DEFAULT_GIT_SHA
    assert info.release == f"v{info.version}"


def test_get_build_info_prefers_environment_overrides():
    module = reload(build_info_module)
    module.get_build_info.cache_clear()

    with patch.dict("os.environ", {"APP_VERSION": "9.9.9", "APP_GIT_SHA": "deadbee"}, clear=False):
        info = module.get_build_info()

    assert info.version == "9.9.9"
    assert info.git_sha == "deadbee"
