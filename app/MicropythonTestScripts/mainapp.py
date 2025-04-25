import uasyncio as asyncio
from machine import Pin, UART, reset
import LEDListener
import InputListener

# Create the UART instance and the DE/RE control pins.
uart = UART(0, baudrate=57600, tx=Pin(0), rx=Pin(1))
de_pin = Pin(2, Pin.OUT)
re_pin = Pin(3, Pin.OUT)
# Set initial state to receive mode (DE low, RE low)
de_pin.value(0)
re_pin.value(0)

async def command_dispatcher():
    print("Command dispatcher started, waiting for commands...")
    while True:
        if uart.any():
            line = uart.readline()
            if line:
                try:
                    cmd = line.decode('utf-8').strip()  # type: ignore
                except Exception as e:
                    await LEDListener.uart_send(uart, de_pin, re_pin, "Error decoding command.\n")
                    print("Error decoding command:", e)
                    continue
                print("Dispatcher received command:", cmd)
                # Dispatch based on command prefix.
                if cmd.upper().startswith("LED"):
                    await LEDListener.process_command(uart, de_pin, re_pin, cmd)
                elif cmd.upper().startswith("INPUT"):
                    await InputListener.process_command(uart, de_pin, re_pin, cmd)
                else:
                    await LEDListener.uart_send(uart, de_pin, re_pin, "Invalid command prefix.\n")
                    print("Invalid command prefix:", cmd)
        await asyncio.sleep_ms(100)

async def main():
    asyncio.create_task(command_dispatcher())
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    # Send a final message and reset the board.
    # (Note: In a KeyboardInterrupt handler you might not be able to await;
    # here we call uart.write() directly with DE/RE toggling if possible.)
    de_pin.value(1)
    re_pin.value(1)
    uart.write("Keyboard interrupt detected. Exiting.\n")
    de_pin.value(0)
    re_pin.value(0)
    print("Keyboard interrupt detected. Exiting program.")
    reset()

