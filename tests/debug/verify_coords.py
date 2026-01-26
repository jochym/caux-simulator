#!/usr/bin/env python3
"""
Coordinate Verification Script
Compares PyEphem (Simulator Engine) with Astropy (Industry Standard)
to isolate topocentric transformation discrepancies.
"""

import ephem
from math import pi, degrees, radians
from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.time import Time
import astropy.units as u
from datetime import datetime, timezone


def verify_altair():
    # 1. Setup Fixed Observer (Your Synced Position)
    lat_deg = 50.1822
    lon_deg = 19.7925
    elevation = 400

    # Use current time (UTC)
    now = datetime.now(timezone.utc)
    print(f"Comparison Time (UTC): {now}")
    print(f"Observer: Lat={lat_deg}, Lon={lon_deg}, Elev={elevation}m\n")

    # --- Astropy Calculation ---
    loc = EarthLocation(
        lat=lat_deg * u.deg, lon=lon_deg * u.deg, height=elevation * u.m
    )
    time = Time(now)

    # Altair J2000 Coordinates (ICRS)
    # RA: 19h 50m 47.0s, Dec: +08° 52' 06"
    altair_icrs = SkyCoord(ra="19h50m47.0s", dec="+08d52m06s", frame="icrs")

    # Convert to AltAz (Apparent - No Refraction)
    # We use AltAz with pressure=0 to match simulator config
    altaz_frame = AltAz(obstime=time, location=loc, pressure=0 * u.bar)
    altair_altaz = altair_icrs.transform_to(altaz_frame)

    # Get Jnow (Apparent RA/Dec)
    altair_jnow = altair_icrs.transform_to("gcrs")  # GCRS is close to Apparent

    print("--- Astropy (Reference) ---")
    print(f"Jnow RA:  {altair_jnow.ra.hms}")
    print(f"Jnow Dec: {altair_jnow.dec.dms}")
    print(f"AZM:      {altair_altaz.az.deg:.6f}°")
    print(f"ALT:      {altair_altaz.alt.deg:.6f}°\n")

    # --- PyEphem Calculation (Simulator Core) ---
    obs = ephem.Observer()
    obs.lat = str(lat_deg)
    obs.lon = str(lon_deg)
    obs.elevation = elevation
    obs.date = now
    obs.pressure = 0  # No refraction
    obs.epoch = obs.date  # Jnow

    star = ephem.star("Altair")
    star.compute(obs)

    print("--- PyEphem (Simulator) ---")
    print(f"Jnow RA:  {star.ra}")
    print(f"Jnow Dec: {star.dec}")
    print(f"AZM:      {degrees(star.az):.6f}°")
    print(f"ALT:      {degrees(star.alt):.6f}°\n")

    # --- Comparison ---
    d_az = abs(degrees(star.az) - altair_altaz.az.deg) * 60
    d_alt = abs(degrees(star.alt) - altair_altaz.alt.deg) * 60

    print("--- Discrepancy ---")
    print(f"Delta Azimuth: {d_az:.4f} arcmin")
    print(f"Delta Altitude: {d_alt:.4f} arcmin")

    if d_az > 1.0 or d_alt > 1.0:
        print(
            "\nWARNING: Large discrepancy (>1') detected between Ephem and Astropy reference!"
        )
    else:
        print("\nSUCCESS: Ephem and Astropy agree within 1 arcminute.")


if __name__ == "__main__":
    verify_altair()
