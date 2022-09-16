"""Module containing forms for uploading documents
"""

from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired
from flask_login import current_user

from .activity_type import ActivityTypeSelectionForm
from ..models.upload import documents


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
        kwargs["activity_list"] = current_user.get_supervised_activities()
        kwargs["submit_label"] = "Ajouter un document"
        super().__init__(*args, **kwargs)
