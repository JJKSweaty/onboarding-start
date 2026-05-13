# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.triggers import RisingEdge
from cocotb.types import Logic
from cocotb.types import LogicArray

CLK_PERIOD_NS = 100
PWM_MIN_FREQ_HZ = 2970
PWM_MAX_FREQ_HZ = 3030
PWM_PERIOD_NS = 13 * 256 * CLK_PERIOD_NS
PWM_PERIOD_CYCLES = 13 * 256

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

async def reset_dut(dut):
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
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

async def setup_pwm_output(dut, duty_cycle):
    await send_spi_transaction(dut, 1, 0x00, 0x01)  # Drive lower output bit 0 high
    await send_spi_transaction(dut, 1, 0x02, 0x01)  # Enable PWM on lower output bit 0
    await send_spi_transaction(dut, 1, 0x04, duty_cycle)
    await ClockCycles(dut.clk, 100)

def uo_out_bit0(dut):
    return int(dut.uo_out.value) & 1

async def wait_uo0_transition(dut, target_value, timeout_cycles=2 * PWM_PERIOD_CYCLES):
    previous = uo_out_bit0(dut)
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        current = uo_out_bit0(dut)
        if previous != target_value and current == target_value:
            return cocotb.utils.get_sim_time(units="ns")
        previous = current
    raise AssertionError(f"Timed out waiting for uo_out[0] to transition to {target_value}")

async def measure_pwm_period_ns(dut):
    first_rising = await wait_uo0_transition(dut, 1)
    second_rising = await wait_uo0_transition(dut, 1)
    return second_rising - first_rising

async def measure_pwm_duty_percent(dut):
    rising_time = await wait_uo0_transition(dut, 1)
    falling_time = await wait_uo0_transition(dut, 0)
    next_rising_time = await wait_uo0_transition(dut, 1)

    high_time = falling_time - rising_time
    period = next_rising_time - rising_time
    return (high_time / period) * 100

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")
    await reset_dut(dut)

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
    await reset_dut(dut)
    await setup_pwm_output(dut, 0x80)

    period_ns = await measure_pwm_period_ns(dut)
    frequency_hz = 1_000_000_000 / period_ns

    assert PWM_MIN_FREQ_HZ <= frequency_hz <= PWM_MAX_FREQ_HZ, (
        f"Expected PWM frequency between {PWM_MIN_FREQ_HZ} Hz and "
        f"{PWM_MAX_FREQ_HZ} Hz, got {frequency_hz:.2f} Hz"
    )
    dut._log.info(f"PWM frequency: {frequency_hz:.2f} Hz")


@cocotb.test()
async def test_pwm_duty(dut):
    await reset_dut(dut)

    await setup_pwm_output(dut, 0x00)
    for _ in range(PWM_PERIOD_CYCLES):
        await RisingEdge(dut.clk)
        assert uo_out_bit0(dut) == 0, "Expected 0% duty cycle to stay low"

    await setup_pwm_output(dut, 0x80)
    duty_percent = await measure_pwm_duty_percent(dut)
    assert 49 <= duty_percent <= 51, f"Expected 50% duty cycle, got {duty_percent:.2f}%"

    await setup_pwm_output(dut, 0xFF)
    for _ in range(PWM_PERIOD_CYCLES):
        await RisingEdge(dut.clk)
        assert uo_out_bit0(dut) == 1, "Expected 100% duty cycle to stay high"

    dut._log.info(f"PWM duty cycle at 0x80: {duty_percent:.2f}%")
