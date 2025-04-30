# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray



async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")
async def PWM_sampling(dut, signal, channel, cycles):
    """
    Sample PWM signal
    
    Parameters:
    - signal: signal we are looking at
    - channel: the PWM bit channel we want 
    - cycles: the number of cycles we are going to measure
    """

    def singlebit(val, bit):
        return (int(val) >> bit) & 1

    # I miss C++ already
    const_timeout = 436700  # This was just assumed to be 1/frequency*0.99 plus an extra 100k for safety
    rising_edges = 0
    hightotal = 0
    periodtotal = 0
    start_time = cocotb.utils.get_sim_time(units='ns')

    # Check for if it's 100% or 0% in addition, allows us to start the test when it's done being 0 and starting high

    while singlebit(signal.value, channel) == 1:
        await RisingEdge(dut.clk)
        if cocotb.utils.get_sim_time(units="ns") - start_time > const_timeout:
            return 0.0, 100.0

    while singlebit(signal.value, channel) == 0:
        await RisingEdge(dut.clk)
        if cocotb.utils.get_sim_time(units="ns") - start_time > const_timeout:
            return 0.0, 0.0

    startingtime = cocotb.utils.get_sim_time(units="ns")

    while rising_edges < cycles:
        # Wait for when the bit is high until it no longer is
        while singlebit(signal.value, channel) == 1:
            await RisingEdge(dut.clk)
            # For the sake of redundancy
            if cocotb.utils.get_sim_time(units="ns") - startingtime > const_timeout:
                return 0.0, 100.0

        # Get time when it fell
        fall = cocotb.utils.get_sim_time(units="ns")

        # Wait for when the bit is low
        while singlebit(signal.value, channel) == 0:
            await RisingEdge(dut.clk)
            # For redundancy
            if cocotb.utils.get_sim_time(units="ns") - startingtime > const_timeout:
                return 0.0, 0.0

        # Get time when it rose back up
        rise = cocotb.utils.get_sim_time(units="ns")
        rising_edges += 1

        # Time when signal was high
        timehigh = fall - startingtime
        # Period
        period = rise - startingtime

        # Finding total time it was high by adding high of each test iteration
        hightotal += timehigh
        # Period
        periodtotal += period
        startingtime = cocotb.utils.get_sim_time(units="ns")

    avghigh = hightotal / cycles
    avgperiod = periodtotal / cycles

    return 1e9 / avgperiod, 100 * (avghigh / avgperiod)



async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())


    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    # using 50% for ease of testing frequency
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)
    print ("frequency results for uio :")
    for j in range(8):
        #turning on uio channels
        ui_in_val= await send_spi_transaction(dut, 1, 0x01, 1 << j)
        ui_in_val= await send_spi_transaction(dut, 1, 0x03, 1<<j)
        frequencywanted, extra = await PWM_sampling(dut, dut.uio_out, j, 4)

        if 2970<=frequencywanted<=3030:
            print(f"fequency met the requested range: at bit {j} the frequency was: {frequencywanted} ")
        # turning off uio channels
        ui_in_val= await send_spi_transaction(dut, 1, 0x01, 0)
        ui_in_val= await send_spi_transaction(dut, 1, 0x03, 0)
    print("freuency results for uo:")
    for j in range(8):
        # turning on uo channels
        ui_in_val= await send_spi_transaction(dut, 1, 0x00, 1 << j)
        ui_in_val= await send_spi_transaction(dut, 1, 0x02, 1<<j)
        frequencywanted, extra = await PWM_sampling(dut, dut.uo_out, j, 4)

        if 2970<=frequencywanted<=3030:
            print(f"fequency met the requested range: at bit {j} the frequency was: {frequencywanted} ")
        # turning off uo channels
        ui_in_val= await send_spi_transaction(dut, 1, 0x00, 0)
        ui_in_val= await send_spi_transaction(dut, 1, 0x02, 0)


    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())


    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    

    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)
    for i in range(3):
        if i==0:
            print( "Duty 0% tests:")
            ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)
        elif i==1:
            print( "Duty 50% tests:")
            ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)
        elif i==2:
            print( "Duty 100% tests:")
            ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)
        #replication of frequency tests but this time caring for duty instead of frequency
        print("duty tests at uio:")
        for j in range(8):
            ui_in_val= await send_spi_transaction(dut, 1, 0x01, 1 << j)
            ui_in_val= await send_spi_transaction(dut, 1, 0x03, 1<<j)
            extra, dutywanted = await PWM_sampling(dut, dut.uio_out, j, 4)

            print(f"duty being tested for is 0% : at bit {j} the duty was: {dutywanted}% ")
            ui_in_val= await send_spi_transaction(dut, 1, 0x01, 0)
            ui_in_val= await send_spi_transaction(dut, 1, 0x03, 0)
        
        print("duty tests at uo:")
        for j in range(8):
            ui_in_val= await send_spi_transaction(dut, 1, 0x00, 1 << j)
            ui_in_val= await send_spi_transaction(dut, 1, 0x02, 1<<j)
            frequencywanted, extra = await PWM_sampling(dut, dut.uo_out, j, 4)

            print(f"duty being tested for is 0% : at bit {j} the duty was: {dutywanted}% ")
            ui_in_val= await send_spi_transaction(dut, 1, 0x00, 0)
            ui_in_val= await send_spi_transaction(dut, 1, 0x02, 0)


    dut._log.info("PWM Duty Cycle test completed successfully")
