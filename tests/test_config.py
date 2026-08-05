import pytest

from wfbot import config as config_module
from wfbot.config import Config, load


def write_config(tmp_path, text):
    path = tmp_path / "wfbot.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_are_safe():
    config = Config()
    # Live trading must never be on by accident.
    assert config.trade.live is False
    assert config.logwatch.enabled is False
    assert config.api.requests_per_second <= 3.0


def test_load_overrides_sections(tmp_path, monkeypatch):
    monkeypatch.setenv("WFBOT_STATE_DIR", str(tmp_path / "state"))
    path = write_config(
        tmp_path,
        """
        [api]
        platform = "ps4"
        requests_per_second = 1.5

        [scan]
        budget = 2000
        min_margin = 0.4
        exclude_patterns = ["*riven*"]

        [trade]
        live = true
        ingame_name = "Tester"
        """,
    )
    config = load(path)
    assert config.api.platform == "ps4"
    assert config.api.requests_per_second == 1.5
    assert config.scan.budget == 2000
    assert config.scan.min_margin == 0.4
    assert config.scan.exclude_patterns == ["*riven*"]
    assert config.trade.live is True
    assert config.trade.ingame_name == "Tester"
    assert config.source_path == path


def test_integers_are_coerced_to_floats(tmp_path, monkeypatch):
    monkeypatch.setenv("WFBOT_STATE_DIR", str(tmp_path / "state"))
    path = write_config(tmp_path, "[scan]\nmin_volume = 8\n")
    config = load(path)
    assert isinstance(config.scan.min_volume, float)
    assert config.scan.min_volume == 8.0


def test_unknown_keys_are_rejected(tmp_path):
    path = write_config(tmp_path, "[scan]\nbudgett = 100\n")
    with pytest.raises(ValueError, match="unknown option 'scan.budgett'"):
        load(path)


def test_unknown_sections_are_rejected(tmp_path):
    path = write_config(tmp_path, "[nonsense]\nx = 1\n")
    with pytest.raises(ValueError, match="unknown config section"):
        load(path)


def test_missing_explicit_config_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "absent.toml")


def test_environment_wins_over_file(tmp_path, monkeypatch):
    monkeypatch.setenv("WFBOT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("WFBOT_PLATFORM", "xbox")
    monkeypatch.setenv("WFM_INGAME_NAME", "EnvName")
    path = write_config(tmp_path, '[api]\nplatform = "pc"\n[trade]\ningame_name = "FileName"\n')
    config = load(path)
    assert config.api.platform == "xbox"
    assert config.trade.ingame_name == "EnvName"


def test_state_dirs_are_created(tmp_path, monkeypatch):
    target = tmp_path / "state"
    monkeypatch.setenv("WFBOT_STATE_DIR", str(target))
    config = load(write_config(tmp_path, ""))
    assert config.cache_dir.is_dir()
    assert config.db_path.parent == target
    assert config.token_path.name == "token.json"


def test_default_ee_log_never_raises(monkeypatch):
    monkeypatch.setattr(config_module.os, "name", "posix")
    # Whatever the host looks like, this must return a path or None.
    assert config_module.default_ee_log() is None or config_module.default_ee_log().name == "EE.log"
