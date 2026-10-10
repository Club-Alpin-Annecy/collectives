"""Form to filter the raw database export."""

from datetime import date

from wtforms import SelectField, SubmitField

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.models import Event
from collectives.utils.time import get_ffcam_year


class DatabaseExportForm(ActivityTypeSelectionForm):
    """Parameters for the raw database export.

    The filter dimensions are the FFCAM ``year`` and the ``activity_id``, the
    same as the statistics page. There is no event type filter.
    """

    year = SelectField("Année", coerce=int)
    """ FFCAM year to export """

    submit = SubmitField("Exporter la base de données")

    def __init__(self, *args, **kwargs):
        """Creates a new form with the year choices derived from the events."""
        current_year = get_ffcam_year(date.today())

        super().__init__(
            *args,
            all_enabled=True,
            activity_id=ActivityTypeSelectionForm.ALL_ACTIVITIES,
            year=current_year,
            **kwargs,
        )

        first_event = Event.query.order_by(Event.start).first()
        first_year = get_ffcam_year(first_event.start) if first_event else current_year

        self.year.choices = [
            (year, f"Année {year}/{year + 1}")
            for year in range(current_year, first_year - 1, -1)
        ]
