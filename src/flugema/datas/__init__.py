
from .users     import User
from .airplane  import Airplane
from .flight    import Flight
from .airport   import Airport, Runway, Frequency, Region, Country
from .openmeteo import OpenMeteo
from .picture   import Picture

def install_database():
    Picture.create_database()
    User.create_database()
    Airplane.create_database()
    Flight.create_database()