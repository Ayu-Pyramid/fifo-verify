// Synchronous FIFO
// - Parameterized WIDTH and DEPTH (DEPTH must be a power of 2)
// - A write is accepted only when !full; a read is accepted only when !empty
// - rd_data is registered: valid one cycle after an accepted read (rd_valid)
`timescale 1ns/1ps
module sync_fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 16
) (
    input  wire               clk,
    input  wire               rst_n,     // active-low synchronous reset
    input  wire               wr_en,
    input  wire [WIDTH-1:0]   wr_data,
    input  wire               rd_en,
    output reg  [WIDTH-1:0]   rd_data,
    output reg                rd_valid,
    output wire               full,
    output wire               empty,
    output wire [$clog2(DEPTH):0] count
);
    localparam AW = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];
    // One extra MSB on each pointer distinguishes full from empty
    reg [AW:0] wr_ptr, rd_ptr;

    wire do_write = wr_en && !full;
    wire do_read  = rd_en && !empty;

    assign empty = (wr_ptr == rd_ptr);
    assign full  = (wr_ptr[AW] != rd_ptr[AW]) && (wr_ptr[AW-1:0] == rd_ptr[AW-1:0]);
    assign count = wr_ptr - rd_ptr;

    always @(posedge clk) begin
        if (!rst_n) begin
            wr_ptr   <= 0;
            rd_ptr   <= 0;
            rd_valid <= 1'b0;
            rd_data  <= {WIDTH{1'b0}};
        end else begin
            if (do_write) begin
                mem[wr_ptr[AW-1:0]] <= wr_data;
                wr_ptr <= wr_ptr + 1'b1;
            end
            rd_valid <= do_read;
            if (do_read) begin
                rd_data <= mem[rd_ptr[AW-1:0]];
                rd_ptr  <= rd_ptr + 1'b1;
            end
        end
    end

`ifdef COCOTB_SIM
    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, sync_fifo);
    end
`endif
endmodule
