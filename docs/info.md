<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

    verilog code sets ups registers needed for spi peripheral, those being shift registers for input, a count register, and a register to store an inputted address alongside if we are reading or writing

    We then set up registers for nc sclk and copi that stores their values synced up with clk
    Then we set up wires that will check for if ncs sclk and copi are high or low, based on the lastest piece of data recieved from their synced registers

    in addition wires that store the current state if they are falling or rising

    we then implement a state machine that check if the peripherial is being reset or if the clk is rising.

    If the FSM is being reset we set all registers to 0

    if not we first add in the latest readings for nc sclk and copi

    Then we check our current state, if the state is idle we check if ncs had a falling edge in order to transition to the recieving data state, and setting all resiters to 0 that relate to data transmission

    If we are in the recieving state we check for when Sclk rises, if it rises we first add data to the shifting register using copi

    then we deal with our count register, if count==0 (no data ever added yet) we store the latest copi data to the read/write bit, and then as long as count is below 15 we add 1 to it, if count equates to 8 then we have recieved all address data and now we know where our address destination is. Finally if count==15 we move onto a state called Latch in order to dump all the data into the desired address

    in the Latch state we check if read/write bit is 1 and what address we have to insert it to
    Once done we go back to the Idle state

## How to test

 call make file (I need to ask, if i didn't please whoever reviews remind me how would I would actually document this)

## External hardware

 SPI controller
