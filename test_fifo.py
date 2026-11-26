"""cocotb testbench for sync_fifo: directed tests + constrained-random test
with a scoreboard (Python reference model) and functional coverage."""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge
from cocotb_coverage.coverage import CoverPoint, CoverCross, coverage_db

from fifo_model import FifoModel

DEPTH = int(os.environ.get("FIFO_DEPTH", "16"))
WIDTH = int(os.environ.get("FIFO_WIDTH", "8"))
MASK = (1 << WIDTH) - 1


# ---------------------------------------------------------------- coverage
def _state(m):
    return "empty" if m.empty else "full" if m.full else "mid"


@CoverPoint("fifo.state", xf=lambda m, w, r: _state(m), bins=["empty", "mid", "full"])
@CoverPoint("fifo.op", xf=lambda m, w, r: (w, r),
            bins=[(False, False), (True, False), (False, True), (True, True)])
@CoverCross("fifo.state_x_op", items=["fifo.state", "fifo.op"])
@CoverPoint("fifo.overflow_attempt", xf=lambda m, w, r: w and m.full, bins=[True])
@CoverPoint("fifo.underflow_attempt", xf=lambda m, w, r: r and m.empty, bins=[True])
@CoverPoint("fifo.count", xf=lambda m, w, r: m.count, bins=list(range(DEPTH + 1)))
def sample(model, wr_en, rd_en):
    """Sampled once per cycle with the state *before* the clock edge."""


# ----------------------------------------------------------------- helpers
class Tb:
    def __init__(self, dut):
        self.dut = dut
        self.model = FifoModel(DEPTH)
        self.cycles = 0
        self.wraps = 0
        self.writes = 0

    async def start(self):
        cocotb.start_soon(Clock(self.dut.clk, 10, unit="ns").start())
        await self.reset()

    async def reset(self):
        d = self.dut
        d.rst_n.value = 0
        d.wr_en.value = 0
        d.rd_en.value = 0
        d.wr_data.value = 0
        for _ in range(2):
            await RisingEdge(d.clk)
        d.rst_n.value = 1
        self.model.reset()
        await FallingEdge(d.clk)
        self.check()

    def check(self):
        d, m = self.dut, self.model
        assert int(d.empty.value) == m.empty, f"empty: dut={d.empty.value} model={m.empty}"
        assert int(d.full.value) == m.full, f"full: dut={d.full.value} model={m.full}"
        assert int(d.count.value) == m.count, f"count: dut={int(d.count.value)} model={m.count}"
        assert int(d.rd_valid.value) == m.rd_valid, "rd_valid mismatch"
        if m.rd_valid:
            assert int(d.rd_data.value) == m.rd_data, (
                f"rd_data: dut={int(d.rd_data.value):#x} model={m.rd_data:#x}")

    async def cycle(self, wr_en, wr_data, rd_en):
        """Drive inputs on the falling edge, update model, check next falling edge."""
        d = self.dut
        sample(self.model, wr_en, rd_en)
        d.wr_en.value = int(wr_en)
        d.wr_data.value = wr_data & MASK
        d.rd_en.value = int(rd_en)
        wrote, _ = self.model.step(wr_en, wr_data & MASK, rd_en)
        if wrote:
            self.writes += 1
            if self.writes % DEPTH == 0:
                self.wraps += 1
        await FallingEdge(d.clk)
        self.cycles += 1
        self.check()

    async def write(self, data):
        await self.cycle(True, data, False)

    async def read(self):
        await self.cycle(False, 0, True)

    async def idle(self):
        await self.cycle(False, 0, False)


# ---------------------------------------------------------- directed tests
@cocotb.test()
async def test_reset(dut):
    """After reset: empty, not full, count 0."""
    tb = Tb(dut)
    await tb.start()
    assert int(dut.empty.value) == 1 and int(dut.full.value) == 0


@cocotb.test()
async def test_fill_then_drain(dut):
    """Fill to full, then drain to empty; data must come out in order."""
    tb = Tb(dut)
    await tb.start()
    for i in range(DEPTH):
        await tb.write(i)
    assert int(dut.full.value) == 1
    for _ in range(DEPTH):
        await tb.read()
    await tb.idle()
    assert int(dut.empty.value) == 1


@cocotb.test()
async def test_overflow_ignored(dut):
    """Writes while full are dropped and don't corrupt stored data."""
    tb = Tb(dut)
    await tb.start()
    for i in range(DEPTH):
        await tb.write(i)
    for _ in range(3):
        await tb.write(0xAA)
    for _ in range(DEPTH):
        await tb.read()


@cocotb.test()
async def test_underflow_ignored(dut):
    """Reads while empty don't assert rd_valid or move the pointer."""
    tb = Tb(dut)
    await tb.start()
    for _ in range(3):
        await tb.read()
    await tb.write(0x5A)
    await tb.read()


@cocotb.test()
async def test_simultaneous_rw(dut):
    """Read+write on the same cycle when empty, mid, and full."""
    tb = Tb(dut)
    await tb.start()
    await tb.cycle(True, 0x11, True)          # empty: only the write happens
    for i in range(DEPTH // 2):
        await tb.write(i)
    for i in range(4):
        await tb.cycle(True, 0x40 + i, True)  # mid: both happen, count stays
    while not tb.model.full:
        await tb.write(0x77)
    await tb.cycle(True, 0x99, True)          # full: only the read happens


@cocotb.test()
async def test_pointer_wraparound(dut):
    """Push 3*DEPTH items through a half-full FIFO so pointers wrap."""
    tb = Tb(dut)
    await tb.start()
    for i in range(DEPTH // 2):
        await tb.write(i)
    for i in range(3 * DEPTH):
        await tb.cycle(True, i, True)
    assert tb.wraps >= 3


# ------------------------------------------------------------- random test
@cocotb.test()
async def test_random(dut):
    """Constrained-random traffic in phases (fill-biased, drain-biased, balanced)."""
    seed = int(os.environ.get("SEED", random.randrange(2**32)))
    rng = random.Random(seed)
    dut._log.info(f"SEED={seed}  (rerun with SEED={seed} make)")
    n_cycles = int(os.environ.get("RAND_CYCLES", "20000"))

    tb = Tb(dut)
    await tb.start()
    # (p_write, p_read) per phase: biasing is what reaches full/empty corners
    phases = [(0.9, 0.2), (0.2, 0.9), (0.5, 0.5), (0.8, 0.8)]
    phase_len = 200
    for c in range(n_cycles):
        pw, pr = phases[(c // phase_len) % len(phases)]
        if c % 1000 == 999:          # occasional mid-traffic reset
            await tb.reset()
            continue
        await tb.cycle(rng.random() < pw, rng.getrandbits(WIDTH), rng.random() < pr)
    dut._log.info(f"random test: {tb.cycles} cycles, {tb.writes} writes, {tb.wraps} wraps")


# ------------------------------------------------------- coverage report
@cocotb.test()
async def zz_coverage_report(dut):
    """Runs last: print and export coverage, fail if any bin is unhit."""
    coverage_db.report_coverage(dut._log.info, bins=False)
    coverage_db.export_to_yaml(filename="coverage.yml")
    holes = []
    for name in ["fifo.state", "fifo.op", "fifo.state_x_op", "fifo.overflow_attempt",
                 "fifo.underflow_attempt", "fifo.count"]:
        cp = coverage_db[name]
        if cp.coverage < cp.size:
            holes.append(f"{name}: {cp.coverage}/{cp.size}")
    total = coverage_db["fifo"]
    dut._log.info(f"TOTAL FUNCTIONAL COVERAGE: {total.cover_percentage:.1f}%")
    assert not holes, "coverage holes: " + ", ".join(holes)
