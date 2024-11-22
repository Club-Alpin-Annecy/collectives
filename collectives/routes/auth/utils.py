""" Auth module for miscaleneous functions and classes."""

from datetime import date, datetime

from flask import url_for, current_app
from flask_login import AnonymousUserMixin
from markupsafe import escape
from flask_wtf.csrf import generate_csrf


from collectives.models import db, User, UserType, Configuration
from collectives.utils import extranet


class UnauthenticatedUserMixin(AnonymousUserMixin):
    """Mixin that defines properties for unauthenticated users"""

    # pylint: disable=invalid-name
    @property
    def id(self) -> int:
        """Id for unauthenticated users (always `-1`)"""
        return -1

    # pylint: enable=invalid-name


def sync_user(user: User, force: bool) -> bool:
    """Synchronize user info from extranet.

    Synchronization is done if license has been renewed or if 'force' is True. Test users
    cannot be synchronized.

    :param user: User to synchronize
    :param force: if True, do synchronisation even if licence has been recently renewed.
    :returns: whether the user exists in the source of truth
    """
    if user.enabled and user.type == UserType.Extranet:
        # Check whether the license has been renewed
        license_info = extranet.api.check_license(user.license)
        if not license_info.exists:
            if user.license_expiry_date > date.today():
                current_app.logger.warning(
                    f"User #{user.id} synchronization : licence is not active on extranet "
                    "but active on this site."
                )
                if force:
                    user.license_expiry_date = datetime.today()
                    db.session.add(user)
                    db.session.commit()
                    current_app.logger.warning(
                        f"User #{user.id} synchronization : licence has been updated."
                    )
            return False

        if force or license_info.expiry_date() > user.license_expiry_date:
            # License has been renewd, sync user data from API
            user_info = extranet.api.fetch_user_info(user.license)
            extranet.sync_user(user, user_info, license_info)
            db.session.add(user)
            db.session.commit()

    return True


def get_bad_phone_message(user, emergency=False):
    """Craft a message for user with a bad phone number.

    :param user: User with a bad phone number
    :param emergency: If true, generates a message relative to the emergency number
    :returns: The html safe message to display to the user to help him change phone number.
    """
    phone_number = user.emergency_contact_phone if emergency else user.phone

    if phone_number is None:
        phone = "n'est pas"
    else:
        phone = f"({escape(phone_number)}) est mal"

    if not emergency:
        description = """un encadrant ne pourrait donc pas vous contacter pour vous communiquer
        des informations importantes comme un changement de lieu de rendez-vous, un changement 
        du lieu de la sortie ou l'annulation de la sortie"""
    else:
        description = """le club ne pourrait donc pas contacter vos proches en cas de
        besoin."""

    return f"""Votre numéro de téléphone {"d'urgence " if emergency else ''} {phone} renseigné:
        {description}<br/>
        Veuillez saisir un numéro de téléphone valide dans <a 
        href="https://extranet-clubalpin.com/monespace/">
        votre espace personnel FFCAM </a>, menu "Mes informations", puis resynchronisez vos 
        informations en cliquant 
        <form action="{url_for('profile.force_user_sync')}" method="post" style="display: inline">
            <a onclick="this.closest('form').submit(); return false;" href="#"/>  ici </a>
            <input type="hidden" name="csrf_token" value="{generate_csrf()}"/>
        </form>. <br/>
        <b>Sans cette information, vous ne pourrez pas participer aux collectives.</b> <br/>
        Si besoin, vous pouvez contacter le support à 
        <a href="mailto:{Configuration.SUPPORT_EMAIL}">{Configuration.SUPPORT_EMAIL}</a>.
        """
