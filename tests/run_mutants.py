"""Mutation testing: inject known bugs into the RTL and confirm the testbench
catches every one. A testbench that passes on buggy RTL is not verifying much.

Usage:  python3 run_mutants.py
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
RTL = HERE.parent / "rtl" / "sync_fifo.v"

MUTANTS = {
    "full flag ignores MSB (off-by-one)":
        ("(wr_ptr[AW] != rd_ptr[AW]) && ", ""),
    "write allowed when full":
        ("wire do_write = wr_en && !full;", "wire do_write = wr_en;"),
    "read allowed when empty":
        ("wire do_read  = rd_en && !empty;", "wire do_read  = rd_en;"),
    "rd_valid stuck high after read":
        ("rd_valid <= do_read;", "rd_valid <= rd_valid | do_read;"),
    "read from wrong address":
        ("rd_data <= mem[rd_ptr[AW-1:0]];", "rd_data <= mem[wr_ptr[AW-1:0]];"),
    "reset doesn't clear read pointer":
        ("rd_ptr   <= 0;", ""),
}


def main():
    src = RTL.read_text()
    caught = 0
    for name, (old, new) in MUTANTS.items():
        assert old in src, f"mutation target not found: {old!r}"
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "sync_fifo.v"
            bad.write_text(src.replace(old, new, 1))
            build = pathlib.Path(tmp) / "sim_build"
            r = subprocess.run(
                ["make", f"VERILOG_SOURCES={bad}", f"SIM_BUILD={build}",
                 "RAND_CYCLES=3000", "SEED=1"],
                cwd=HERE, capture_output=True, text=True)
            killed = "FAIL=0" not in r.stdout
        caught += killed
        print(f"[{'CAUGHT' if killed else 'MISSED'}] {name}")
    print(f"\n{caught}/{len(MUTANTS)} mutants caught")
    sys.exit(0 if caught == len(MUTANTS) else 1)


if __name__ == "__main__":
    main()
