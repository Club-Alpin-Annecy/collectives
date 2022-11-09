""" Module to help generate Volunteer certificate. """

import textwrap
from datetime import date

from flask import flash, redirect, url_for
from PIL import Image, ImageDraw, ImageFont

from collectives.models import Configuration, Gender


def generate_image(president, user):
    """Generate an image containing the volunteer certificate.

    :param president:
    :type president: :py:class:`collectives.models.user.User`
    :param user:
    :type user: :py:class:`collectives.models.user.User`
    :returns: The image of the volunteer certificate
    :rtype: :py:class:`PIL.Image`
    """

    # Generate template with watermark
    template = Image.open(Configuration.VOLUNTEER_CERT_IMAGE)
    image = generate_background(template, user)

    # usefull variables
    font_file_bold = "collectives/static/fonts/DINWeb-Bold.woff"
    font = ImageFont.truetype("collectives/static/fonts/DINWeb.woff", 45)
    font_bold = ImageFont.truetype(font_file_bold, 45)
    text_color = (0, 0, 0)
    width = template.size[0]

    # Add Header text
    ImageDraw.Draw(image).multiline_text(
        (width / 2, 600),
        "Attestation de fonction Bénévole\nau CAF d'Annecy",
        text_color,
        font=ImageFont.truetype(font_file_bold, 80),
        anchor="ms",
        align="center",
    )

    # Add Main text
    conjugate = "e" if user.gender == Gender.Woman else ""
    club_name = "Club Alpin Français d'Annecy (74)"
    if user.license_expiry_date:
        expiry = user.license_expiry_date.year
    elif user.is_test:
        expiry = 1789  # Default year if user is a test user
    else:
        flash("""Erreur de date de license. Contactez le support.""", "error")
        return redirect(url_for("profile.show_user", user_id=user.id))

    # Start drawing main text
    current_line_position = 0
    text = "Je soussigné, "
    ImageDraw.Draw(image).multiline_text(
        (350, 900),
        text,
        text_color,
        font=font,
        spacing=10,
    )
    current_line_position = ImageDraw.Draw(image).textlength(
        text, font=font
    )
    text = f"{president.full_name().upper()}"
    ImageDraw.Draw(image).multiline_text(
        (350 + current_line_position, 900),
        text,
        text_color,
        font=font_bold,
        spacing=10,
    )
    current_line_position += ImageDraw.Draw(image).textlength(
        text, font=font_bold
    )
    ImageDraw.Draw(image).multiline_text(
        (350 + current_line_position, 900),
        f", président du {club_name},",
        text_color,
        font=font,
        spacing=10,
    )
    ImageDraw.Draw(image).multiline_text(
        (270, 975),
        "certifie que:",
        text_color,
        font=font,
        spacing=10,
    )

    text = f"{user.form_of_address()}"
    ImageDraw.Draw(image).multiline_text(
        (400, 1100),
        text,
        text_color,
        font=font,
        spacing=10,
    )
    current_line_position = ImageDraw.Draw(image).textlength(
        text, font=font
    )
    text = f"{user.full_name()}"
    ImageDraw.Draw(image).multiline_text(
        (600 + current_line_position, 1100),
        text,
        text_color,
        font=font_bold,
        spacing=10,
    )
    current_line_position += ImageDraw.Draw(image).textlength(
        text, font=font_bold
    )
    ImageDraw.Draw(image).multiline_text(
        (600 + current_line_position, 1100),
        f", né{conjugate} le {user.date_of_birth.strftime('%d/%m/%Y')}, ",
        text_color,
        font=font,
        spacing=10,
    )

    text = (
        f"est licencié{conjugate} au {club_name}\n"
        "sous le numéro d'adhérent: "
        f"{user.license}"
    )
    ImageDraw.Draw(image).multiline_text(
        (width / 2, 1300),
        "\n".join([textwrap.fill(line, width=80) for line in text.split("\n")]),
        text_color,
        font=font_bold,
        anchor="ms",
        align="center",
        spacing=45,
    )

    text = (
        f"est membre de la FFCAM, la Fédération "
        "Française des Clubs Alpins et de Montagne, est à jour de cotisation "
        f"pour l'année en cours, du 1er septembre {expiry-1} au 30 septembre "
        f"{expiry}, "
    )
    ImageDraw.Draw(image).multiline_text(
        (width / 2, 1450),
        "\n".join([textwrap.fill(line, width=80) for line in text.split("\n")]),
        text_color,
        font=font,
        anchor="ms",
        align="center",
        spacing=30,
    )

    text = f"et est Bénévole reconnu{conjugate} au sein de notre association."
    ImageDraw.Draw(image).multiline_text(
        (width / 2, 1650),
        "\n".join([textwrap.fill(line, width=80) for line in text.split("\n")]),
        text_color,
        font=font_bold,
        anchor="ms",
        align="center",
        spacing=45,
    )

    text = (
        f"Nom et adresse de la structure:\n        {club_name}\n"
        "        17 rue du Mont Blanc\n"
        "        74000 Annecy\n"
        "        www.cafannecy.fr\n\n"
        "Pour toute question ou réclamation concernant l'attestation: "
        "partenaires@cafannecy.fr\n\n"
        "Ces informations sont certifiées conformes."
    )
    ImageDraw.Draw(image).multiline_text(
        (270, 1800),
        "\n".join([textwrap.fill(line, width=90) for line in text.split("\n")]),
        text_color,
        font=font,
        spacing=40,
    )

    ImageDraw.Draw(image).multiline_text(
        (1580, 2550),
        f"Fait à Annecy le {date.today().strftime('%d/%m/%Y')}\n"
        "Cachet et signature du président",
        text_color,
        font=font,
        spacing=10,
    )

    return image

def generate_background(template, user):
    """Generate an image containing the volunteer certificate.

    :param template:
    :type template: :py:class:`PIL.Image`
    :param user:
    :type user: :py:class:`collectives.models.user.User`
    :returns: The template image with the rotated watermark
    :rtype: :py:class:`PIL.Image`
    """

    font = ImageFont.truetype("collectives/static/fonts/DINWeb.woff", 45)
    size = template.size

    image = Image.new("RGBA", (int(size[0] * 1.2), int(size[1] * 1.1)), "#ffffff")
    watermark_text = f"{user.full_name()} - {user.license} - " * 6
    watermark_text = [" " * 20 * (i % 4) + watermark_text + "\n" for i in range(75)]
    watermark_text = "\n".join(watermark_text)
    ImageDraw.Draw(image).multiline_text(
        (-1000, 0),
        watermark_text,
        "#00000018",
        font=font,
        spacing=-10,
    )
    image = image.rotate(10)
    image = image.crop((size[0] * 0.1, size[1] * 0.05, size[0] * 1.1, size[1] * 1.05))
    image.paste(template, (0, 0), template)

    return image
