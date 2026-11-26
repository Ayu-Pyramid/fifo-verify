# Usage:  make            (run all cocotb tests)
#         make SEED=1234  (reproduce a random run)
#         make FIFO_DEPTH=8
SIM ?= icarus
TOPLEVEL_LANG = verilog
FIFO_DEPTH ?= 16
FIFO_WIDTH ?= 8
export FIFO_DEPTH FIFO_WIDTH

VERILOG_SOURCES = $(PWD)/../rtl/sync_fifo.v
COMPILE_ARGS += -P sync_fifo.DEPTH=$(FIFO_DEPTH) -P sync_fifo.WIDTH=$(FIFO_WIDTH)
TOPLEVEL = sync_fifo
COCOTB_TOPLEVEL = sync_fifo
COCOTB_TEST_MODULES = test_fifo

include $(shell cocotb-config --makefiles)/Makefile.sim

waves:
	gtkwave waves.vcd &

.PHONY: waves
