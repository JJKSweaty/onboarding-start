## How it works

This project is an SPI-controlled PWM peripheral for Tiny Tapeout. It receives
write-only SPI transactions and uses them to configure output enable registers,
PWM enable registers, and a shared PWM duty-cycle register.

The design uses the following Tiny Tapeout inputs for the SPI interface:

| Signal | Tiny Tapeout input |
| --- | --- |
| SCLK | `ui_in[0]` |
| COPI | `ui_in[1]` |
| nCS | `ui_in[2]` |

SPI mode 0 is used, so data is sampled on the rising edge of `SCLK`. Each
transaction is 16 bits long:

| Field | Width | Description |
| --- | --- | --- |
| R/W bit | 1 bit | `1` writes a register, `0` is ignored |
| Address | 7 bits | Valid addresses are `0x00` through `0x04` |
| Data | 8 bits | Value written to the selected register |

The register map is:

| Address | Register | Description | Reset value |
| --- | --- | --- | --- |
| `0x00` | `en_reg_out_7_0` | Enables static/PWM output on `uo_out[7:0]` | `0x00` |
| `0x01` | `en_reg_out_15_8` | Enables static/PWM output on `uio_out[7:0]` | `0x00` |
| `0x02` | `en_reg_pwm_7_0` | Enables PWM mode on `uo_out[7:0]` | `0x00` |
| `0x03` | `en_reg_pwm_15_8` | Enables PWM mode on `uio_out[7:0]` | `0x00` |
| `0x04` | `pwm_duty_cycle` | Sets the PWM duty cycle | `0x00` |

The output behavior for each output bit is:

| Output enable bit | PWM mode bit | Output |
| --- | --- | --- |
| `0` | `X` | `0` |
| `1` | `0` | `1` |
| `1` | `1` | PWM signal |

The PWM peripheral drives the 16-bit output bus `{uio_out[7:0], uo_out[7:0]}`.
The duty cycle is controlled by `pwm_duty_cycle`, where `0x00` is 0% duty cycle
and `0xFF` is forced high for 100% duty cycle.

## How to test

Run the Cocotb testbench from the `test` directory:

```sh
cd test
make
```

The provided tests exercise SPI register writes and check the resulting
`uo_out` and `uio_out` behavior. During debugging, the generated `tb.vcd`
waveform can be opened in a waveform viewer to inspect SPI transactions,
register updates, and PWM output behavior.

Example SPI transaction:

```text
Write 0xF0 to address 0x00:
1 0000000 11110000
```

This writes the value `0xF0` into `en_reg_out_7_0`.

## External hardware

No external hardware is required. The design uses only the Tiny Tapeout input,
output, bidirectional IO, clock, reset, and enable pins.
