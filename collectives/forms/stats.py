"""Form for statistics display and parameters"""

from datetime import date

from wtforms import SelectField, SubmitField

from collectives.forms.activity_type import ActivityTypeSelectionForm


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
        current_year = date.today().year - 2000
        if date.today().month < 9:
            current_year = current_year - 1

        super().__init__(*args, all_enabled=True, year=2000 + current_year, **kwargs)
        self.activity_id.choices = [
            (self.ALL_ACTIVITIES, "Toute activité")
        ] + self.activity_id.choices
        current_year = date.today().year - 2000
        self.year.choices = [
            (2000 + year, f"Année 20{year}/{year+1}")
            for year in range(20, current_year)
        ]

    class Meta:
        """Form meta parameters"""

        csrf = False
        """ CSRF parameter.
        
        It is deactivated for this form"""
