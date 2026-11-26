# Synchronous FIFO: RTL + Python-based Verification

![verify](https://github.com/<your-username>/fifo-verify/actions/workflows/ci.yml/badge.svg)

A parameterized synchronous FIFO in Verilog, verified with a cocotb (Python)
testbench using a reference model, a scoreboard, constrained-random stimulus,
functional coverage and mutation testing.

## Spec
| Item | Behavior |
|---|---|
| Parameters | `WIDTH` (default 8), `DEPTH` (default 16, power of 2) |
| Reset | Active-low, synchronous. Clears pointers, so FIFO becomes empty |
| Write | Accepted only when `!full`. A write while full is dropped |
| Read | Accepted only when `!empty`. `rd_data` is registered and valid the cycle after, flagged by `rd_valid` |
| Read + write, same cycle | Empty: only the write happens. Full: only the read happens. Otherwise both happen |
| Flags | `full`, `empty`, `count` (0..DEPTH) |
| Full/empty detection | Pointers carry one extra MSB: equal means empty, MSB differs with the rest equal means full |

## Repo layout
```
rtl/sync_fifo.v         the design
tests/fifo_model.py     cycle-level Python reference model
tests/test_model.py     pytest unit tests for the model
tests/test_fifo.py      cocotb testbench (directed, random, coverage)
tests/run_mutants.py    injects bugs into the RTL, checks every one is caught
.github/workflows/      CI runs everything on each push
```

## Run it
```bash
sudo apt-get install iverilog gtkwave     # macOS: brew install icarus-verilog gtkwave
pip install -r requirements.txt
cd tests
pytest -q test_model.py     # model unit tests
make                        # all simulation tests + coverage report
make SEED=1234              # reproduce a specific random run
make FIFO_DEPTH=8           # try another depth
python3 run_mutants.py      # mutation testing
gtkwave waves.vcd           # view waveforms
```

## Test plan
| Test | What it checks |
|---|---|
| `test_reset` | Empty, not full, count 0 after reset |
| `test_fill_then_drain` | Fill to full, drain to empty, data stays in order |
| `test_overflow_ignored` | Writes while full are dropped, stored data isn't corrupted |
| `test_underflow_ignored` | Reads while empty don't assert `rd_valid` |
| `test_simultaneous_rw` | Same-cycle read and write when empty, mid and full |
| `test_pointer_wraparound` | Pointers wrap several times with data still intact |
| `test_random` | 20,000 cycles of seeded random traffic in biased phases, with mid-run resets. Every cycle is checked against the model |

**How checking works:** inputs are driven on the falling edge and the model is
stepped with them. On the next falling edge, `full`, `empty`, `count`,
`rd_valid` and `rd_data` are compared against the model.

## Coverage
| Cover point | Bins |
|---|---|
| `fifo.state` | empty / mid / full |
| `fifo.op` | idle / write / read / read+write |
| `fifo.state_x_op` | every op in every state (12 bins) |
| `fifo.count` | every occupancy level 0..DEPTH |
| `fifo.overflow_attempt`, `fifo.underflow_attempt` | hit at least once |

Result: **38/38 bins (100%)**. The test fails if any bin is missed.

## Mutation testing
`run_mutants.py` plants 6 realistic bugs in the RTL (an off-by-one full flag,
writes allowed when full, reads allowed when empty, a stuck `rd_valid`, a wrong
read address, an incomplete reset). The testbench catches **6/6**.

## Bugs found during development
<!-- Write about a real bug you hit while building or changing this: what the
symptom was, which test caught it, what the waveform showed, and the fix. -->
- _TODO_

## Next steps
- Asynchronous FIFO with Gray-code pointers across two clock domains
- Run on Verilator as well as Icarus
