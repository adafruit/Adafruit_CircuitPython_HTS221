import time
import board
import busio
import adafruit_hts221
print("poop")
i2c = busio.I2C(board.SCL, board.SDA)
hts = adafruit_hts221.HTS221(i2c)
print("got out of init")
while True:
    print("Humidity: %.2f percent rH" % hts.humidity)
    print("Temperature: %.2f C" % hts.temperature)
    time.sleep(1)