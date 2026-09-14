
from .country   import Country
from .region    import Region
from .airport   import Airport
from .runway    import Runway
from .frequency import Frequency

import logging
logger = logging.getLogger(__name__)

def update_all():
    try:
        Airport.update()
        Runway.update()
        Frequency.update()
        Region.update()
        Country.update()
    except Exception as e:
        logger.exception(f"Fail to update database: {e}")