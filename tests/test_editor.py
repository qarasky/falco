import time
import tkinter as tk

import pytest

from editor import app, builder


@pytest.fixture
def window(monkeypatch):
    monkeypatch.setattr(app, "discover_stubs", lambda: {})
    monkeypatch.setattr(builder, "discover_stubs", lambda: {})
    try:
        probe = tk.Tk()
        probe.destroy()
    except tk.TclError as exc:
        pytest.skip(f"Tk display is unavailable: {exc}")
    try:
        root = app.FalcoEditor()
    except tk.TclError as exc:
        # Some hosted Windows Python installs lose Tcl initialization between
        # roots. Only skip this environment error; widget failures must fail.
        if "Can't find a usable init.tcl" in str(exc):
            pytest.skip(f"Tk installation is unavailable: {exc}")
        raise
    root.withdraw()
    yield root
    if not root._closing:
        root._on_close()


def test_name_default_tracks_launcher_name_but_preserves_custom_output(window):
    window.var_name.set("my-server")
    assert window.var_output.get().startswith("my-server")
    window.var_output.set("custom")
    window.var_name.set("another-server")
    assert window.var_output.get() == "custom"


def test_build_failure_restores_controls_and_shows_useful_error(window, tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr(app.messagebox, "showerror", lambda title, message, **kwargs: messages.append(message))
    window.var_host.set("127.0.0.1")
    window.var_user.set("user")
    window.var_directory.set(str(tmp_path))
    window._on_build()
    deadline = time.monotonic() + 3
    while window._building and time.monotonic() < deadline:
        window._drain_events()
        time.sleep(0.01)
    assert not window._building
    assert "disabled" not in window.build_button.state()
    assert "failed" in window.status.get().lower()
    assert messages and "stub" in messages[-1]


def test_close_with_queued_completion_is_safe(window):
    from editor.build_jobs import BuildEvent
    window._events.put(BuildEvent(kind="error", message="late worker result"))
    window._on_close()
    assert window._closing


def test_unresolvable_output_folder_is_reported_without_starting_build(window, monkeypatch):
    messages = []
    monkeypatch.setattr(app.messagebox, "showerror", lambda title, message, **kwargs: messages.append(message))
    window.var_host.set("127.0.0.1")
    window.var_user.set("user")
    window.var_directory.set("~falco-user-that-does-not-exist-9e8a1/output")
    def fail_expanduser(path):
        raise RuntimeError("Could not determine home directory")
    # Windows may resolve ~unknown-user under the current user's parent folder.
    monkeypatch.setattr(app.Path, "expanduser", fail_expanduser)
    window._on_build()
    assert messages and "folder" in messages[-1].lower()
    assert not window._building


def test_thread_start_failure_restores_build_controls(window, tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr(app.messagebox, "showerror", lambda title, message, **kwargs: messages.append(message))
    def fail_start(thread):
        raise RuntimeError("cannot start build worker")
    monkeypatch.setattr(app.threading.Thread, "start", fail_start)
    window.var_host.set("127.0.0.1")
    window.var_user.set("user")
    window.var_directory.set(str(tmp_path))
    window._on_build()
    assert not window._building
    assert "disabled" not in window.build_button.state()
    assert messages and "worker" in messages[-1]


def test_key_controls_only_appear_for_key_authentication(window):
    window.update_idletasks()
    assert not window.key_row.winfo_manager()
    assert "disabled" in window.key_entry.state()
    window.var_auth.set("private_key")
    window._auth_changed()
    assert window.key_row.winfo_manager() == "grid"
    assert "disabled" not in window.key_entry.state()
    window._set_building(True)
    assert "disabled" in window.key_entry.state()
    window._set_building(False)
    assert "disabled" not in window.key_entry.state()
    window.var_auth.set("password")
    window._auth_changed()
    assert not window.key_row.winfo_manager()


def test_details_are_collapsed_and_can_be_toggled(window):
    assert not window._details_visible
    assert not window.log.frame.winfo_manager()
    window._toggle_details()
    assert window._details_visible
    assert window.log.frame.winfo_manager() == "grid"
    window._toggle_details()
    assert not window.log.frame.winfo_manager()


def test_build_failure_reveals_details(window, monkeypatch):
    from editor.build_jobs import BuildEvent
    monkeypatch.setattr(app.messagebox, "showerror", lambda *args, **kwargs: None)
    window._events.put(BuildEvent(kind="error", message="Missing launcher stub"))
    window._drain_events()
    assert window._details_visible
    assert "Missing launcher stub" in window.log.get("1.0", "end")


def test_progress_only_visible_during_build(window):
    assert not window.progress.winfo_manager()
    window._set_building(True)
    assert window.progress.winfo_manager() == "grid"
    window._set_building(False)
    assert not window.progress.winfo_manager()


def test_editor_loads_its_icon(window):
    assert window._icon.width() == 64
    assert window._icon.height() == 64
