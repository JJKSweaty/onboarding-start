`default_nettype none

module spi_peripheral (
    input wire clk,
    input wire reset,

    input wire sclk,
    input wire ncs,
    input wire copi,

    output reg [7:0] reg0,
    output reg [7:0] reg1,
    output reg [7:0] reg2,
    output reg [7:0] reg3,
    output reg [7:0] reg4
);
localparam [6:0] MAX_ADDRESS = 7'h04;

    // Synchronizer registers
    reg sclk_sync_0, sclk_sync_1;
    reg ncs_sync_0,  ncs_sync_1;
    reg copi_sync_0, copi_sync_1;

    // Previous values for edge detection
    reg sclk_prev;
    reg ncs_prev;

    // SPI transaction registers
    reg transaction_active;

    reg [4:0] bit_count;
    reg [15:0] shift_reg;

    //sync setup
    always @(posedge clk)begin
        if (reset) begin
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

    //edge detection
    always @(posedge clk)begin
        if (reset) begin
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

    //transaction
    always @(posedge clk) begin
        if(reset) begin
            transaction_active <= 1'b0;
        end else begin
            if (ncs_falling) begin
                transaction_active <= 1'b1;
            end else if (ncs_rising) begin
                transaction_active <= 1'b0;
            end
        end
    end

    always @(posedge clk) begin
        if (reset) begin
            shift_reg <= 16'd0;
            bit_count <= 5'd0;
        end else begin
            if (ncs_falling) begin
                shift_reg <= 16'd0;
                bit_count <= 5'd0;
            end else if (transaction_active && sclk_rising) begin
                shift_reg <= {shift_reg[14:0], copi_sync_1};
                bit_count <= bit_count + 1'b1;
            end
        end
    end

wire rw_bit = shift_reg[15];
wire [6:0] addr = shift_reg[14:8];
wire [7:0] data = shift_reg[7:0];
wire valid_write = (rw_bit == 1'b1);
wire valid_address = (addr <= MAX_ADDRESS);
wire transaction_ready;

assign transaction_ready = ncs_rising && (bit_count == 5'd16) && valid_write && valid_address;

always @(posedge clk)begin 
    if (transaction_ready) begin
        case (addr)
            7'h00: reg0 <= data;
            7'h01: reg1 <= data;
            7'h02: reg2 <= data;
            7'h03: reg3 <= data;
            7'h04: reg4 <= data;
            default: ;
        endcase
        
    end else if (reset)begin
        reg0 <= 8'd0;
        reg1 <= 8'd0;
        reg2 <= 8'd0;
        reg3 <= 8'd0;
        reg4 <= 8'd0;
    end

end

endmodule

`default_nettype wire
