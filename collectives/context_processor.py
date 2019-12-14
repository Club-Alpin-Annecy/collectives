# Helpers functions that are make available to Jinja

def helpers_processor():
    def format_date(datetime):
        return str(datetime.date())
    
    def format_time(datetime):
        return str(datetime.time())

    def format_datetime_range(start, end):
        if start.date() == end.date():
            return 'le {} de {} à {}'.format(format_date(start), format_time(start), format_time(end))
        return 'du {} à {} au {} à {}'.format(format_date(start), format_time(start), format_date(end), format_time(end))

    return dict(format_date = format_date, format_time = format_time, 
                format_datetime_range = format_datetime_range)