from wfbot.config import LogWatchConfig
from wfbot.logwatch import LogWatcher


def watcher_for(path, **overrides):
    config = LogWatchConfig(path=str(path), **overrides)
    return LogWatcher(config)


def append(path, *lines):
    with open(path, "a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")


def test_reads_only_new_lines(tmp_path):
    log = tmp_path / "EE.log"
    append(log, "old line")
    watcher = watcher_for(log)
    watcher.seek_to_end()
    assert watcher.read_new_lines() == []

    append(log, "new line", "another")
    assert watcher.read_new_lines() == ["new line", "another"]
    assert watcher.read_new_lines() == []


def test_detects_truncation(tmp_path):
    log = tmp_path / "EE.log"
    append(log, "a" * 200)
    watcher = watcher_for(log)
    watcher.seek_to_end()

    # Warframe restarted and rewrote the log in place.
    log.write_text("fresh start\n", encoding="utf-8")
    assert watcher.read_new_lines() == ["fresh start"]


def test_missing_file_is_not_an_error(tmp_path):
    watcher = watcher_for(tmp_path / "nope.log")
    assert not watcher.available()
    assert watcher.read_new_lines() == []
    assert watcher.poll() == []


def test_whisper_pattern_extracts_the_user(tmp_path):
    log = tmp_path / "EE.log"
    log.write_text("", encoding="utf-8")
    watcher = watcher_for(
        log, whisper_patterns=[r"whisper from (?P<user>\S+)"], trade_patterns=[]
    )
    watcher.seek_to_end()
    append(log, "12.345 Script [Info]: whisper from BulletJumper: hi wtb loki prime")
    events = watcher.poll()
    assert len(events) == 1
    assert events[0].kind == "whisper"
    assert events[0].user == "BulletJumper"


def test_game_state_transitions(tmp_path):
    log = tmp_path / "EE.log"
    log.write_text("", encoding="utf-8")
    watcher = watcher_for(
        log,
        game_start_patterns=[r"Main game loop"],
        game_stop_patterns=[r"Game/Client shutdown"],
        whisper_patterns=[],
        trade_patterns=[],
    )
    watcher.seek_to_end()
    assert watcher.game_running is None

    append(log, "0.001 Sys [Info]: Main game loop started")
    watcher.poll()
    assert watcher.game_running is True

    append(log, "9999.9 Sys [Info]: Game/Client shutdown")
    watcher.poll()
    assert watcher.game_running is False


def test_invalid_pattern_is_ignored_not_fatal(tmp_path):
    log = tmp_path / "EE.log"
    log.write_text("", encoding="utf-8")
    watcher = watcher_for(log, whisper_patterns=[r"(unclosed", r"whisper from (?P<user>\S+)"])
    watcher.seek_to_end()
    append(log, "whisper from Tenno")
    assert watcher.poll()[0].user == "Tenno"


def test_undecodable_bytes_do_not_break_the_tail(tmp_path):
    log = tmp_path / "EE.log"
    log.write_bytes(b"")
    watcher = watcher_for(log, whisper_patterns=[r"whisper from (?P<user>\S+)"])
    watcher.seek_to_end()
    with open(log, "ab") as handle:
        handle.write(b"\xff\xfe garbage\nwhisper from Tenno\n")
    events = watcher.poll()
    assert [event.user for event in events] == ["Tenno"]
