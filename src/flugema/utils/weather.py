
import math

def dew_point(temperature: float, humidity: float) -> float:
    """Compute the dew point temperature from air temperature and relative humidity.

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