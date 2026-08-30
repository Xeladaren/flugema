
from .country   import Country
from .region    import Region
from .airport   import Airport
from .runway    import Runway
from .frequency import Frequency

def update_all():
    try:
        Airport.update()
        Runway.update()
        Frequency.update()
        Region.update()
        Country.update()
    except Exception as e:
        print(f"Fail to update database: {e}")