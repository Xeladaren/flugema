import math
import drawsvg

def marker_wind_barb(wind_speed: int, south_lat: bool = False) -> None | drawsvg.Marker:
    wind_rounded = int(5 * round(wind_speed / 5))

    if wind_rounded == 0:
        return None

    marker = drawsvg.Marker(0, 0, 1, 1, 
        scale=1, 
        orient="auto-start-reverse", 
        overflow="visible", 
        id=f"wind{wind_rounded}kn"
    )

    path = drawsvg.Path(
        fill="context-stroke", 
        stroke="context-stroke", 
        stroke_width=0.8, 
        stroke_linecap="round",
        stroke_linejoin="round"
    )

    x_index = 0
    while wind_rounded > 0:
        if wind_rounded >= 50:
            wind_rounded -= 50
            if x_index == 0:
                x_index -= 2
            else:
                x_index -= 1
            
            path.M(x_index, 0)
            if south_lat:
                path.l(2,-4).l(0,4).l(-2,0)
            else:
                path.l(2,4).l(0,-4).l(-2,0)

        elif wind_rounded >= 10:
            wind_rounded -= 10

            path.M(x_index, 0)
            if south_lat:
                path.l(2,-4)
            else:
                path.l(2,4)

        elif wind_rounded >= 5:
            wind_rounded -= 5

            if x_index == 0:
                x_index -= 2

            path.M(x_index, 0)
            if south_lat:
                path.l(1,-2)
            else:
                path.l(1,2)
        x_index -= 2
    
    marker.append(path)
    return marker