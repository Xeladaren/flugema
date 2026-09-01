
from .users     import User
from .airplane  import Airplane
from .flight    import Flight
from .airport   import Airport, Runway, Frequency, Region, Country
from .openmeteo import OpenMeteo

def install_database():
    User.create_database()
    Airplane.create_database()
    Flight.create_database()