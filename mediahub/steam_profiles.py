"""Scoped AntiMicroX profiles using an existing, empty per-game AutoProfile.

AntiMicroX 3.1.4 caches its AutoProfile rules. It opens the selected profile
file when the watched window gets focus and the selected profile changes.
Stage before launch/focus, restore after Handover, and leave the resident
mapper, defaults, and all rules alone.
"""

import logging
import os
from pathlib import Path
import select
import stat
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET

from PySide6.QtCore import QSettings


log = logging.getLogger(__name__)
_SUFFIX = '.gamecontroller.amgp'
_LIMIT = 1024 * 1024


def _backup(target: Path) -> Path:
    return target.with_name(f'.{target.name}.mediahub-backup')


def _profile(path: Path) -> tuple[bytes, ET.Element]:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('profile must be a regular file, not a link')
    with path.open('rb') as stream:
        data = stream.read(_LIMIT + 1)
    if len(data) > _LIMIT:
        raise ValueError('profile too large')
    root = ET.fromstring(data)
    if root.tag != 'gamecontroller' or not (
        root.get('configversion', '').isdigit() and root.find('sets') is not None
    ):
        raise ValueError('not an AntiMicroX SDL gamecontroller profile')
    return data, root


def _empty(root: ET.Element) -> bool:
    return all(child.tag in {'profilename', 'sets'} for child in root) and all(
        child.tag == 'set' and all(tag.tag == 'name' for tag in child)
        for child in root.findall('sets/*')
    )


def _payload(root: ET.Element) -> bytes:
    # AntiMicroX gamecontroller XML uses the SDL button enum plus one;
    # Guide is zero-based button 5. Remove its binding in every set.
    for mapping in root.findall('sets/set'):
        for button in mapping.findall('button'):
            try:
                is_guide = int(button.get('index', '')) == 6
            except ValueError:
                is_guide = False
            if is_guide:
                mapping.remove(button)
    if not _empty(root) and not root.findall('.//slot'):
        raise ValueError('profile has no usable mappings')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


class SteamProfiles:
    def __init__(self, settings_path: Path | None = None):
        self.settings_path = Path(settings_path) if settings_path is not None else (
            Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
            / 'antimicrox' / 'antimicrox_settings.ini'
        )
        self._worker: subprocess.Popen | None = None

    def choices(self) -> list[tuple[str, str]]:
        """Return (basename, display name) pairs; UI adds None separately."""
        choices = []
        for path in self.settings_path.parent.glob(f'*{_SUFFIX}'):
            if _backup(path).exists():
                continue
            try:
                _, root = _profile(path)
                if not _empty(root):
                    _payload(root)
                    choices.append((path.name, (root.findtext('profilename') or '').strip()
                                    or path.name.removesuffix(_SUFFIX)))
            except (OSError, ValueError, ET.ParseError):
                continue
        return sorted(choices, key=lambda item: (item[1].casefold(), item[0]))

    def supports(self, window_class: str) -> bool:
        """Check if settings provide a dedicated, empty mapping for the game."""
        try:
            target = self._target(window_class)
            return not _backup(target).exists() and _empty(_profile(target)[1])
        except (OSError, ValueError, ET.ParseError):
            return False

    def _target(self, window_class: str) -> Path:
        cfg = QSettings(str(self.settings_path), QSettings.Format.IniFormat)
        cfg.sync()
        if cfg.status() != QSettings.Status.NoError or str(cfg.value('AutoProfiles/AutoProfilesActive')) != '1':
            raise ValueError('AntiMicroX AutoProfiles are not enabled')
        rules = []
        for i in range(1, len(cfg.allKeys()) + 1):
            key = f'AutoProfiles/AutoProfile{i}'
            fields = {field: cfg.value(key + field, '', type=str) for field in (
                'Active', 'UniqueID', 'GUID', 'WindowClass', 'Exe', 'WindowName', 'Profile',
            )}
            if not (fields['UniqueID'] or fields['GUID']) or not any(
                fields[f] for f in ('WindowClass', 'Exe', 'WindowName')
            ):
                break  # AntiMicroX stops at the first gap as well.
            if fields['Active'] == '1':
                rules.append((key, fields))

        def matches(wm_class):
            configured = window_class.strip().lower()
            wm_class = wm_class.lower()
            for index, char in enumerate(wm_class):
                if char != ' ':
                    continue
                instance, klass = wm_class[:index], wm_class[index + 1:]
                if configured in (instance, klass) or (
                    len(configured.split()) == 2 and configured in (wm_class, f'{klass} {instance}')
                ):
                    return True
            return False

        candidates = [(key, rule) for key, rule in rules if rule['WindowClass'] and matches(rule['WindowClass'])]
        if len(candidates) != 1 or any(not rule['WindowClass'] for _, rule in rules):
            raise ValueError('no unambiguous per-game AntiMicroX AutoProfile')
        key, rule = candidates[0]
        if rule['UniqueID'] != 'all' or rule['Exe'] or rule['WindowName']:
            raise ValueError('game AutoProfile must be class-only and apply to all controllers')
        target = Path(rule['Profile'])
        if (not target.is_absolute() or not target.name.endswith(_SUFFIX)
                or target.parent.resolve() != self.settings_path.parent.resolve()):
            raise ValueError('game AutoProfile must use a local gamecontroller profile')
        target = target.parent.resolve() / target.name
        for other_key in cfg.allKeys():
            if other_key == key + 'Profile' or (
                other_key.startswith('Controllers/') and not other_key.endswith('LastSelected')
            ):
                continue
            value = cfg.value(other_key)
            if isinstance(value, str) and value.endswith('.amgp') and Path(value).resolve() == target:
                raise ValueError('game profile is shared with another AntiMicroX rule')
        return target

    def activate(self, profile_id: str | None, window_class: str) -> bool:
        """Stage before launch; False means leave existing behavior alone."""
        if self._worker is not None or not profile_id:
            return False
        try:
            if Path(profile_id).name != profile_id or not profile_id.endswith(_SUFFIX):
                raise ValueError('invalid profile name')
            if not window_class.strip():
                raise ValueError('missing game window class')
            source = self.settings_path.parent / profile_id
            if _backup(source).exists():
                raise ValueError('selected profile is a temporary game mapping')
            _, selected = _profile(source)
            if _empty(selected):
                raise ValueError('selected profile is empty')
            data = _payload(selected)
            target = self._target(window_class)
            # Inherit a private temporary file for the payload; stdin is a
            # lifetime pipe, whose EOF also rolls back on a launcher crash.
            with tempfile.TemporaryFile() as payload:
                payload.write(data)
                payload.seek(0)
                self._worker = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), str(target), str(payload.fileno())],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, pass_fds=(payload.fileno(),),
                    start_new_session=True,
                )
            stdout = self._worker.stdout
            assert stdout is not None
            if select.select([stdout], [], [], 2)[0] and stdout.read(1) == b'1':
                return True
            raise ValueError('AntiMicroX profile could not be staged')
        except (OSError, ValueError, ET.ParseError) as error:
            self.restore()
            log.warning('Steam controller profile skipped: %s', error)
            return False

    def restore(self) -> None:
        """Idempotent. Call on Handover failure, close, and application quit."""
        worker, self._worker = self._worker, None
        if worker is not None:
            if worker.stdin is not None:
                worker.stdin.close()
            try:
                if worker.wait(timeout=2) != 0:
                    log.warning('Steam controller profile worker failed; check AntiMicroX profile backup')
            except subprocess.TimeoutExpired:
                # Killing this worker could strand the temporary mapping.
                log.warning('Steam controller profile rollback still pending')
            finally:
                if worker.stdout is not None:
                    worker.stdout.close()


def _lease(target: Path, payload_fd: int) -> None:
    with os.fdopen(payload_fd, 'rb') as payload:
        data = payload.read()
    backup = _backup(target)
    temp = None
    staged = None
    replaced = False
    owns_backup = False
    try:
        # Exclusive link both preserves the original inode and prevents overlap.
        os.link(target, backup, follow_symlinks=False)
        owns_backup = True
        original, root = _profile(backup)
        if not _empty(root):
            raise ValueError('game AutoProfile is not empty')
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
            temp = Path(handle.name)
            os.fchmod(handle.fileno(), stat.S_IMODE(backup.stat().st_mode))
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            staged = os.fstat(handle.fileno())
        if not target.samefile(backup) or target.read_bytes() != original:
            raise ValueError('game AutoProfile was changed during staging')
        if select.select([sys.stdin], [], [], 0)[0]:
            return
        os.replace(temp, target)
        replaced = True
        temp = None
        print('1', flush=True)
        sys.stdin.buffer.read(1)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        if owns_backup:
            if replaced and staged is not None:
                if target.is_file() and not target.is_symlink() and (
                    os.path.samestat(staged, target.stat()) and target.read_bytes() == data
                ):
                    os.replace(backup, target)
                else:
                    raise ValueError(f'profile changed externally; original preserved at {backup}')
            else:
                backup.unlink()


if __name__ == '__main__':
    try:
        _lease(Path(sys.argv[1]), int(sys.argv[2]))
    except (OSError, ValueError, ET.ParseError) as error:
        sys.exit(f'Steam controller profile worker: {error}')
