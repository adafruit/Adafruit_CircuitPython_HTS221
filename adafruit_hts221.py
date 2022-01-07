# SPDX-FileCopyrightText: 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_hts221`
================================================================================

Helper library for the HTS221 Humidity and Temperature Sensor

* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* `Adafruit HTS221 - Temperature & Humidity
  Sensor Breakout Board <https://www.adafruit.com/products/4535>`_

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
from adafruit_register.i2c_bit import RWBit, ROBit

try:
    from typing import Union, Sequence, Tuple
    from busio import I2C
except ImportError:
    pass

_WHO_AM_I = const(0x0F)

_CTRL_REG1 = const(0x20)
_CTRL_REG2 = const(0x21)
_CTRL_REG3 = const(0x22)
_STATUS_REG = const(0x27)
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
    def add_values(
        cls, value_tuples: Sequence[Tuple[str, int, Union[int, float]]]
    ) -> None:
        """creates CV entries"""
        cls.label = {}

        for value_tuple in value_tuples:
            name, value, label = value_tuple
            setattr(cls, name, value)
            cls.label[value] = label

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Returns true if the given value is a member of the CV"""
        return value in cls.label


class Rate(CV):
    """Options for :attr:`data_rate`

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
        ("ONE_SHOT", 0, 0),
        ("RATE_1_HZ", 1, 1),
        ("RATE_7_HZ", 2, 7),
        ("RATE_12_5_HZ", 3, 12.5),
    )
)


class HTS221:  # pylint: disable=too-many-instance-attributes
    """Library for the ST HTS221 Humidity and Temperature Sensor

    :param ~busio.I2C i2c_bus: The I2C bus the HTS221 is connected to


    **Quickstart: Importing and using the HTS221**

        Here is an example of using the :class:`HTS221` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_hts221

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()  # uses board.SCL and board.SDA
            hts = adafruit_hts221.HTS221(i2c)

        Now you have access to the :attr:`temperature` and :attr:`relative_humidity` attributes

        .. code-block:: python

            temperature = hts.temperature
            relative_humidity = hts.relative_humidity

    """

    _chip_id = ROUnaryStruct(_WHO_AM_I, "<B")
    _boot_bit = RWBit(_CTRL_REG2, 7)
    enabled = RWBit(_CTRL_REG1, 7)
    """Controls the power down state of the sensor. Setting to `False` will shut the sensor down"""
    _data_rate = RWBits(2, _CTRL_REG1, 0)
    _one_shot_bit = RWBit(_CTRL_REG2, 0)
    _temperature_status_bit = ROBit(_STATUS_REG, 0)
    _humidity_status_bit = ROBit(_STATUS_REG, 1)
    _raw_temperature = ROUnaryStruct(_TEMP_OUT_L, "<h")
    _raw_humidity = ROUnaryStruct(_HUMIDITY_OUT_L, "<h")

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

    def __init__(self, i2c_bus: I2C) -> None:
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, _HTS221_DEFAULT_ADDRESS)
        if not self._chip_id in [_HTS221_CHIP_ID]:
            raise RuntimeError(
                "Failed to find HTS221HB! Found chip ID 0x%x" % self._chip_id
            )
        self._boot()
        self.enabled = True
        self.data_rate = Rate.RATE_12_5_HZ  # pylint:disable=no-member

        t1_t0_msbs = self._t1_t0_deg_c_x8_msbits
        self.calib_temp_value_0 = self._t0_deg_c_x8_lsbyte
        self.calib_temp_value_0 |= (t1_t0_msbs & 0b0011) << 8

        self.calibrated_value_1 = self._t1_deg_c_x8_lsbyte
        self.calibrated_value_1 |= (t1_t0_msbs & 0b1100) << 6

        self.calib_temp_value_0 >>= 3  # divide by 8 to remove x8
        self.calibrated_value_1 >>= 3  # divide by 8 to remove x8

        self.calib_temp_meas_0 = self._t0_out
        self.calib_temp_meas_1 = self._t1_out

        self.calib_hum_value_0 = self._h0_rh_x2
        self.calib_hum_value_0 >>= 1  # divide by 2 to remove x2

        self.calib_hum_value_1 = self._h1_rh_x2
        self.calib_hum_value_1 >>= 1  # divide by 2 to remove x2

        self.calib_hum_meas_0 = self._h0_t0_out
        self.calib_hum_meas_1 = self._h1_t0_out

    # This is the closest thing to a software reset. It re-loads the calibration values from flash
    def _boot(self) -> None:
        self._boot_bit = True
        # wait for the reset to finish
        while self._boot_bit:
            pass

    @property
    def relative_humidity(self) -> float:
        """The current relative humidity measurement in %rH"""
        calibrated_value_delta = self.calib_hum_value_1 - self.calib_hum_value_0
        calibrated_measurement_delta = self.calib_hum_meas_1 - self.calib_hum_meas_0

        calibration_value_offset = self.calib_hum_value_0
        calibrated_measurement_offset = self.calib_hum_meas_0
        zeroed_measured_humidity = self._raw_humidity - calibrated_measurement_offset

        correction_factor = calibrated_value_delta / calibrated_measurement_delta

        adjusted_humidity = (
            zeroed_measured_humidity * correction_factor + calibration_value_offset
        )

        return adjusted_humidity

    @property
    def temperature(self) -> float:
        """The current temperature measurement in degrees Celsius"""

        calibrated_value_delta = self.calibrated_value_1 - self.calib_temp_value_0
        calibrated_measurement_delta = self.calib_temp_meas_1 - self.calib_temp_meas_0

        calibration_value_offset = self.calib_temp_value_0
        calibrated_measurement_offset = self.calib_temp_meas_0
        zeroed_measured_temp = self._raw_temperature - calibrated_measurement_offset

        correction_factor = calibrated_value_delta / calibrated_measurement_delta

        adjusted_temp = (
            zeroed_measured_temp * correction_factor
        ) + calibration_value_offset

        return adjusted_temp

    @property
    def data_rate(self) -> int:
        """The rate at which the sensor measures :attr:`relative_humidity` and :attr:`temperature`.
        :attr:`data_rate` should be set to one of the values of :class:`adafruit_hts221.Rate`.
        Note that setting :attr:`data_rate` to ``Rate.ONE_SHOT`` will cause
        :attr:`relative_humidity` and :attr:`temperature` measurements to only
        update when :meth:`take_measurements` is called."""
        return self._data_rate

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        if not Rate.is_valid(value):
            raise AttributeError("data_rate must be a `Rate`")

        self._data_rate = value

    @property
    def humidity_data_ready(self) -> bool:
        """Returns true if a new relative humidity measurement is available to be read"""
        return self._humidity_status_bit

    @property
    def temperature_data_ready(self) -> bool:
        """Returns true if a new temperature measurement is available to be read"""
        return self._temperature_status_bit

    def take_measurements(self) -> None:
        """Update the value of :attr:`relative_humidity` and :attr:`temperature` by taking a single
        measurement. Only meaningful if :attr:`data_rate` is set to ``ONE_SHOT``"""
        self._one_shot_bit = True
        while self._one_shot_bit:
            pass
