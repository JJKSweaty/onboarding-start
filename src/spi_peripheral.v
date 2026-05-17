`default_nettype none

module spi_peripheral (
    input  wire       clk,
    input  wire       rst_n,

    input  wire       sclk,
    input  wire       ncs,
    input  wire       copi,

    output reg  [7:0] reg0,
    output reg  [7:0] reg1,
    output reg  [7:0] reg2,
    output reg  [7:0] reg3,
    output reg  [7:0] reg4
);

    // Synchronizer registers
    reg sclk_sync_0, sclk_sync_1;
    reg ncs_sync_0,  ncs_sync_1;
    reg copi_sync_0, copi_sync_1;

    // Previous values for edge detection
    reg sclk_prev;
    reg ncs_prev;

    // SPI transaction registers
    reg [4:0] bit_count;
    reg [15:0] shift_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_sync_0 <= 1'b0;
            sclk_sync_1 <= 1'b0;
            ncs_sync_0  <= 1'b1;
            ncs_sync_1  <= 1'b1;
            copi_sync_0 <= 1'b0;
            copi_sync_1 <= 1'b0;
        end else begin
            sclk_sync_0 <= sclk;
            sclk_sync_1 <= sclk_sync_0;
            ncs_sync_0  <= ncs;
            ncs_sync_1  <= ncs_sync_0;
            copi_sync_0 <= copi;
            copi_sync_1 <= copi_sync_0;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_prev <= 1'b0;
            ncs_prev  <= 1'b1;
        end else begin
            sclk_prev <= sclk_sync_1;
            ncs_prev  <= ncs_sync_1;
        end
    end

    wire sclk_rising = sclk_sync_1 && !sclk_prev;
    wire ncs_rising  = ncs_sync_1 && !ncs_prev;
    wire ncs_falling = !ncs_sync_1 && ncs_prev;
    wire transaction_active = !ncs_sync_1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg <= 16'd0;
            bit_count <= 5'd0;
        end else if (ncs_falling) begin
            shift_reg <= 16'd0;
            bit_count <= 5'd0;
        end else if (transaction_active && sclk_rising && (bit_count < 5'd16)) begin
            shift_reg <= {shift_reg[14:0], copi_sync_1};
            bit_count <= bit_count + 1'b1;
        end
    end

    wire [6:0] addr = shift_reg[14:8];
    wire [7:0] data = shift_reg[7:0];
    wire valid_write = shift_reg[15];
    wire transaction_ready = ncs_rising && (bit_count == 5'd16) && valid_write;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg0 <= 8'd0;
            reg1 <= 8'd0;
            reg2 <= 8'd0;
            reg3 <= 8'd0;
            reg4 <= 8'd0;
        end else if (transaction_ready) begin
            case (addr)
                7'h00: reg0 <= data;
                7'h01: reg1 <= data;
                7'h02: reg2 <= data;
                7'h03: reg3 <= data;
                7'h04: reg4 <= data;
                default: ;
            endcase
        end
    end

endmodule

`default_nettype wire
