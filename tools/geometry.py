from math import radians, degrees, asin, sin, cos, atan2, log, tan, pi


def r2d(rad):
    """Return degrees in range [-180, 180) for given radians angle"""
    return ((degrees(rad) + 180) % 360) - 180


def pointRadialDistance(lat1, lon1, bearing, distance):
    """
    Return final coordinates (lat,lon) [in degrees] given initial coordinates
    (lat1,lon1) [in degrees] and a bearing [in degrees] and distance [in km]
    """
    rlat, rlon = pointRadialDistanceRad(*map(radians,(lat1, lon1, bearing)),
                                        distance*1000)
    return (r2d(rlat), r2d(rlon))


def pointRadialDistanceRad(rlat1, rlon1, rbearing, distance):
    """
    Return final coordinates (lat,lon) [in radians] given initial coordinates
    (lat1,lon1) [in radians] and a bearing [in radians] and distance [in m]
    Based on: https://stackoverflow.com/questions/877524/calculating-coordinates-given-a-bearing-and-a-distance
    """
    rdistance = distance / 6371000  # normalize linear distance to radian angle
    rlat = asin(sin(rlat1) * cos(rdistance) + cos(rlat1) * sin(rdistance) * cos(rbearing))
    rlon = rlon1 + atan2(sin(rbearing) * sin(rdistance) * cos(rlat1),
                         cos(rdistance) - sin(rlat1) * sin(rlat))
    return (rlat, rlon)

