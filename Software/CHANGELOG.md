# Changelog for Firmware

Put all software notes/changelog stuff here. Try to format something like below to minimize git conflicts:

```
## <date, optionally w/ commit hash>

<notes>

### Added

### Changed

### Removed

## <older date>

...
```

This format is adopted from [keepachangelog.com](https://keepachangelog.com).

## 4/13/2026 (1e6b12e)

### Added

- Port C, pins 1 - 8 are GPIO inputs, for the 8 channels respectively. All pulled low internally.
- PC0 is intended as a status output LED
    - Solid indicates it's in idle mode
    - Slow flash indicates it's working
    - Fast flash indicates error
- USART2 and SWD is connected to onboard programmer (on nucleo board)
- PA 12, 11, 9, and 8 are USB FS DP, DM, VBUS\_sense, and Start Of Frame (SOF) respectively.
    - SOF is a hardware output thing, originating at the host computer, generated every 1ms. We can use it within our code to sync the data packets we send. It is on an output pin in case we need it on an external device, but I don't expect we will. Not sure if we can turn it off.
- Prescaler is 89, and auto-reload register (ARR) is 137. Reasoning:
    - The ultimate cap on capture speed comes from USB FS constraints. This is realistically going to be ~1MBps.
    - For sending data from STM to PC, we have two options:
        - Send a start byte, a byte holding the 8 channels, and a byte for uint\_8 timestamp (`[Start byte] [Channels] [Timestamp]`). This means one packet (one data point on a channel) will be 3 bytes. At 1MBps we can send 333,333 updates per second. Fast enough for UART, I2C, and low speed CAN and SPI.
        - Alternative is to send in the format `[Start byte] [N Datapoints] [Timestamp]`. This way, every N bytes sent corresponds to N-2 datapoints. USB has a [max packet size of 64 bytes](https://community.st.com/t5/stm32-mcus-products/usb-cdc-how-to-increase-speed-baud-rate/td-p/620701), and apparently it's most efficient to send at this rate. If N=62, each 64 bytes sends 62 data points, which is effectively 900,000 data points per second. I'd argue this is more effective. We could make N variable in the code.
        - If we go with the 2nd option, prescaler being 89 and ARR being 1 (0 indexed) will make timer trigger DMA ~1M times per second; fastest rate. Increasing ARR will slow down the timer effectively, down to ARR = 5 making DMA trigger ~333,333 times per second. Since we're using UART for now (comms between STM and PC), I've set ARR to 137, putting DMA at ~15,000 per second (matches 115,200 baud). We can easily decrease later.
- CAN bus *is* enableable, but not enabled.
- System Core -> DMA, and Clock Tree is *not* set up yet.
