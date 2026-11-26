"""Pytest unit tests for the reference model itself (no simulator needed)."""
from fifo_model import FifoModel


def test_starts_empty():
    m = FifoModel(4)
    assert m.empty and not m.full and m.count == 0


def test_fill_and_drain_order():
    m = FifoModel(4)
    for i in range(4):
        assert m.step(True, i, False) == (True, False)
    assert m.full
    out = []
    for _ in range(4):
        m.step(False, 0, True)
        out.append(m.rd_data)
    assert out == [0, 1, 2, 3] and m.empty


def test_write_when_full_is_dropped():
    m = FifoModel(2)
    m.step(True, 1, False)
    m.step(True, 2, False)
    assert m.step(True, 3, False) == (False, False)
    assert list(m.q) == [1, 2]


def test_read_when_empty_is_ignored():
    m = FifoModel(2)
    assert m.step(False, 0, True) == (False, False)
    assert not m.rd_valid


def test_simultaneous_rw_when_full_only_reads():
    m = FifoModel(2)
    m.step(True, 1, False)
    m.step(True, 2, False)
    assert m.step(True, 9, True) == (False, True)
    assert m.rd_data == 1 and m.count == 1


def test_simultaneous_rw_when_empty_only_writes():
    m = FifoModel(2)
    assert m.step(True, 7, True) == (True, False)
    assert m.count == 1 and not m.rd_valid
