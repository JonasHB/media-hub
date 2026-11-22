from select import select
import subprocess
import sys
import time
from xml.etree import ElementTree as ET

import pytest

from mediahub.steam_profiles import SteamProfiles


def profile(name, buttons=''):
    return (f'<gamecontroller configversion="19"><profilename>{name}</profilename>'
            f'<sets><set index="1">{buttons}</set></sets></gamecontroller>').encode()


@pytest.fixture
def setup(tmp_path):
    empty = tmp_path / 'game.gamecontroller.amgp'
    empty.write_bytes(profile('Native'))
    (tmp_path / 'example.gamecontroller.amgp').write_bytes(profile('Example', '<button index="1"><slots><slot/></slots></button>'))
    settings = tmp_path / 'antimicrox_settings.ini'
    settings.write_text('[AutoProfiles]\nAutoProfilesActive=1\nAutoProfile1Active=1\n'
                        f'AutoProfile1Profile={empty}\nAutoProfile1UniqueID=all\n'
                        'AutoProfile1WindowClass=Game Game\n')
    return settings, empty


def test_named_profile_replaces_only_game_specific_empty_profile(setup):
    settings, empty = setup
    original = empty.read_bytes()
    original_settings = settings.read_bytes()
    mapper = SteamProfiles(settings)
    assert mapper.activate('example.gamecontroller.amgp', 'Game Game')
    try:
        assert b'Example' in empty.read_bytes()
        assert settings.read_bytes() == original_settings
        assert mapper.choices() == [('example.gamecontroller.amgp', 'Example')]
    finally:
        mapper.restore()
    assert empty.read_bytes() == original


def test_catalog_omits_empty_bad_and_linked_profiles(setup):
    settings, empty = setup
    (empty.parent / 'bad.gamecontroller.amgp').write_text('not XML')
    (empty.parent / 'linked.gamecontroller.amgp').symlink_to('example.gamecontroller.amgp')
    assert SteamProfiles(settings).choices() == [('example.gamecontroller.amgp', 'Example')]


def test_none_preserves_existing_game_and_defaults(setup):
    settings, empty = setup
    original = empty.read_bytes()
    mapper = SteamProfiles(settings)
    assert not mapper.activate(None, 'Game')
    mapper.restore()
    assert empty.read_bytes() == original


def test_shared_profile_is_not_changed(setup):
    settings, empty = setup
    original = empty.read_bytes()
    with settings.open('a') as stream:
        stream.write(f'\n[DefaultAutoProfileAll]\nActive=1\nProfile={empty}\n')
    assert not SteamProfiles(settings).activate('example.gamecontroller.amgp', 'Game')
    assert empty.read_bytes() == original


def test_case_insensitive_handover_class_is_supported(setup):
    settings, _ = setup
    assert SteamProfiles(settings).supports('game')


def test_guide_is_reserved_in_staged_profile(setup):
    settings, empty = setup
    source = empty.parent / 'example.gamecontroller.amgp'
    source.write_bytes(profile('Example', '<button index="6"><slot/></button><button index="1"><slot/></button>'))
    original = source.read_bytes()
    mapper = SteamProfiles(settings)
    assert mapper.activate(source.name, 'Game')
    try:
        assert [b.get('index') for b in ET.parse(empty).findall('.//button')] == ['1']
        assert source.read_bytes() == original
    finally:
        mapper.restore()


def test_launcher_death_rolls_back_lease(setup):
    settings, empty = setup
    original = empty.read_bytes()
    proc = subprocess.Popen([sys.executable, '-c', '''
import sys
import time
from pathlib import Path
from mediahub.steam_profiles import SteamProfiles
mapper = SteamProfiles(Path(sys.argv[1]))
assert mapper.activate('example.gamecontroller.amgp', 'Game')
print('staged', flush=True)
time.sleep(20)
''', str(settings)], stdout=subprocess.PIPE)
    assert proc.stdout is not None
    try:
        assert select([proc.stdout], [], [], 5)[0]
        assert proc.stdout.readline().strip() == b'staged'
        assert empty.read_bytes() != original
    finally:
        proc.kill()
        proc.wait(timeout=3)
        proc.stdout.close()
    deadline = time.monotonic() + 3
    while empty.read_bytes() != original and time.monotonic() < deadline:
        time.sleep(.02)
    assert empty.read_bytes() == original
    assert not list(empty.parent.glob('.*.mediahub-backup'))
