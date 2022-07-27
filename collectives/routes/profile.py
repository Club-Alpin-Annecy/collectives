""" Module for profile related route

This modules contains the /profile Blueprint
"""
from datetime import date
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.generic import DecodedStreamObject, EncodedStreamObject, NameObject
from flask import send_file, abort

from flask import flash, render_template, redirect, url_for, request
from flask import Blueprint
from flask_login import current_user
from flask_images import Images

from ..utils.access import valid_user
from ..forms import UserForm
from ..models import User, Role, db
from .auth import sync_user

images = Images()

blueprint = Blueprint("profile", __name__, url_prefix="/profile")


@blueprint.before_request
@valid_user()
def before_request():
    """Protect all profile from unregistered access"""
    pass


@blueprint.route("/user/<user_id>", methods=["GET"])
def show_user(user_id):
    """Route to show detail of a regular user.

    :param int user_id: Primary key of the user.
    """
    if int(user_id) != current_user.id:
        if not current_user.has_any_role():
            flash("Non autorisé", "error")
            return redirect(url_for("event.index"))
        if not current_user.has_signed_ca():
            flash(
                """Vous devez signer la charte RGPD avant de pouvoir
                     accéder à des informations des utilisateurs""",
                "error",
            )
            return redirect(url_for("profile.confidentiality_agreement"))

    user = User.query.filter_by(id=user_id).first()

    return render_template("profile.html", title="Profil adhérent", user=user)


@blueprint.route("/organizer/<leader_id>", methods=["GET"])
def show_leader(leader_id):
    """Route to show leader details of a user.

    :param int user_id: Primary key of the user.
    """
    user = User.query.filter_by(id=leader_id).first()

    # For now allow getting information about any user with roles
    # Limit to leaders of events the user is registered to?
    if user is None or not user.can_create_events():
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    return render_template(
        "leader_profile.html",
        title="Profil adhérent",
        user=user,
    )


@blueprint.route("/user/edit", methods=["GET", "POST"])
def update_user():
    """Route to update current user information"""

    form = UserForm(obj=current_user)

    if not form.validate_on_submit():
        form.password.data = None
        return render_template(
            "basicform.html",
            form=form,
            title="Profil adhérent",
        )

    user = current_user

    # Do not touch password if user does not want to change it
    if form.password.data == "":
        delattr(form, "password")

    form.populate_obj(user)

    # Save avatar into UploadSet
    if form.remove_avatar and form.remove_avatar.data:
        user.delete_avatar()
    user.save_avatar(UserForm().avatar_file.data)

    db.session.add(user)
    db.session.commit()

    return redirect(url_for("profile.update_user"))


@blueprint.route("/user/force_sync", methods=["POST"])
def force_user_sync():
    """Route to force user synchronisation with extranet"""
    sync_user(current_user, True)
    return redirect(url_for("profile.show_user", user_id=current_user.id))


@blueprint.route("/user/confidentiality", methods=["GET", "POST"])
def confidentiality_agreement():
    """Route to show confidentiality agreement."""
    if (
        request.method == "POST"
        and current_user.confidentiality_agreement_signature_date == None
    ):
        current_user.confidentiality_agreement_signature_date = datetime.now()
        db.session.add(current_user)
        db.session.commit()
        flash("Merci d'avoir signé la charte RGPD", "success")

    return render_template("confidentiality_agreement.html", title="Charte RGPD")


@blueprint.route("/my_payments", methods=["GET"])
def my_payments():
    """Route to show payments associated to the current user"""
    return render_template("profile/my_payments.html", title="Mes paiements")


@blueprint.route("/user/volunteer_card/<user_id>", methods=["GET"])
def show_volunteer_card(user_id):
    """Route to show the volunteer card of a regular user.

    :param int user_id: Primary key of the user.
    """
    if int(user_id) != current_user.id:
        if not current_user.has_any_role():
            flash("Non autorisé", "error")
            return redirect(url_for("event.index"))
        if not current_user.has_signed_ca():
            flash(
                """Vous devez signer la charte RGPD avant de pouvoir
                     accéder à des informations des utilisateurs""",
                "error",
            )
            return redirect(url_for("profile.confidentiality_agreement"))

    president_role = Role.query.filter_by(role_id = "President").first()
    if not president_role:
        # No president in roles table
        abort(500)

    president = president_role.user
    user = User.query.filter_by(id=user_id).first()
    today = date.today()
    if(today.month >= 9):
        season = str(today.year) + "/" + str(today.year+1)
    else:
        season = str(today.year-1) + "/" + str(today.year)

    # Variables for PDF:
    # Prénom: user.first_name
    # Nom: user.last_name
    # Jour: today.day
    # Mois: today.month
    # Année: today.year
    # Année en cours: season
    # Prénom Président: president.first_name
    # Nom Président: president.last_name

    pdf = PdfFileReader(open("./collectives/static/caf/doc/Template_Attestion_benevole.pdf", "rb"))
    page = pdf.getPage(0)
    content = page.extractText()
        

    # Arrive à décoder le PDF apparement, mais ne trouve pas le texte à remplacer
    # generatePDF(user, today, season, president)
    
    return render_template("profile.html", title="Profil adhérent", user=user)

def generatePDF(user, date, season, president):
    """Function to generate the "Attestation Bénévole" of a given user

    :param User user: User object of the volunteer.
    :param datetime date: Today date.
    :param str season: Current season for the card.
    :param User president: User object of the current president.
    """

    # Provide replacements list
    replacements = { 'benevole': 'C\'est moi !'}

    # Load PDF template
    pdf = PdfFileReader(open("./collectives/static/caf/doc/Template_Attestion_benevole.pdf", "rb"))

    # Prepare PDF output
    writer = PdfFileWriter()

    # Check on each pages of the document
    for page_number in range(0, pdf.getNumPages()):
        page = pdf.getPage(page_number)
        contents = page.getContents()

        if isinstance(contents, DecodedStreamObject) or isinstance(contents, EncodedStreamObject):
            process_pdf_data(contents, replacements)
        elif len(contents) > 0:
            for obj in contents:
                if isinstance(obj, DecodedStreamObject) or isinstance(obj, EncodedStreamObject):
                    streamObj = obj.getObject()
                    process_pdf_data(streamObj, replacements)

        # Force content replacement
        page[NameObject("/Contents")] = contents.decodedSelf
        writer.addPage(page)

    # Save the PDF (We will have to show it live, not save it)
    with open("./collectives/static/caf/doc/test.result.pdf", 'wb') as out_file:
        writer.write(out_file)

def process_pdf_data(object, replacements):
    """Function to decode / encode data of a pdf page

    :param StreamObject object: Stream of a PDF page.
    :param dict replacements: Dictionnary of the datas to replace.
    """
    data = object.getData()
    #decoded_data = data.decode('utf-8')
    #decoded_data = data.decode('ascii')
    decoded_data = data.decode('iso-8859-1')
    #decoded_data = data.decode('utf-8", "ignore')

    replaced_data = replace_text(decoded_data, replacements)

    #encoded_data = replaced_data.encode('utf-8')
    encoded_data = replaced_data.encode('iso-8859-1')
    if object.decodedSelf is not None:
        object.decodedSelf.setData(encoded_data)
    else:
        object.setData(encoded_data)

def replace_text(content, replacements = dict()):
    """Function to decode / encode data of a pdf page

    :param pdf_page content: Decoded pdf page.
    :param dict replacements: Dictionnary of the datas to replace.
    """
    lines = content.splitlines()

    result = ""
    in_text = False

    for line in lines:
        if line == "BT":
            in_text = True

        elif line == "ET":
            in_text = False

        elif in_text:
            cmd = line[-2:]
            if cmd.lower() == 'tj':
                replaced_line = line
                for k, v in replacements.items():
                    replaced_line = replaced_line.replace(k, v)
                result += replaced_line + "\n"
            else:   
                result += line + "\n"
            continue

        result += line + "\n"

    return result