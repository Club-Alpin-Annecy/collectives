"""Module containing forms for uploading documents"""

from flask_login import current_user
from flask_wtf.file import FileAllowed, FileField
from wtforms.validators import DataRequired

from ..models.upload import documents
from .activity_type import ActivityTypeSelectionForm


class AddActivityDocumentForm(ActivityTypeSelectionForm):
    """Form for supervisors to upload activity documents"""

    document_file = FileField(
        "Document à télécharger",
        validators=[
            DataRequired(),
            FileAllowed(documents, "Type de fichier non accepté"),
        ],
    )

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""
        activity_list = current_user.get_supervised_activities()
        submit_label = "Ajouter un document"
        super().__init__(
            *args, activity_list=activity_list, submit_label=submit_label, **kwargs
        )
