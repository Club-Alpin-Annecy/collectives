"""Form for statistics display and parameters"""

from datetime import date

from wtforms import SelectField, SubmitField

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.models import Event
from collectives.utils.time import get_ffcam_year


class StatisticsParametersForm(ActivityTypeSelectionForm):
    """Parameters for statistics page"""

    ALL_ACTIVITIES = 999999
    """ Id for all activity choice in `activity_id`"""

    year = SelectField()
    """ Year to display """

    submit = SubmitField(label="Sélectionner")
    """ Submit button for regular HTML display """

    excel = SubmitField(label="Export Excel")
    """ Submit button for excel download """

    def __init__(self, *args, **kwargs):
        """Creates a new form"""
        current_year = get_ffcam_year(date.today())

        super().__init__(*args, all_enabled=True, year=current_year, **kwargs)
        self.activity_id.choices = [
            (self.ALL_ACTIVITIES, "Toutes activités"),
            *self.activity_id.choices,
        ]

        first_event = Event.query.order_by(Event.start).first()
        first_year = get_ffcam_year(first_event.start)

        self.year.choices = [
            (year, f"Année {year}/{year + 1}")
            for year in range(current_year, first_year - 1, -1)
        ]

    class Meta:
        """Form meta parameters"""

        csrf = False
        """ CSRF parameter.
        
        It is deactivated for this form"""
