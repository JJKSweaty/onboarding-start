module spi_peripheral (
    input wire clk,
    input wire reset,

    input wire sclk,
    input wire ncs,
    input wire copi,

    output wire [7:0] uo_out
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

    // Internal registers
    reg [7:0] reg0, reg1, reg2, reg3, reg4;

    wire sclk_s = sclk_sync_1;
    wire ncs_s  = ncs_sync_1;
    wire copi_s = copi_sync_1;

    wire sclk_rising = sclk_s && !sclk_prev;
    wire ncs_rising  = ncs_s && !ncs_prev;
    wire ncs_falling = !ncs_s && ncs_prev;

    wire rw_bit = shift_reg[15];
    wire [6:0] addr = shift_reg[14:8];
    wire [7:0] data = shift_reg[7:0];

    wire valid_write = (rw_bit == 1'b0);
    wire valid_address = (addr <= MAX_ADDRESS);

    //sync setup
    always @(posedge clk)begin
        sclk_sync_0<=sclk;
        sclk_sync_1<=sclk_sync_0;
        ncs_sync_0 <= ncs;
        ncs_sync_1 <= ncs_sync_0;
        copi_sync_0 <= copi;
        copi_sync_1 <= copi_sync_0;
    end

    //edge detection
    always @(posedge clk)begin
         sclk_prev <= sclk_sync_1;
         ncs_prev <= ncs_sync_1;
    end

    wire sclk_rising = sclk_s && !sclk_prev; 
    wire ncs_rising  = ncs_s && !ncs_prev;
    wire ncs_falling = !ncs_s && ncs_prev;

    //transaction
    always @(posedge clk) begin
        if(reset) begin
        transaction_active<=1'b0;
        end else begin
        if (ncs_falling) 
            transaction_active<=1'b1;
        else if (ncs_rising)
            transaction_active<=1'b0;
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
            shift_reg <= {shift_reg[14:0], copi_s};
            bit_count <= bit_count + 1'b1;
        end
    end
end

        



    endmodule
