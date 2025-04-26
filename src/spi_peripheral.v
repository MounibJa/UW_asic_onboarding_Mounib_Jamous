
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 04/24/2025 10:32:36 AM
// Design Name: 
// Module Name: spi_peripheral
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////

`timescale 1ns / 1ps

module spi_peripheral(
    output reg [7:0] en_reg_out_7_0, //registers
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle,
    
    input wire clk, //clk and reset
    input wire rst,
    
    input wire SCLK, //asynchronous signals for SPI
    input wire COPI,
    input wire nCS
    );
    
    // needed registers for FSM
    reg rw_bit;
    reg [6:0] reg_address;
    reg [3:0] count;
    reg [7:0] shift_regin;
    
    // state register
    reg [1:0] state;
    localparam IDLE= 2'b00, RECEIVING =2'b01, LATCH =2'b10; // setting up states
    
    reg [1:0] sync_nc, sync_sclk, sync_copi; // metastability signals

    // storing the latest signal recieved
    wire syncd_ncs  = sync_nc[0];
    wire syncd_sclk = sync_sclk[0];
    wire syncd_copi = sync_copi[0];
    // storing rising sclk and falling ncs for checks
    wire sclk_rising= ~sync_sclk[1] & sync_sclk[0];
    wire ncs_falling= sync_nc[1] & ~sync_nc[0] ;
    //begin when we are reseting or when clk is rising
always @(posedge clk or negedge rst) begin

    // check if rst is 0, if so we need to empty things out 
    if(!rst) begin
         shift_regin<= 8'b0;  
         count<= 4'b0;   
         reg_address<= 7'b0;   
         state<= 2'b00; //remember add idle state later  
         
         en_reg_out_7_0   <= 8'b0;
         en_reg_out_15_8  <= 8'b0;
         en_reg_pwm_7_0   <= 8'b0;
         en_reg_pwm_15_8  <= 8'b0;
         pwm_duty_cycle   <= 8'b0;
        
        
        sync_nc<= 2'b0;
        sync_sclk <= 2'b0;
        sync_copi<= 2'b0;

    // if not reseting then carry out FSM 
    end else begin 
    // updating syncs
        sync_nc  <= { sync_nc[0],nCS };
        sync_sclk <= { sync_sclk[0],SCLK};
        sync_copi <= {sync_copi[0],COPI  };
        //setting up cases 

        case(state)
        IDLE: begin
        // check if its falling based on documentation
        if (ncs_falling) begin
                    // if falling we are now recieving  and now we reset registers and write to 0
                    state <= RECEIVING;
                    count <= 4'd0;
                    shift_regin <= 8'b0;
                    reg_address <= 7'b0;
                    rw_bit <= 1'b0; // Default to write operation
                   
       end
       end
       // recieving state
       RECEIVING: begin
                // only initiate if clk is rising for sclk
                 if (sclk_rising) begin
                           // rising edge shift next bit
                        shift_regin <= {shift_regin[6:0], syncd_copi};   //shifting

                        
                        if (count == 4'd0) begin // no count started read the rw bit which is first bit
                            rw_bit <= syncd_copi;  
                        end

                         // increment until saturated
                        if (count < 4'd15) begin
                        
                            count <= count + 1;
                        end
                        if( count == 4'd8) begin 
                            reg_address<=  shift_regin[6:0];
                            
                         end
                        if( count== 4'd15) begin
                            
                            state<= LATCH;
                            
                        end
                        // once saturated

  end
  
  
  end
  
  LATCH: begin

                            if( rw_bit==1'b1) begin // check if we read or write
                                case(reg_address)
                                    7'd0: en_reg_out_7_0 <= shift_regin; 
                                    7'd1: en_reg_out_15_8 <= shift_regin;
                                    7'd2: en_reg_pwm_7_0 <= shift_regin; 
                                    7'd3: en_reg_pwm_15_8 <= shift_regin;
                                    7'd4: pwm_duty_cycle <= shift_regin; 
                               endcase
                               end
                        
                        state<= IDLE;
   
   end
  
  endcase
  
  end
  
  end
    

                    
endmodule
