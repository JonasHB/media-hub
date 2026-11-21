import socket
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QCoreApplication

from mediahub.main import listen_for_controller_return


def test_local_controller_return(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    calls = []
    with TemporaryDirectory(dir=tmp_path.parent.parent) as runtime:
        server = listen_for_controller_return(app, runtime, lambda: calls.append("return"))
        try:
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(str(Path(runtime) / "media-hub-return.sock"))
                assert server.waitForNewConnection(500)
            assert calls == ["return"]
        finally:
            server.close()
