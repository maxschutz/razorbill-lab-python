from instruments.micro_epsilon.capa_ncdt import DT62xx
import time

# Replace with your DT6200’s IP address
sensor_ip = "169.254.168.150"

# Connect to the DT6200 (default: 1 channel; change if your device has more)
dt6200 = DT62xx(sensor_ip, num_channels=4)

for i in range(1, 5):
    # Poll the latest measurement from channel 1 (returns the most recent reading)
    value = dt6200.channels[1].measure
    value2 = dt6200.channels[2].measure
    value3 = dt6200.channels[3].measure
    value4 = dt6200.channels[4].measure
    print("Latest measurement (channel 1):", value)
    print("Latest measurement (channel 2):", value2)
    print("Latest measurement (channel 3):", value3)
    print("Latest measurement (channel 4):", value4)
    time.sleep(0.01)  # Sleep for 10ms to avoid flooding the device with requests


dt6200.flush_buffer()  # Clear the buffer
time.sleep(1)  # Wait for a second to allow new data to be collected

# To get a block of all available measurements (all channels, all buffered frames)
data_block = dt6200.get_data_block()
print("Buffered data block:")
for i, data in enumerate(data_block):
    print(f"Frame {i}: {data}")
    if i > 10:
        break

# To clear the internal data buffer before starting a new measurement
dt6200.flush_buffer()