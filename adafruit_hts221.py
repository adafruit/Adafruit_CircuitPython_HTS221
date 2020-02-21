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
    https://circuitpython.org/downloads
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
_CTRL_REG3 = const(0x22)

# some addresses are anded to set the  top bit so that multi-byte reads will work
_HUMIDITY_OUT_L = const(0x28 | 0x80)  # Humidity output register (LSByte)
_TEMP_OUT_L = const(0x2A | 0x80)  # Temperature output register (LSByte)

_H0_RH_X2 = const(0x30)  # Humididy calibration LSB values
_H1_RH_X2 = const(0x31)  # Humididy calibration LSB values

_T0_DEGC_X8 = const(0x32)  # First byte of T0, T1 calibration values
_T1_DEGC_X8 = const(0x33)  # First byte of T0, T1 calibration values
_T1_T0_MSB = const(0x35)  # Top 2 bits of T0 and T1 (each are 10 bits)

_H0_T0_OUT = const(0x36 | 0x80)  # Humididy calibration Time 0 value
_H1_T1_OUT = const(0x3A | 0x80)  # Humididy calibration Time 1 value

_T0_OUT = const(0x3C | 0x80)  # T0_OUT LSByte
_T1_OUT = const(0x3E | 0x80)  # T1_OUT LSByte

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

# def bp(val):
#     return format(val, "#010b")
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

    _h0_rh_x2 = ROUnaryStruct(_H0_RH_X2, "<B")
    _h1_rh_x2 = ROUnaryStruct(_H1_RH_X2, "<B")

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

        t1_t0_msbs = self._t1_t0_deg_c_x8_msbits
        self.t0_deg_c = self._t0_deg_c_x8_lsbyte
        self.t0_deg_c |= (t1_t0_msbs & 0b0011) << 8
        self.t1_deg_c = self._t1_deg_c_x8_lsbyte
        self.t1_deg_c |= (t1_t0_msbs & 0b1100) << 6

        self.t0_out = self._t0_out
        self.t1_out = self._t1_out
        self.h0_rh = self._h0_rh_x2
        self.h1_rh = self._h1_rh_x2
        self.h0_out = self._h0_t0_out
        self.h1_out = self._h1_t0_out

    def _correct_humidity(self):
        pass

    def _correct_temp(self):
        pass

    def boot(self):
        """Reset the sensor, restoring all configuration registers to their defaults"""
        self._boot = True
        # wait for the reset to finish
        while self._boot:
            pass

    @property
    def humidity(self):
        """The current humidity measurement in hPa"""
        hum = ((self.h1_rh) - (self.h0_rh)) / 2.0  # remove x2 multiple

        # Calculate humidity in decimal of grade centigrades i.e. 15.0 = 150.
        h_temp = ((self._raw_humidity - self.h0_out) * hum) / (
            self.h1_out - self.h0_out
        )

        hum = self.h0_rh / 2.0  # remove x2 multiple
        return hum + h_temp  # provide signed % measurement unit

    @property
    def temperature(self):
        """The current temperature measurement in degrees C"""
        temp = (self._raw_temperature - self.t0_out) * (self.t1_deg_c - self.t0_deg_c)
        temp /= (self.t1_out - self.t0_out) + self.t0_deg_c
        return temp
        # Calibration LSB delta + Calibration offset?

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
