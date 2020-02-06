from ..worker import Worker, StopWorkException
from .faketime import FakeTime
import pytest
import asyncio


@pytest.mark.asyncio
async def test_worker(time: FakeTime):
    data = {'count': 0}

    async def work():
        if data['count'] >= 5:
            raise StopWorkException()
        data['count'] += 1

    worker = Worker("test", work, time, 1)
    task = worker.start()
    await asyncio.wait([task])
    assert not worker.isRunning()
    assert data['count'] == 5
    assert time.sleeps == [1, 1, 1, 1, 1]
    # assert worker._task.name == "test"
    assert worker.getLastError() is None


@pytest.mark.asyncio
async def test_worker_error(time: FakeTime):
    data = {'count': 0}

    def work():
        if data['count'] >= 5:
            raise StopWorkException()
        data['count'] += 1
        raise OSError()

    worker = Worker("test", work, time, 1)
    task = worker.start()
    await asyncio.wait([task])
    assert not worker.isRunning()
    assert data['count'] == 5
    assert time.sleeps == [1, 1, 1, 1, 1]
    # assert worker.getName() == "test"
    assert worker.getLastError() is not None
    assert type(worker.getLastError()) is OSError
