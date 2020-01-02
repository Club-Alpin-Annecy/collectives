from flask import current_app
from datetime import datetime
from dateutil import tz
import re
import unicodedata

def current_time():
    tz_name = current_app.config['TZ_NAME']
    tz_info = tz.gettz(tz_name)
    now = datetime.now(tz_info)
    # Datetimes are stored in naive format, assumed to
    # always be in the correct timezone
    # For Python to allow comparisons we need to strip the 
    # tz information from our local time
    return now.replace(tzinfo = None)


_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    
    From Django's "django/template/defaultfilters.py".
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = _slugify_strip_re.sub('', value.decode('ascii')).strip().lower()
    return _slugify_hyphenate_re.sub('-', value)