from __future__ import annotations

import logging
import os
import shutil
import subprocess

from PySide6.QtCore import QCoreApplication, QObject, Slot

log = logging.getLogger(__name__)


def _run(command: list[str]) -> bool:
    log.info("system: %s", " ".join(command))
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as error:
        log.error("system: kunde inte köra %s: %s", command[0], error)
        return False
    return True


class SystemActions(QObject):
    @Slot(result=bool)
    def suspend(self) -> bool:
        return _run(["systemctl", "suspend"])

    @Slot(result=bool)
    def logout(self) -> bool:
        session = os.environ.get("XDG_SESSION_ID")
        if session and shutil.which("loginctl"):
            return _run(["loginctl", "terminate-session", session])
        return _run(["mate-session-save", "--logout"])

    @Slot(result=bool)
    def poweroff(self) -> bool:
        return _run(["systemctl", "poweroff"])

    @Slot()
    def quit(self) -> None:
        QCoreApplication.quit()
