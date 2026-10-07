"""Anonymized export of a MariaDB/MySQL database.

The source database is copied into a temporary database on the same server,
personal data and secrets are scrubbed there, the temporary database is dumped
into a gzipped SQL file, then dropped. The source database is only read.

Typical usage, from the application directory::

  python -m collectives.utils.anonymize export_anon.sql.gz

The source database defaults to :py:data:`config.SQLALCHEMY_DATABASE_URI`, as
the application resolves it (``config.py`` then ``instance/config.py``). It
requires the ``mariadb``/``mariadb-dump`` (or ``mysql``/``mysqldump``) clients,
and the right to create and drop a database on the server.
"""

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

from flask import Flask
from sqlalchemy import (
    String,
    bindparam,
    cast,
    create_engine,
    func,
    literal,
    select,
    text,
)
from sqlalchemy.engine import make_url

from collectives.models import (
    ActivityType,
    ConfigurationItem,
    ConfirmationToken,
    Event,
    Payment,
    QuestionAnswer,
    Retex,
    UploadedFile,
    User,
)

TEMPORARY_DATABASE_MARKER = "_anon_"
"""Marker in the name of the temporary database. :py:func:`anonymize_database`
refuses to run on a database whose name does not contain it."""

SECRET_CONFIGURATION_ITEMS = [
    "PAYLINE_MERCHANT_ID",
    "PAYLINE_CONTRACT_NUMBER",
    "EXTRANET_ACCOUNT_ID",
    "SMTP_LOGIN",
]
"""Configuration items emptied in addition to the ``hidden`` ones (passwords,
keys): identifiers of the club accounts on third-party services."""

CONTACT_CONFIGURATION_ITEMS = {
    "CONTACT_EMAIL": "contact@example.org",
    "SUPPORT_EMAIL": "support@example.org",
    "SECRETARIAT_EMAIL": "secretariat@example.org",
}
"""Real addresses of the club, replaced so that a development instance does
not write to them."""

PAYLINE_METADATA_KEPT = {
    "result": None,
    "payment": ["amount", "currency", "action", "mode"],
    "transaction": ["date"],
}
"""Parts of a Payline response kept in ``Payment.raw_metadata`` and
``refund_metadata``: the result and the amount, enough for
:py:class:`collectives.utils.payline.PaymentDetails`. None keeps a part whole.
Buyer, card, order and contract details are dropped."""

DUMP_OPTIONS = ["--single-transaction", "--routines", "--triggers"]
"""Options of ``mariadb-dump``. ``--single-transaction`` gives a consistent
snapshot without locking the source tables."""

ANONYMIZED_TEXT = "[anonymisé]"

ANONYMIZED_PHONE = "0600000000"

ANONYMIZED_MAIL = "contact@example.org"

PHONE_PATTERN = re.compile(
    r"(?<![\w+])(?:(?:\+|00)33[\s.-]?(?:\(0\)[\s.-]?)?|0)[1-9](?:[\s.-]?\d{2}){4}(?!\d)"
)
"""French phone numbers, national or international, with or without
separators."""

MAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _prefixed(prefix, column, suffix=""):
    """SQL expression concatenating a prefix, a column, and a suffix.

    Compiles to ``||`` on SQLite and to ``concat()`` on MariaDB.
    """
    expression = literal(prefix, String) + cast(column, String)
    if suffix:
        expression = expression + literal(suffix, String)
    return expression


def _start_of_year(connection, column):
    """SQL expression of the 1st of January of the year of a date column."""
    if connection.dialect.name == "sqlite":
        return func.date(column, "start of year")
    return func.makedate(func.year(column), 1)


def _rewrite_rows(connection, table, columns, rewrite):
    """Rewrite some columns of every row of a table in Python.

    :param table: Table to rewrite, with an ``id`` primary key.
    :param columns: Names of the columns to rewrite.
    :param rewrite: Function taking the row and returning the new values of
        ``columns``, as a dict.
    """
    rows = connection.execute(
        select(table.c.id, *(table.c[name] for name in columns))
    ).all()
    changes = []
    for row in rows:
        values = rewrite(row)
        if any(values[name] != getattr(row, name) for name in columns):
            changes.append(
                {"row_id": row.id, **{f"new_{k}": v for k, v in values.items()}}
            )
    if changes:
        connection.execute(
            table.update()
            .where(table.c.id == bindparam("row_id"))
            .values({name: bindparam(f"new_{name}") for name in columns}),
            changes,
        )


def scrub_contacts(content):
    """Replace the phone numbers and mail addresses in a text.

    :param content: Text to scrub, or None.
    :type content: string
    :return: The text, with every phone and mail replaced by a fake one.
    :rtype: string
    """
    if not content:
        return content
    content = MAIL_PATTERN.sub(ANONYMIZED_MAIL, content)
    return PHONE_PATTERN.sub(ANONYMIZED_PHONE, content)


def filter_payline_metadata(raw_metadata):
    """Keep only the parts of a Payline response listed in
    :py:data:`PAYLINE_METADATA_KEPT`.

    :param raw_metadata: JSON Payline response, or the details typed for a
        cash or check payment.
    :type raw_metadata: string
    :return: The filtered JSON response; an empty string for anything else
        than a Payline response; None for None.
    :rtype: string
    """
    if raw_metadata is None:
        return None
    try:
        response = json.loads(raw_metadata)
    except ValueError:
        return ""
    if not isinstance(response, dict) or "result" not in response:
        return ""
    kept = {}
    for key, fields in PAYLINE_METADATA_KEPT.items():
        value = response.get(key)
        if isinstance(value, dict) and fields is not None:
            value = {field: value[field] for field in fields if field in value}
        if value is not None:
            kept[key] = value
    return json.dumps(kept)


def _anonymize_users(connection, password):
    """Replace the identity, contacts and password of users."""
    users = User.__table__
    connection.execute(
        users.update().values(
            first_name=_prefixed("Prénom", users.c.id),
            last_name=_prefixed("Nom", users.c.id),
            license=cast(999900000000 + users.c.id, String),
            date_of_birth=_start_of_year(connection, users.c.date_of_birth),
            password=password,
            avatar=None,
            phone="0600000000",
            emergency_contact_name="Contact d'urgence",
            emergency_contact_phone="0600000000",
        )
    )
    connection.execute(
        users.update()
        .where(users.c.mail != "admin")
        .values(mail=_prefixed("user", users.c.id, "@example.org"))
    )
    connection.execute(ConfirmationToken.__table__.delete())


def _anonymize_payments(connection):
    """Drop buyer and card details and Payline session references.

    ``processor_order_ref`` is kept: built from the date, the activity and the
    id, it is printed on receipts and searched by.
    """
    payments = Payment.__table__
    connection.execute(
        payments.update().values(
            processor_token=_prefixed("anon-", payments.c.id), processor_url=None
        )
    )
    _rewrite_rows(
        connection,
        payments,
        ["raw_metadata", "refund_metadata"],
        lambda row: {
            "raw_metadata": filter_payline_metadata(row.raw_metadata),
            "refund_metadata": filter_payline_metadata(row.refund_metadata),
        },
    )


def _anonymize_free_texts(connection):
    """Scrub texts typed by members: answers, retex, event descriptions."""
    answers = QuestionAnswer.__table__
    connection.execute(
        answers.update()
        .where(answers.c.value.is_not(None))
        .values(value=ANONYMIZED_TEXT)
    )

    retex = Retex.__table__
    connection.execute(
        retex.update().values(
            description=ANONYMIZED_TEXT, rendered_description=ANONYMIZED_TEXT
        )
    )

    _rewrite_rows(
        connection,
        Event.__table__,
        ["description", "rendered_description"],
        lambda row: {
            "description": scrub_contacts(row.description),
            "rendered_description": scrub_contacts(row.rendered_description),
        },
    )


def _anonymize_uploads(connection):
    """Replace the original file names, keeping date prefix and extension."""

    def rewrite(row):
        """New name, path and session of an uploaded file row."""
        name_ext = os.path.splitext(row.name)[1]
        path_ext = os.path.splitext(row.path)[1]
        date_prefix = row.path[:9] if re.match(r"\d{2}_\d{2}_\d{2}_", row.path) else ""
        return {
            "name": f"fichier-{row.id}{name_ext}",
            "path": f"{date_prefix}fichier-{row.id}{path_ext}",
            "session_id": None,
        }

    _rewrite_rows(
        connection, UploadedFile.__table__, ["name", "path", "session_id"], rewrite
    )


def _anonymize_configuration(connection):
    """Empty secrets and replace the contact addresses of the club."""
    config = ConfigurationItem.__table__
    connection.execute(
        config.update()
        .where(
            config.c.hidden.is_(True) | config.c.name.in_(SECRET_CONFIGURATION_ITEMS)
        )
        .values(json_content=json.dumps(""))
    )
    for name, mail in CONTACT_CONFIGURATION_ITEMS.items():
        connection.execute(
            config.update()
            .where(config.c.name == name)
            .values(json_content=json.dumps(mail))
        )

    activity_types = ActivityType.__table__
    connection.execute(
        activity_types.update()
        .where(activity_types.c.email.is_not(None) & (activity_types.c.email != ""))
        .values(email=_prefixed("activite-", activity_types.c.id, "@example.org"))
    )


def anonymize(connection, password=None):
    """Scrub personal data and secrets from a database.

    Users keep their id, gender, license category and expiry date, roles and
    badges, so that the anonymized database behaves like the real one. The
    ``admin`` account keeps its mail, so that the application still finds it
    at startup and enforces its password (:py:func:`init_admin`).

    :param connection: Connection to the database to scrub, within a transaction.
    :type connection: :py:class:`sqlalchemy.engine.Connection`
    :param password: Password given to every account, or None to disable logins.
    :type password: string
    """
    _anonymize_users(connection, password)
    _anonymize_payments(connection)
    _anonymize_free_texts(connection)
    _anonymize_uploads(connection)
    _anonymize_configuration(connection)


def anonymize_database(url, password=None):
    """Scrub the temporary database at ``url``, see :py:func:`anonymize`.

    :param url: SQLAlchemy URL of the temporary database.
    :type url: :py:class:`sqlalchemy.engine.URL`
    :param password: Password given to every account, or None to disable logins.
    :type password: string
    """
    if TEMPORARY_DATABASE_MARKER not in (url.database or ""):
        raise ValueError(
            f"Refus d'anonymiser {url.database!r} : ce n'est pas une base temporaire"
        )
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            anonymize(connection, password)
    finally:
        engine.dispose()


def _source_url_from_config():
    """SQLAlchemy URL of the database of the application.

    Loads the configuration like :py:func:`collectives.create_app`, without
    creating the application (no scheduler, no write to the database).
    """
    app = Flask("collectives", instance_relative_config=True)
    app.config.from_object("config")
    app.config.from_pyfile("config.py", silent=True)
    return app.config["SQLALCHEMY_DATABASE_URI"]


def _client_binary(*names):
    """Path of the first available command among ``names``."""
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError(f"Commande introuvable : {' ou '.join(names)}")


def _write_client_options(url):
    """Write the connection settings of ``url`` into a MariaDB option file.

    The password does not appear on the command lines of the clients, which
    any user of the server can read.

    :return: path of the option file, readable only by its owner.
    :rtype: string
    """
    options = {
        "user": url.username,
        "password": url.password,
        "host": url.host,
        "port": url.port,
        "socket": url.query.get("unix_socket"),
        "default-character-set": url.query.get("charset", "utf8mb4"),
    }
    fd, path = tempfile.mkstemp(prefix="collectives-", suffix=".cnf")
    with os.fdopen(fd, "w") as file:
        file.write("[client]\n")
        for key, value in options.items():
            if value is not None:
                escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
                file.write(f'{key}="{escaped}"\n')
    return path


def _copy_database(options_file, source, target):
    """Copy the database ``source`` into the empty database ``target``."""
    dump = subprocess.Popen(  # pylint: disable=consider-using-with
        [
            _client_binary("mariadb-dump", "mysqldump"),
            f"--defaults-extra-file={options_file}",
            *DUMP_OPTIONS,
            source,
        ],
        stdout=subprocess.PIPE,
    )
    try:
        subprocess.run(
            [
                _client_binary("mariadb", "mysql"),
                f"--defaults-extra-file={options_file}",
                target,
            ],
            stdin=dump.stdout,
            check=True,
        )
    finally:
        dump.stdout.close()
        if dump.wait() != 0:
            raise RuntimeError(f"Échec du dump de {source}")


def _dump_database(options_file, database, output):
    """Dump ``database`` into the gzipped SQL file ``output``.

    The file is written under a temporary name and renamed once complete, so
    that a failed export does not leave a truncated file at ``output``.
    """
    partial = f"{output}.part"
    with subprocess.Popen(
        [
            _client_binary("mariadb-dump", "mysqldump"),
            f"--defaults-extra-file={options_file}",
            *DUMP_OPTIONS,
            database,
        ],
        stdout=subprocess.PIPE,
    ) as dump:
        with gzip.open(partial, "wb") as file:
            shutil.copyfileobj(dump.stdout, file)
    if dump.returncode != 0:
        os.unlink(partial)
        raise RuntimeError(f"Échec du dump de {database}")
    os.replace(partial, output)


def export_anonymized(source_url, output, password=None):
    """Export an anonymized copy of the database at ``source_url``.

    The temporary database is dropped even if a step fails.

    :param source_url: SQLAlchemy URL of the MariaDB/MySQL source database.
    :type source_url: string
    :param output: Path of the gzipped SQL file to write.
    :type output: string
    :param password: Password given to every account, or None to disable logins.
    :type password: string
    """
    url = make_url(source_url)
    if url.get_backend_name() != "mysql":
        raise ValueError(f"Base MariaDB/MySQL attendue, pas {url.get_backend_name()}")
    source = url.database
    target = f"{source}{TEMPORARY_DATABASE_MARKER}{datetime.now():%Y%m%d%H%M%S}"
    if not re.fullmatch(r"\w{1,64}", target):
        raise ValueError(f"Nom de base temporaire invalide : {target!r}")

    engine = create_engine(url)
    options_file = _write_client_options(url)
    try:
        with engine.connect() as connection:
            charset, collation = connection.execute(
                text(
                    "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                    "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = :name"
                ),
                {"name": source},
            ).one()
            connection.execute(
                text(
                    f"CREATE DATABASE `{target}` "
                    f"CHARACTER SET {charset} COLLATE {collation}"
                )
            )
        try:
            print(f"Copie de {source} vers {target}…", file=sys.stderr)
            _copy_database(options_file, source, target)
            print(f"Anonymisation de {target}…", file=sys.stderr)
            anonymize_database(url.set(database=target), password)
            print(f"Dump de {target} vers {output}…", file=sys.stderr)
            _dump_database(options_file, target, output)
        finally:
            with engine.connect() as connection:
                connection.execute(text(f"DROP DATABASE IF EXISTS `{target}`"))
            print(f"Base {target} supprimée.", file=sys.stderr)
    finally:
        os.unlink(options_file)
        engine.dispose()


def main(argv=None):
    """Command line entry point, see the module documentation."""
    parser = argparse.ArgumentParser(
        prog="python -m collectives.utils.anonymize",
        description="Exporte une copie anonymisée de la base MariaDB.",
    )
    parser.add_argument("output", help="fichier SQL gzippé à écrire")
    parser.add_argument(
        "--source-url",
        help="URL SQLAlchemy de la base source "
        "(par défaut : SQLALCHEMY_DATABASE_URI de la configuration)",
    )
    parser.add_argument(
        "--password",
        help="mot de passe donné à tous les comptes "
        "(par défaut : aucun, connexions impossibles sauf admin)",
    )
    args = parser.parse_args(argv)

    export_anonymized(
        args.source_url or _source_url_from_config(), args.output, args.password
    )


if __name__ == "__main__":
    main()
