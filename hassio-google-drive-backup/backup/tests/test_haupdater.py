import pytest
from ..haupdater import HaUpdater
from ..globalinfo import GlobalInfo
from .faketime import FakeTime
from ..logbase import LogBase

STALE_ATTRIBUTES = {
    "friendly_name": "Snapshots Stale"
}


@pytest.mark.asyncio
async def test_init(updater: HaUpdater, global_info, server):
    await updater.update()
    assert not updater._stale()
    assert updater._state() == "waiting"
    verifyEntity(server, "binary_sensor.snapshots_stale", False, STALE_ATTRIBUTES)
    verifyEntity(server, "sensor.snapshot_backup", "waiting", {
        'friendly_name': 'Snapshot State',
        'last_snapshot': 'Never',
        'snapshots': [],
        'snapshots_in_google_drive': 0,
        'snapshots_in_hassio': 0
    })
    assert server.getNotification() is None

    global_info.success()
    assert not updater._stale()
    assert updater._state() == "backed_up"


@pytest.mark.asyncio
async def test_init_failure(updater: HaUpdater, global_info: GlobalInfo, time: FakeTime, server):
    await updater.update()
    assert not updater._stale()
    assert updater._state() == "waiting"

    global_info.failed(Exception())
    assert not updater._stale()
    assert updater._state() == "backed_up"
    assert server.getNotification() is None

    time.advanceDay()
    assert updater._stale()
    assert updater._state() == "error"
    await updater.update()
    assert server.getNotification() == {
        'message': 'The add-on is having trouble backing up your snapshots and needs attention.  Please visit the add-on status page for details.',
        'title': 'Hass.io Google Drive Backup is Having Trouble',
        'notification_id': 'backup_broken'
    }


@pytest.mark.asyncio
async def test_failure_backoff_502(updater: HaUpdater, server, time: FakeTime):
    server.setHomeAssistantError(502)
    for x in range(9):
        await updater.update()
    assert time.sleeps == [60, 120, 240, 300, 300, 300, 300, 300, 300]

    server.setHomeAssistantError(None)
    await updater.update()
    assert time.sleeps == [60, 120, 240, 300, 300, 300, 300, 300, 300]


@pytest.mark.asyncio
async def test_failure_backoff_510(updater: HaUpdater, server, time: FakeTime):
    server.setHomeAssistantError(510)
    for x in range(9):
        await updater.update()
    assert time.sleeps == [60, 120, 240, 300, 300, 300, 300, 300, 300]

    server.setHomeAssistantError(None)
    await updater.update()
    assert time.sleeps == [60, 120, 240, 300, 300, 300, 300, 300, 300]


@pytest.mark.asyncio
async def test_failure_backoff_other(updater: HaUpdater, server, time: FakeTime):
    server.setHomeAssistantError(400)
    for x in range(9):
        await updater.update()
    assert time.sleeps == [60, 120, 240, 300, 300, 300, 300, 300, 300]
    server.setHomeAssistantError(None)
    await updater.update()
    assert time.sleeps == [60, 120, 240, 300, 300, 300, 300, 300, 300]


@pytest.mark.asyncio
async def test_update_snapshots(updater: HaUpdater, server, time: FakeTime):
    await updater.update()
    assert not updater._stale()
    assert updater._state() == "waiting"
    verifyEntity(server, "binary_sensor.snapshots_stale", False, STALE_ATTRIBUTES)
    verifyEntity(server, "sensor.snapshot_backup", "waiting", {
        'friendly_name': 'Snapshot State',
        'last_snapshot': 'Never',
        'snapshots': [],
        'snapshots_in_google_drive': 0,
        'snapshots_in_hassio': 0
    })


@pytest.mark.asyncio
async def test_notification_link(updater: HaUpdater, server, time: FakeTime, global_info):
    await updater.update()
    assert not updater._stale()
    assert updater._state() == "waiting"
    verifyEntity(server, "binary_sensor.snapshots_stale", False, STALE_ATTRIBUTES)
    verifyEntity(server, "sensor.snapshot_backup", "waiting", {
        'friendly_name': 'Snapshot State',
        'last_snapshot': 'Never',
        'snapshots': [],
        'snapshots_in_google_drive': 0,
        'snapshots_in_hassio': 0
    })
    assert server.getNotification() is None

    global_info.failed(Exception())
    global_info.url = "http://localhost/test"
    time.advanceDay()
    await updater.update()
    assert server.getNotification() == {
        'message': 'The add-on is having trouble backing up your snapshots and needs attention.  Please visit the add-on [status page](http://localhost/test) for details.',
        'title': 'Hass.io Google Drive Backup is Having Trouble',
        'notification_id': 'backup_broken'
    }


@pytest.mark.asyncio
async def test_notification_clears(updater: HaUpdater, server, time: FakeTime, global_info):
    await updater.update()
    assert not updater._stale()
    assert updater._state() == "waiting"
    assert server.getNotification() is None

    global_info.failed(Exception())
    time.advanceDay()
    await updater.update()
    assert server.getNotification() is not None

    global_info.success()
    await updater.update()
    assert server.getNotification() is None


@pytest.mark.asyncio
async def test_publish_for_failure(updater: HaUpdater, server, time: FakeTime, global_info: GlobalInfo):
    global_info.success()
    await updater.update()
    assert server.getNotification() is None

    time.advanceDay()
    global_info.failed(Exception())
    await updater.update()
    assert server.getNotification() is not None

    time.advanceDay()
    global_info.failed(Exception())
    await updater.update()
    assert server.getNotification() is not None

    global_info.success()
    await updater.update()
    assert server.getNotification() is None


@pytest.mark.asyncio
async def test_failure_logging(updater: HaUpdater, server, time: FakeTime):
    server.setHomeAssistantError(501)
    assert LogBase.getLast() is None
    await updater.update()
    assert LogBase.getLast() is None

    time.advance(minutes=1)
    await updater.update()
    assert LogBase.getLast() is None

    time.advance(minutes=5)
    await updater.update()
    assert LogBase.getLast().msg == "Unable to reach Home Assistant (HTTP 501).  Is it restarting?"

    last_log = LogBase.getLast()
    time.advance(minutes=5)
    await updater.update()
    assert LogBase.getLast() is not last_log
    assert LogBase.getLast().msg == "Unable to reach Home Assistant (HTTP 501).  Is it restarting?"

    last_log = LogBase.getLast()
    server.setHomeAssistantError(None)
    await updater.update()
    assert LogBase.getLast() is last_log


def verifyEntity(backend, name, state, attributes):
    assert backend.getEntity(name) == state
    assert backend.getAttributes(name) == attributes
