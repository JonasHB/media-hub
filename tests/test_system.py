from mediahub import system


def test_reboot_requests_systemctl_without_force(monkeypatch):
    calls = []
    monkeypatch.setattr(system.subprocess, "Popen", lambda command, **kwargs: calls.append(command))
    assert system.SystemActions().reboot()
    assert calls == [["systemctl", "reboot"]]
