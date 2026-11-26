"""Cycle-level Python reference model of sync_fifo.v."""
from collections import deque


class FifoModel:
    def __init__(self, depth: int):
        self.depth = depth
        self.q = deque()
        self.rd_valid = False
        self.rd_data = 0

    @property
    def count(self) -> int:
        return len(self.q)

    @property
    def full(self) -> bool:
        return len(self.q) == self.depth

    @property
    def empty(self) -> bool:
        return len(self.q) == 0

    def step(self, wr_en: bool, wr_data: int, rd_en: bool):
        """Advance one clock edge. Returns (write_accepted, read_accepted)."""
        do_write = wr_en and not self.full
        do_read = rd_en and not self.empty
        # Read sees the state before this edge's write (same as the RTL)
        if do_read:
            self.rd_data = self.q.popleft()
        self.rd_valid = do_read
        if do_write:
            self.q.append(wr_data)
        return do_write, do_read

    def reset(self):
        self.q.clear()
        self.rd_valid = False
        self.rd_data = 0
