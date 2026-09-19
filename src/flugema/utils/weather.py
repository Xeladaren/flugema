
import math

# --- Unit conversion --------------------------------------------------------
ZERO_CELSIUS = 273.15     # Offset between degC and K

# --- ISA constants ----------------------------------------------------------
P0 = 1013.25              # Standard sea level pressure (hPa)
T0 = 15.0                 # Standard sea level temperature (degC)
T0_KELVIN = T0 + ZERO_CELSIUS   # Standard sea level temperature (K), 288.15
LAPSE_RATE = 0.0065             # Temperature lapse rate (degC/m)
R_AIR = 287.05287               # Specific gas constant for dry air (J/(kg.K))
R_VAPOR = 461.495               # Specific gas constant for water vapour (J/(kg.K))
EPSILON = R_AIR / R_VAPOR       # Molar mass ratio water / dry air (~0.621945)
EXPONENT = 5.2558797            # g / (L * R)
SCALE_HEIGHT = T0_KELVIN / LAPSE_RATE 

# Upper altitude bound of the troposphere model
H_TROPOPAUSE = 11000.0    # m

# Standard sea level density (kg/m3), ~1.225
RHO0 = (P0 * 100) / (R_AIR * T0_KELVIN)

def saturation_vapor_pressure(temperature: float) -> float:
    """
    Compute the saturation vapour pressure at a given temperature.

    Uses the Buck (1996) equation, whose accuracy is better than 0.1 %
    over the -40 °C to +50 °C range. The over-ice form is used below
    0 °C, which is the physically relevant branch for cold, cloud-free
    air.

    Args:
        temperature: The air temperature in degrees Celsius.

    Returns:
        The saturation vapour pressure in hPa.

    Raises:
        ValueError: If ``temperature`` is at or below absolute zero.
    """

    if temperature <= -ZERO_CELSIUS:
        raise ValueError("Temperature must be above absolute zero (-273.15 °C).")

    if temperature >= 0.0:
        # Over liquid water
        return 6.1121 * math.exp(
            (18.678 - temperature / 234.5) * temperature / (257.14 + temperature)
        )
    # Over ice
    return 6.1115 * math.exp(
        (23.036 - temperature / 333.7) * temperature / (279.82 + temperature)
    )


def relative_humidity(temperature: float, dew_point: float) -> float:
    """
    Compute the relative humidity from the air temperature and the dew point.

        RH = 100 * Psat(Td) / Psat(T)

    Args:
        temperature: The air temperature in degrees Celsius.
        dew_point: The dew point temperature in degrees Celsius.

    Returns:
        The relative humidity in percent, in the range ``]0, 100]``.

    Raises:
        ValueError: If ``dew_point`` exceeds ``temperature``.
    """
    if dew_point > temperature:
        raise ValueError("Dew point cannot exceed air temperature.")

    ratio = saturation_vapor_pressure(dew_point) / saturation_vapor_pressure(temperature)
    return 100.0 * ratio

def dew_point(temperature: float, humidity: float) -> float:
    """
    Compute the dew point temperature from air temperature and relative humidity.

    Uses the Magnus-Tetens approximation with the Alduchov-Eskridge
    coefficients (``b = 17.62``, ``c = 243.12 °C``), which is accurate to
    within about 0.1 °C for temperatures ranging from -40 °C to +50 °C.

    Args:
        temperature: The air temperature in degrees Celsius.
        humidity: The relative humidity in percent, in the range ``]0, 100]``.

    Returns:
        The dew point temperature in degrees Celsius.

    Raises:
        ValueError: If ``humidity`` is not in the range ``]0, 100]``.
    """
    if not 0 < humidity <= 100:
        raise ValueError("humidity need to be inter ]0, 100]")

    b = 17.62
    c = 243.12
    gamma = math.log(humidity / 100.0) + (b * temperature) / (c + temperature)
    return (c * gamma) / (b - gamma)

def altitude_to_pressure(altitude: float, reference_pressure: float = P0) -> float:
    """Compute the ISA pressure at a given altitude.

        P = Pref * (1 - L * h / T0) ** 5.2558797

    Inverse of `pressure_to_altitude`. The linear lapse rate model only
    holds inside the troposphere, hence the upper bound on the altitude.

    Args:
        altitude: The altitude in meters.
        reference_pressure: The sea level reference pressure in hPa,
            defaulting to the ISA standard of 1013.25 hPa.

    Returns:
        The pressure in hPa.

    Raises:
        ValueError: If ``reference_pressure`` is not strictly positive, or
            if ``altitude`` lies above the tropopause, where the
            troposphere model no longer applies.
    """
    if reference_pressure <= 0.0:
        raise ValueError("Reference pressure must be strictly positive.")

    if altitude > H_TROPOPAUSE:
        raise ValueError(
            f"Altitude {altitude:.1f} m is above the tropopause limit of "
            f"{H_TROPOPAUSE:.1f} m: the troposphere model does not apply."
        )

    # The absolute temperature is mandatory in the lapse rate ratio
    ratio = 1.0 - LAPSE_RATE * altitude / T0_KELVIN
    return reference_pressure * ratio**EXPONENT

def pressure_altitude(altitude: float, qnh: float) -> float:
    """
    Compute the pressure altitude, i.e. the altitude read on an altimeter
    set to the standard setting of 1013.25 hPa.

    Args:
        qnh: The sea level reference pressure in hPa.
        altitude: The indicated altitude in meters for the given QNH.

    Returns:
        The pressure altitude in meters.

    Raises:
        ValueError: If altitude lies above the tropopause, where the
            temperature stops decreasing and the model no longer applies.
    """
    if altitude > H_TROPOPAUSE:
        raise ValueError(f"Altitude {altitude:.1f} m is above the tropopause limit of {H_TROPOPAUSE:.1f} m")

    return altitude + SCALE_HEIGHT * (1.0 - (qnh / P0) ** (1 / EXPONENT))

def air_density(pressure: float, temperature: float, relative_humidity: float | None = None) -> float:
    """
    Compute the moist air density from pressure, temperature and humidity.
    Dalton's law of partial pressures gives::
        Pv  = RH * Psat(T)
        rho = (P - Pv) / (Rd * T) + Pv / (Rv * T)
             = P / (Rd * T) * (1 - (Pv / P) * (1 - Rd / Rv))

    Water vapour (18 g/mol) is lighter than dry air (29 g/mol), so a
    higher humidity lowers the density. Leaving ``relative_humidity`` to
    ``None`` falls back to the dry air law.

    Args:
        pressure: The static pressure in hPa.
        temperature: The air temperature in degrees Celsius.
        relative_humidity: The optional relative humidity in percent, in
            the range ``[0, 100]``.

    Returns:
        The air density in kg/m3.

    Raises:
        ValueError: If ``pressure`` is not strictly positive, if
            ``temperature`` is at or below absolute zero, or if
            ``relative_humidity`` falls outside the ``[0, 100]`` range.
    """
    if pressure <= 0.0:
        raise ValueError("Pressure must be strictly positive.")
    if temperature <= -ZERO_CELSIUS:
        raise ValueError("Temperature must be above absolute zero (-273.15 °C).")

    # The ideal gas law requires absolute units
    dry_density = (pressure * 100) / (R_AIR * (temperature + ZERO_CELSIUS))
    if relative_humidity is None:
        return dry_density

    if not 0.0 <= relative_humidity <= 100.0:
        raise ValueError("Relative humidity must lie in the [0, 100] range.")

    # Both pressures are in hPa, so their ratio stays unit free
    vapor_pressure = (relative_humidity / 100.0) * saturation_vapor_pressure(temperature)
    # Vapour pressure cannot exceed the total pressure (guards against
    # inconsistent inputs such as a very low pressure at a high temperature).
    vapor_pressure = min(vapor_pressure, pressure)

    return dry_density * (1.0 - (vapor_pressure / pressure) * (1.0 - EPSILON))


def density_altitude(altitude: float, qnh: float, temperature: float, relative_humidity: float | None = None) -> float:
    """
    Compute the density altitude from pressure, temperature and humidity.

    The density altitude is the ISA altitude at which the standard
    atmosphere matches the actual air density::
        rho = P / (Rd * T) * (1 - (Pv / P) * (1 - Rd / Rv))
        DA  = (T0 / L) * (1 - (rho / rho0) ** (1 / (5.2558797 - 1)))

    Humidity lowers the air density and therefore raises the density
    altitude: water vapour (18 g/mol) is lighter than dry air (29 g/mol).
    Leaving ``relative_humidity`` to ``None`` falls back to the dry air
    model.

    Args:
        pressure: The static pressure in hPa.
        temperature: The outside air temperature in degrees Celsius.
        relative_humidity: The optional relative humidity in percent, in
            the range ``[0, 100]``.

    Returns:
        The density altitude in meters.

    Raises:
        ValueError: Propagated from `air_density` on invalid pressure,
            temperature or humidity values.
    """
    pressure_alt = pressure_altitude(altitude, qnh)
    pressure = altitude_to_pressure(pressure_alt)
    rho = air_density(pressure, temperature, relative_humidity)
    return SCALE_HEIGHT * (1.0 - (rho / RHO0) ** (1.0 / (EXPONENT - 1.0)))

def isa_temperature(altitude: float) -> float:
    """
    Compute the standard ISA temperature at a given altitude.

        T = T0 - L * h

    Args:
        altitude: The altitude in meters.

    Returns:
        The standard temperature in degrees Celsius.

    Raises:
        ValueError: If ``altitude`` lies above the tropopause, where the
            temperature stops decreasing and the model no longer applies.
    """
    if altitude > H_TROPOPAUSE:
        raise ValueError(f"Altitude {altitude:.1f} m is above the tropopause limit of {H_TROPOPAUSE:.1f} m")
    
    return T0 - (LAPSE_RATE * altitude)