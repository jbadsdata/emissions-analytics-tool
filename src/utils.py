import math
from datetime import datetime
import pytz
from src.config import TZ_DICTIONARY

def sanitize_time_needed(x,y):
    return int(math.ceil(min(x, y) / 300.0) * 5)

def sanitize_total_intervals(x):
    return math.ceil(x)

def intervalize_power_rate(kW_value: float, convert_to_MWh=True) -> float:
    """
    Calculate the energy used in an interval from a power rate in kilowatts
    This will return a value in units of MWh by default.
    If convert_to_MWh is false, it will convert to kWh units instead.
    """
    five_min_rate = kW_value / 12
    if convert_to_MWh:
        five_min_rate = five_min_rate / 1000
    return five_min_rate

def get_timezone_from_dict(key, dictionary=TZ_DICTIONARY):
    """
    Retrieve the timezone value from the dictionary based on the given key.

    Parameters:
    -----------
    key : str
        The key whose corresponding timezone value is to be retrieved.
    dictionary : dict, optional
        The dictionary from which to retrieve the value (default is TZ_DICTIONARY).

    Returns:
    --------
    str or None
        The timezone value corresponding to the given key if it exists, otherwise None.
    """
    return dictionary.get(key)


def convert_to_utc(local_time_str, local_tz_str):
    """
    Convert a time expressed in any local time to UTC.

    Parameters:
    -----------
    local_time_str : str
        The local time as a pd.Timestamp.
    local_tz_str : str
        The timezone of the local time as a string, e.g., 'America/New_York'.

    Returns:
    --------
    str
        The time in UTC as a datetime object in the format 'YYYY-MM-DD HH:MM:SS'.

    Example:
    --------
    >>> convert_to_utc(pd.Timestamp('2023-08-29 14:30:00'), 'America/New_York')
    '2023-08-29 18:30:00'
    """
    local_time = datetime.strptime(
        local_time_str.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
    )
    local_tz = pytz.timezone(local_tz_str)
    local_time = local_tz.localize(local_time)
    return local_time.astimezone(pytz.utc)