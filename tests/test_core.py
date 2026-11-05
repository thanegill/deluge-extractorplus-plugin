import threading
import types

import deluge.component
import deluge.configmanager


def live_timers():
    return {t for t in threading.enumerate() if isinstance(t, threading.Timer)}


def test_init_starts_no_cleanup_timer(monkeypatch, tmp_path):
    deluge.configmanager.set_config_dir(str(tmp_path))
    rpc_server = types.SimpleNamespace(
        register_object=lambda *args: None,
        deregister_object=lambda *args: None,
    )
    monkeypatch.setattr(deluge.component, "get", lambda name: rpc_server)

    from extractorplus.core import Core

    timers_before = live_timers()
    Core("ExtractorPlus")
    assert not live_timers() - timers_before, "Core.__init__ left a cleanup timer running before enable()"
