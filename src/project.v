`default_nettype none

module tt_um_uwasic_onboarding_mounib_jamous (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (1=output, 0=input)
    input  wire       ena,      // always 1
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);



    wire sclk;
    wire ncs;
    wire copi;

    wire [7:0] en_reg_out_7_0;
    wire [7:0] en_reg_out_15_8;
    wire [7:0] en_reg_pwm_7_0;
    wire [7:0] en_reg_pwm_15_8;
    wire [7:0] pwm_duty_cycle;


    assign sclk = ui_in[0];
    assign copi  = ui_in[1];
    assign ncs = ui_in[2];


    assign uio_oe = 8'hFF;



    spi_peripheral periph_inst (
        .clk(clk),
        .rst(rst_n),
        .SCLK(sclk),
        .nCS(ncs),
        .COPI(copi),
        .en_reg_out_7_0(en_reg_out_7_0),
        .en_reg_out_15_8(en_reg_out_15_8),
        .en_reg_pwm_7_0(en_reg_pwm_7_0),
        .en_reg_pwm_15_8(en_reg_pwm_15_8),
        .pwm_duty_cycle(pwm_duty_cycle)
    );

    // -------------------------------------------------------------------
    // Instantiate PWM Peripheral
    pwm_peripheral pwm_peripheral_inst (
        .clk(clk),
        .rst_n(rst_n),
        .en_reg_out_7_0(en_reg_out_7_0),
        .en_reg_out_15_8(en_reg_out_15_8),
        .en_reg_pwm_7_0(en_reg_pwm_7_0),
        .en_reg_pwm_15_8(en_reg_pwm_15_8),
        .pwm_duty_cycle(pwm_duty_cycle),
        .out({uio_out, uo_out})
    );

    // -------------------------------------------------------------------
    // Tie off unused inputs to avoid warnings
    wire _unused = &{ena, ui_in[7:3], uio_in, 1'b0};

endmodule
