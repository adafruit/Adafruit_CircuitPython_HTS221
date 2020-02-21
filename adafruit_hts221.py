# The MIT License (MIT)
#
# Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
`adafruit_hts221`
================================================================================

Helper library for the HTS221 Humidity and Temperature Sensor

* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* `HTS221 Breakout <https://www.adafruit.com/products/4535>`_

**Software and Dependencies:**
 * Adafruit CircuitPython firmware for the supported boards:
    https://circuitpythohn.org/downloads
 * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
 * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register

"""
__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_HTS221.git"

from micropython import const
import adafruit_bus_device.i2c_device as i2cdevice
from adafruit_register.i2c_struct import ROUnaryStruct
from adafruit_register.i2c_bits import RWBits, ROBits
from adafruit_register.i2c_bit import RWBit

_WHO_AM_I = const(0x0F)

_CTRL_REG1 = const(0x20)
_CTRL_REG2 = const(0x21)
_CTRL_REG3 = const(0x22)   #Third control regsiter; DRDY_H_L, DRDY

_HUMIDITY_OUT_L = const(0x28 | 0x80) #Humidity output register (LSByte)
_TEMP_OUT_L = const(0x2A | 0x80)   #Temperature output register (LSByte)

_H0_RH_X2 = const(0x30)     #Humididy calibration LSB values
_H1_RH_X2 = const(0x31)     #Humididy calibration LSB values

_T0_DEGC_X8 = const(0x32)   #First byte of T0, T1 calibration values
_T1_DEGC_X8 = const(0x33)   #First byte of T0, T1 calibration values
_T1_T0_MSB = const(0x35)    #Top 2 bits of T0 and T1 (each are 10 bits)

_H0_T0_OUT = const(0x36|0x80)        #Humididy calibration Time 0 value
_H1_T1_OUT = const(0x3A|0x80)        #Humididy calibration Time 1 value

_T0_OUT = const(0x3C|0x80)       #T0_OUT LSByte
_T1_OUT = const(0x3E|0x80)       #T1_OUT LSByte


# _PRESS_OUT_XL = const(0x28 | 0x80)  # | 0x80 to set auto increment on multi-byte read
# _TEMP_OUT_L = const(0x2B | 0x80) # | 0x80 to set auto increment on multi-byte read

_HTS221_CHIP_ID = 0xBC
_HTS221_DEFAULT_ADDRESS = 0x5F


class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples):
        "creates CV entires"
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value):
        "Returns true if the given value is a member of the CV"
        return value in cls.string


class Rate(CV):
    """Options for ``data_rate``

    +-----------------------+------------------------------------------------------------------+
    | Rate                  | Description                                                      |
    +-----------------------+------------------------------------------------------------------+
    | ``Rate.ONE_SHOT``     | Setting `data_rate` to ``Rate.ONE_SHOT`` takes a single humidity |
    |                       | and temperature measurement                                      |
    +-----------------------+------------------------------------------------------------------+
    | ``Rate.RATE_1_HZ``    | 1 Hz                                                             |
    +-----------------------+------------------------------------------------------------------+
    | ``Rate.RATE_7_HZ``    | 7 Hz                                                             |
    +-----------------------+------------------------------------------------------------------+
    | ``Rate.RATE_12_5_HZ`` | 12.5 Hz                                                          |
    +-----------------------+------------------------------------------------------------------+

    """

    pass  # pylint: disable=unnecessary-pass


Rate.add_values(
    (
        ("RATE_ONE_SHOT", 0, 0, None),
        ("RATE_1_HZ", 1, 1, None),
        ("RATE_7_HZ", 2, 7, None),
        ("RATE_12_5_HZ", 3, 12.5, None),
    )
)

def bp(val):
    return format(val, "#010b")
class HTS221:  # pylint: disable=too-many-instance-attributes
    """Library for the ST LPS2x family of humidity sensors

        :param ~busio.I2C i2c_bus: The I2C bus the HTS221HB is connected to.
        :param address: The I2C device address for the sensor. Default is ``0x5d`` but will accept
            ``0x5c`` when the ``SDO`` pin is connected to Ground.

    """

    _chip_id = ROUnaryStruct(_WHO_AM_I, "<B")
    _boot = RWBit(_CTRL_REG2, 7)
    enabled = RWBit(_CTRL_REG1, 7)
    """Controls the power down state of the sensor. Setting to `False` will shut the sensor down"""
    _data_rate = RWBits(2, _CTRL_REG1, 0)

    _raw_temperature = ROUnaryStruct(_TEMP_OUT_L, "<h")
    _raw_humidity = ROUnaryStruct(_HUMIDITY_OUT_L, "<b")


    # humidity calibration consts
    _t0_deg_c_x8_lsbyte = ROBits(8, _T0_DEGC_X8, 0)
    _t1_deg_c_x8_lsbyte = ROBits(8, _T1_DEGC_X8, 0)
    _t1_t0_deg_c_x8_msbits = ROBits(4, _T1_T0_MSB, 0)

    _t0_out = ROUnaryStruct(_T0_OUT, "<h")
    _t1_out = ROUnaryStruct(_T1_OUT, "<h")

    _h0_rh_x2 = ROUnaryStruct(_H0_RH_X2, "<b")
    _h1_rh_x2 = ROUnaryStruct(_H1_RH_X2, "<b")

    _h0_t0_out = ROUnaryStruct(_H0_T0_OUT, "<h")
    _h1_t0_out = ROUnaryStruct(_H1_T1_OUT, "<h")


    def __init__(self, i2c_bus, address=_HTS221_DEFAULT_ADDRESS):
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, address)
        if not self._chip_id in [_HTS221_CHIP_ID]:
            raise RuntimeError(
                "Failed to find HTS221HB! Found chip ID 0x%x" % self._chip_id
            )
        self.boot()
        self.enabled = True
        self.data_rate = Rate.RATE_12_5_HZ  # pylint:disable=no-member
        self.T0_DEG_C = None
        self.T1_DEG_C = None
        self.T0_OUT = None
        self.T1_OUT = None

        self.H0_RH = None
        self.H1_RH = None
        self.H0_T0_OUT = None
        self.H1_T0_OUT = None
        self._load_calibration_values()

        print(" T0_DEG_C", self.T0_DEG_C)
        print(" T1_DEG_C", self. T1_DEG_C)
        print("   T0_OUT", self.T0_OUT)
        print("   T1_OUT", self.T1_OUT)

        print("    H0_RH", self.H0_RH)
        print("    H1_RH", self.H1_RH)
        print("H0_T0_OUT", self.H0_T0_OUT)
        print("H1_T0_OUT", self.H1_T0_OUT)

    def _load_calibration_values(self):
        print("loading")
        t1_t0_msbs = self._t1_t0_deg_c_x8_msbits
        # print("t1t0msbs:", bp(t1_t0_msbs))

        self.T0_DEG_C = self._t0_deg_c_x8_lsbyte
        self.T0_DEG_C |= ((t1_t0_msbs & 0b0011) << 8)
        # print("\nT0_DEG_C:", bp(self.T0_DEG_C))

        self.T1_DEG_C = self._t1_deg_c_x8_lsbyte
        # print("\nT1_DEG_C:", bp(self.T1_DEG_C))
        self.T1_DEG_C |= (t1_t0_msbs & 0b1100) << 6
        # print("\nT1_DEG_C:", bp(self.T1_DEG_C))
        self.T0_OUT = self._t0_out
        self.T1_OUT = self._t1_out
        # self.T1_OUT = None

        self.H0_RH = self._h0_rh_x2
        self.H1_RH = self._h1_rh_x2
        self.H0_T0_OUT = self._h0_t0_out
        self.H1_T0_OUT = self._h1_t0_out
        # self._t0_deg_c_x8_lsbyte = ROUnaryStruct(_T0_DEGC_X8, "<b")
        # self._t1_deg_c_x8_lsbyte = ROUnaryStruct(_T1_DEGC_X8, "<b")
        # self._t1_t0_deg_c_x8_msbits = ROBits(4, _T1_T0_MSB, 0)

        # self._h0_rh_x2 = ROUnaryStruct(_H0_RH_X2, "<b")
        # self._h1_rh_x2 = ROUnaryStruct(_H1_RH_X2, "<b")

        # self._h0_t0_out = ROUnaryStruct(_H0_T0_OUT, "<h")
        # self._h1_t0_out = ROUnaryStruct(_H1_T1_OUT, "<h")

        # to_out = ROUnaryStruct(_T0_OUT, "<h")
        # t1_out = ROUnaryStruct(_T1_OUT, "<h")

    #   _T0_DEGC_X8 = const(0x32|0x80)   #First byte of T0, T1 calibration values
    #   _T1_T0_MSB = const(0x35|0x80)    #Top 2 bits of T0 and T1 (each are 10 bits)
    #   # TO, T1 have to be assembled
    #   self._T0 = 0
    #   self._T1 = 0
    #   self._T1 = (buffer[0] & 0b1100)
    #   self._T1 <<= 6
    #   self._T0 = (buffer[0] & 0b0011)
    #   self._T0 <<= 8

    #   t0_degc_x8_l.read(buffer, 2)
    #   #  Or self._T1[0:7] on to the above to make a full 10 bits
    #   self._T0 |= buffer[0]
    #   self._T0 >>= 3 #// divide by 8 (as documented)
    #   self._T1 |= buffer[1]
    #   self._T1 >>= 3



    def _correct_humidity(self):
      pass
      # hum = ((int16_t)(H1) - (int16_t)(H0)) / 2.0; // remove x2 multiple

      # // Calculate humidity in decimal of grade centigrades i.e. 15.0 = 150.
      # h_temp = (float)(((int16_t)raw_humidity - (int16_t)H0_T0_OUT) * hum) /
      #         (float)((int16_t)H1_T0_OUT - (int16_t)H0_T0_OUT);
      # hum = (float)((int16_t)H0) / 2.0;    // remove x2 multiple
      # corrected_humidity = (hum + h_temp); // provide signed % measurement unit
    def _correct_temp(self):
      pass
      # corrected_temp =
      # (float)
      #     // measured temp(LSB) - offset(LSB) * (calibration measurement delta)
      #     (float)((int16_t)raw_temperature - (int16_t)T0_OUT) *
      #     (float)((int16_t)T1 - (int16_t)T0) / // divided by..
      #     // Calibration LSB delta + Calibration offset?
      #     (float)((int16_t)T1_OUT - (int16_t)T0_OUT) +
      # (int16_t)T0;
    def boot(self):
        """Reset the sensor, restoring all configuration registers to their defaults"""
        self._boot = True
        # wait for the reset to finish
        while self._boot:
            pass

    @property
    def humidity(self):
        """The current humidity measurement in hPa"""
        raw = self._raw_humidity

        if raw & (1 << 23) != 0:
            raw = raw - (1 << 24)
        return raw / 4096.0

    @property
    def temperature(self):
        """The current temperature measurement in degrees C"""
        raw_temperature = self._raw_temperature
        return (raw_temperature / 480) + 42.5

    @property
    def data_rate(self):
        """The rate at which the sensor measures ``humidity`` and ``temperature``. ``data_rate``
        shouldbe set to one of the values of ``adafruit_lps2x.DataRate``. Note that setting
        ``data_rate``to ``Rate.ONE_SHOT`` places the sensor into a low-power shutdown mode where
        measurements toupdate ``humidity`` and ``temperature`` are only taken when
        ``take_measurement`` is called."""
        return self._data_rate

    @data_rate.setter
    def data_rate(self, value):
        if not Rate.is_valid(value):
            raise AttributeError("data_rate must be a `Rate`")

        self._data_rate = value