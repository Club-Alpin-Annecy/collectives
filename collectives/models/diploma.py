"""Module to describe a diploma
"""
from .globals import db


class DiplomaType(db.Model):
    """Class to describe a diploma type."""

    __tablename__ = "diploma_types"
    """Database table name to store diploma data.

    :type: string"""

    id = db.Column(db.Integer, primary_key=True)
    """Unique id for the diploma type.

    :type: int"""

    title = db.Column(db.Text(), nullable=False, info={"label": "Titre"})
    """Diploma title to display to humans.

    :type: string"""

    reference = db.Column(
        db.String(10),
        nullable=False,
        unique=True,
        info={
            "label": "Reference",
            "description": "Ex: STG-UFALA4",
            "render_kw": {"placeholder": "XXX-XXXX99"},
        },
    )
    """ FFCAM diploma reference.

    Usually a string like "XXX-XXXX99". EG:

    - STG-UFALA4 : UF vers l'autonomie progression sur terrain glaciaire
    - BRV-BFSM40 : INITIATEUR SKI DE RANDONNEE

    :type: string(10)"""

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=False
    )
    """Activity ID to which this diploma is related.

    :type: :py:class:`collectives.models.activitytype.ActivityType`
    """

    activity = db.relationship("ActivityType", back_populates="diploma_types")

    diplomas = db.relationship("Diploma", back_populates="type")


class Diploma(db.Model):
    """Class to describe a user diploma."""

    __tablename__ = "diplomas"

    id = db.Column(db.Integer, primary_key=True)
    """Unique id for the diploma.

    :type: int"""

    user = db.relationship("User", back_populates="diplomas", lazy=True)
    """ User to which the diploma has been issued to.

    :type: :py:class:`collectives.models.user.User`"""

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    """ User id.

    :type: int"""

    type = db.relationship("DiplomaType", back_populates="diplomas", lazy=True)
    """ Type of this diploma.

    :type: :py:class:`collectives.models.diploma.DiplomaType`"""

    type_id = db.Column(db.Integer, db.ForeignKey("diploma_types.id"), nullable=False)
    """ Diploma type id.

    :type: int"""

    obtention = db.Column(db.Date, nullable=True, info={"label": "Obtention"})
    """ Obtention date of this diploma.

    :type: :py:class:`datetime.date`"""

    expiration = db.Column(
        db.Date,
        nullable=True,
        info={
            "label": "Expiration",
            "description": "Laisser vide pour un diplôme sans expiration",
        },
    )
    """ End date of this diploma.

    :type: :py:class:`datetime.date`"""
