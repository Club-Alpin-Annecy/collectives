""" Module for payment related routes

This modules contains the /payment Blueprint
"""

from flask import Blueprint, redirect, url_for
from flask import render_template, current_app, flash
from flask_login import current_user
from ..utils.access import supervisor_required, valid_user, confidentiality_agreement
from ..forms import DiplomaTypeCreationForm, DiplomaForm
from ..models import DiplomaType, Diploma, db


blueprint = Blueprint("diploma", __name__, url_prefix="/diploma")
""" Event blueprint

This blueprint contains all routes for event display and management
"""


@blueprint.before_request
@valid_user()
@supervisor_required()
@confidentiality_agreement()
def before_request():
    """Protect all of the payment endpoints.

    Protection is done by the decorator :py:func:`collectives.utils.access.supervisor_required`
    """
    pass


@blueprint.route("/", methods=["GET"])
def index():
    """Main endpoint for diploma.

    Display current diploma types, diplomas and diploma attribution form. This page
    displays informations regarding the supervised activities of the user.
    """
    activities = current_user.get_supervised_activities()
    activities_id = [a.id for a in activities]
    diploma_types = DiplomaType.query.filter(DiplomaType.activity_id.in_(activities_id))
    diploma_types = diploma_types.order_by(DiplomaType.activity_id).all()

    form = DiplomaForm()

    return render_template(
        "diploma/index.html",
        conf=current_app.config,
        activities=activities,
        diploma_types=diploma_types,
        form=form,
    )


@blueprint.route("/type/add", methods=["GET", "POST"])
@blueprint.route("/type/<type_id>", methods=["GET", "POST"])
def edit_type(type_id=None):
    """ Endpoint to add or edit a new diploma type. """
    diploma_type = DiplomaType() if type_id is None else DiplomaType.query.get(type_id)
    if type_id is None:
        form = DiplomaTypeCreationForm()
    else:
        form = DiplomaTypeCreationForm(obj=diploma_type)

    if type_id == None:
        title = "Ajout d'un type de diplôme"
    else:
        diploma = DiplomaType.query.get(type_id)
        title = f"Gestion d'un type de diplôme: {diploma.reference}"

    if form.validate_on_submit():
        form.populate_obj(diploma_type)
        db.session.add(diploma_type)
        db.session.commit()

        flash(f"Le type {diploma_type.title} a été enregistré avec succès.")
        return redirect(url_for(".index"))

    return render_template(
        "basicform.html", conf=current_app.config, title=title, form=form
    )


@blueprint.route("/type/delete/<type_id>", methods=["POST"])
def delete_type(type_id=None):
    """Delete a diploma type.

    Cascade by deleting the linked diplomas."""
    nb_diplomas = Diploma.query.filter(Diploma.type_id == type_id).delete()

    diploma_type = DiplomaType.query.get(type_id)
    db.session.delete(diploma_type)

    db.session.commit()

    flash(f"Type de diplôme supprimé. {nb_diplomas} diplômes ont aussi été supprimés.")

    return redirect(url_for(".index"))


@blueprint.route("/add", methods=["POST"])
def add_diploma():
    """ Endpoint to add a diplomation to a user. """
    form = DiplomaForm()

    if not form.validate():
        message = "Impossible d'enregistrer ce diplôme: "
        for field, errors in form.errors.items():
            message += f"{ form[field].name }: { ', '.join(errors) }"
        flash(message, "error")
        return redirect(url_for(".index"))

    diploma = Diploma()
    form.populate_obj(diploma)
    db.session.add(diploma)
    db.session.commit()

    flash("Diplôme enregistré", "success")
    return redirect(url_for(".index"))


@blueprint.route("/delete/<diploma_id>", methods=["POST"])
def delete(diploma_id=None):
    """ Endpoint to remove a diploma."""
    diploma = Diploma.query.get(diploma_id)
    db.session.delete(diploma)
    db.session.commit()

    flash("Diplôme supprimé.")

    return redirect(url_for(".index"))
