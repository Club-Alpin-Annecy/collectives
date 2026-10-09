#! /usr/bin/env python
"""Faux serveur Loxya pour le développement local, sans dépendance.

Reproduit, avec un état en mémoire, la partie de l'API Loxya qu'utilise
l'intégration, telle qu'observée sur l'instance réelle (Loxya v1.3.11-premium) ::

    python etc/loxya_stub.py [--port 5055]

Pour y brancher l'application : activer ``LOXYA_ENABLED`` (``instance/config.py``,
ou ``FLASK_APP='collectives:create_app(extra_config={"LOXYA_ENABLED": True})'``),
puis saisir dans Configuration → Loxya l'URL du stub et les identifiants
``dev`` / ``dev``. ``GET /_stub/state`` montre son état.

Les pièges de l'instance sont reproduits volontairement :

- un ``DELETE`` sur une ressource déjà à la corbeille la **purge** ;
- ``GET`` et ``PUT`` sur une ressource à la corbeille répondent 404 ;
- ``PUT`` remplace l'objet entier : un champ absent est effacé ;
- l'e-mail n'est unique que parmi les comptes de connexion, et un doublon est
  refusé par un 400, pas un 409 ;
- mettre un bénéficiaire à la corbeille laisse son compte actif, et purger un
  compte laisse son bénéficiaire, ``user_id`` remis à ``null`` ;
- bénéficiaires et comptes ont des identifiants distincts — sur l'instance ils
  coïncident souvent, ce qui masque une confusion ; ici, elle échoue.
"""

import argparse
import json
import logging
import re
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

LOGGER = logging.getLogger("loxya_stub")

CREDENTIALS = {"identifier": "dev", "password": "dev"}
""" Identifiants acceptés par ``POST /api/session``. """

BENEFICIARY_FIELDS = (
    "first_name",
    "last_name",
    "reference",
    "email",
    "phone",
    "note",
    "country",
    "can_make_reservation",
)
""" Champs d'un bénéficiaire conservés par le stub. """

STATE = {
    "tokens": set(),
    "beneficiaries": {},
    "users": {},
    "next_id": {"b": 1, "u": 101},
}
""" État en mémoire. Comptes numérotés à partir de 101, bénéficiaires à partir de 1. """


def new_id(kind: str) -> int:
    """Alloue un identifiant de bénéficiaire (``b``) ou de compte (``u``)."""
    STATE["next_id"][kind] += 1
    return STATE["next_id"][kind] - 1


def live(store: str, key: int) -> dict:
    """Renvoie la ressource si elle existe et n'est pas à la corbeille."""
    item = STATE[store].get(key)
    return item if item and not item["deleted"] else None


def account_errors(body: dict, user: dict = None) -> dict:
    """Valide les champs d'un compte de connexion, comme l'instance.

    L'unicité du pseudo n'a pas été observée ; elle est supposée.
    """
    errors = {}
    if user is None:
        for field in ("pseudo", "email", "password"):
            if not body.get(field):
                errors[field] = "Ce champ est obligatoire."
    for field, message in (
        ("email", "Cette adresse e-mail est déjà utilisée."),
        ("pseudo", "Cet identifiant est déjà utilisé."),
    ):
        value = body.get(field)
        if value and any(
            u[field] == value and u is not user
            for u in STATE["users"].values()
            if not u["deleted"]
        ):
            errors[field] = message
    return errors


def beneficiary_payload(beneficiary: dict) -> dict:
    """Représentation d'un bénéficiaire, dans la forme renvoyée par Loxya."""
    user = STATE["users"].get(beneficiary["user_id"])
    return {
        **{field: beneficiary.get(field) for field in BENEFICIARY_FIELDS},
        "id": beneficiary["id"],
        "user_id": beneficiary["user_id"],
        "is_deleted": beneficiary["deleted"],
        "user": None if user is None else user_payload(user),
    }


def user_payload(user: dict) -> dict:
    """Représentation d'un compte de connexion."""
    return {key: user[key] for key in ("id", "pseudo", "email", "group")}


class Handler(BaseHTTPRequestHandler):
    """Routeur HTTP du faux serveur."""

    # pylint: disable=invalid-name

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """Redirige les journaux du serveur vers le logger du module."""
        LOGGER.info("%s", format % args)

    def _body(self) -> dict:
        """Lit le corps JSON de la requête."""
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else {}

    def _reply(self, status: int, payload=None):
        """Écrit une réponse JSON, vide pour un 204."""
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str, details: dict = None):
        """Écrit une erreur dans l'enveloppe de Loxya."""
        self._reply(
            status,
            {
                "success": False,
                "error": {"code": status, "message": message, "details": details},
            },
        )

    def _route(self, method: str):
        """Authentifie la requête puis la confie au gestionnaire de sa route."""
        url = urlparse(self.path)
        if method == "GET" and url.path == "/_stub/state":
            state = {k: v for k, v in STATE.items() if k in ("beneficiaries", "users")}
            return self._reply(200, state)
        if method == "POST" and url.path == "/api/session":
            if self._body() != CREDENTIALS:
                return self._error(401, "Bad credentials.")
            token = uuid.uuid4().hex
            STATE["tokens"].add(token)
            return self._reply(200, {"token": token})

        token = self.headers.get("Authorization", "").removeprefix("Bearer ")
        if token not in STATE["tokens"]:
            return self._error(401, "Unauthenticated.")

        for pattern, handler in ROUTES[method]:
            match = re.fullmatch(pattern, url.path)
            if match:
                return handler(
                    self, *map(int, match.groups()), query=parse_qs(url.query)
                )
        return self._error(404, f"No route for {method} {url.path}")

    def do_GET(self):
        """Traite les requêtes GET."""
        self._route("GET")

    def do_POST(self):
        """Traite les requêtes POST."""
        self._route("POST")

    def do_PUT(self):
        """Traite les requêtes PUT."""
        self._route("PUT")

    def do_DELETE(self):
        """Traite les requêtes DELETE."""
        self._route("DELETE")

    # -- Bénéficiaires -----------------------------------------------------

    def create_beneficiary(self, query):
        """Crée un bénéficiaire, et son compte si les réservations en ligne sont permises."""
        body = self._body()
        with_account = bool(body.get("can_make_reservation"))
        errors = account_errors(body) if with_account else {}
        if errors:
            return self._error(400, "Validation failed.", errors)
        beneficiary = {"id": new_id("b"), "user_id": None, "deleted": False}
        beneficiary.update({field: body.get(field) for field in BENEFICIARY_FIELDS})
        if with_account:
            beneficiary["user_id"] = self._create_user(body)
        STATE["beneficiaries"][beneficiary["id"]] = beneficiary
        return self._reply(201, beneficiary_payload(beneficiary))

    def _create_user(self, body: dict) -> int:
        """Crée le compte de connexion d'un bénéficiaire et renvoie son identifiant."""
        user = {"id": new_id("u"), "pseudo": body["pseudo"], "email": body["email"]}
        user.update(group="external", deleted=False)
        STATE["users"][user["id"]] = user
        return user["id"]

    def list_beneficiaries(self, query):
        """Recherche par sous-chaîne, sans casse, sur nom, prénom, e-mail et référence."""
        deleted = query.get("deleted", ["0"])[0] == "1"
        terms = [t.casefold() for t in query.get("search", [])]
        fields = ("first_name", "last_name", "email", "reference")
        matches = [
            beneficiary_payload(b)
            for b in STATE["beneficiaries"].values()
            if b["deleted"] == deleted
            and all(
                any(t in (b.get(f) or "").casefold() for f in fields) for t in terms
            )
        ]
        limit = int(query.get("limit", ["100"])[0])
        return self._reply(
            200, {"data": matches[:limit], "pagination": {"total": len(matches)}}
        )

    def get_beneficiary(self, beneficiary_id, query):
        """Fiche d'un bénéficiaire ; 404 s'il est à la corbeille."""
        beneficiary = live("beneficiaries", beneficiary_id)
        if beneficiary is None:
            return self._error(404, "Not found.")
        return self._reply(200, beneficiary_payload(beneficiary))

    def replace_beneficiary(self, beneficiary_id, query):
        """Remplace un bénéficiaire ; lui ajoute un compte s'il passe en réservation en ligne."""
        beneficiary = live("beneficiaries", beneficiary_id)
        if beneficiary is None:
            return self._error(404, "Not found.")
        body = self._body()
        user = STATE["users"].get(beneficiary["user_id"])
        if body.get("can_make_reservation"):
            errors = account_errors(body, user)
            if errors:
                return self._error(400, "Validation failed.", errors)
            if user is None:
                beneficiary["user_id"] = self._create_user(body)
        beneficiary.update({field: body.get(field) for field in BENEFICIARY_FIELDS})
        return self._reply(200, beneficiary_payload(beneficiary))

    # -- Commun aux bénéficiaires et aux comptes ---------------------------

    def delete(self, store: str, key: int):
        """Met à la corbeille, ou purge une ressource déjà à la corbeille."""
        item = STATE[store].get(key)
        if item is None:
            return self._error(404, "Not found.")
        if not item["deleted"]:
            item["deleted"] = True
            return self._reply(204)
        del STATE[store][key]
        LOGGER.warning("%s %d PURGÉ (second DELETE)", store, key)
        if store == "users":
            for beneficiary in STATE["beneficiaries"].values():
                if beneficiary["user_id"] == key:
                    beneficiary["user_id"] = None
        return self._reply(204)

    def restore(self, store: str, key: int):
        """Sort une ressource de la corbeille ; 404 si elle a été purgée."""
        item = STATE[store].get(key)
        if item is None:
            return self._error(404, "Not found.")
        item["deleted"] = False
        payload = (
            beneficiary_payload(item)
            if store == "beneficiaries"
            else user_payload(item)
        )
        return self._reply(200, payload)

    def get_user(self, user_id, query):
        """Fiche d'un compte ; 404 s'il est à la corbeille."""
        user = live("users", user_id)
        if user is None:
            return self._error(404, "Not found.")
        return self._reply(200, user_payload(user))


ROUTES = {
    "GET": [
        (r"/api/beneficiaries", Handler.list_beneficiaries),
        (r"/api/beneficiaries/(\d+)", Handler.get_beneficiary),
        (r"/api/users/(\d+)", Handler.get_user),
    ],
    "POST": [(r"/api/beneficiaries", Handler.create_beneficiary)],
    "PUT": [
        (
            r"/api/beneficiaries/restore/(\d+)",
            lambda h, k, query: h.restore("beneficiaries", k),
        ),
        (r"/api/users/restore/(\d+)", lambda h, k, query: h.restore("users", k)),
        (r"/api/beneficiaries/(\d+)", Handler.replace_beneficiary),
    ],
    "DELETE": [
        (r"/api/beneficiaries/(\d+)", lambda h, k, query: h.delete("beneficiaries", k)),
        (r"/api/users/(\d+)", lambda h, k, query: h.delete("users", k)),
    ],
}
""" Routes de l'API, par verbe : motif du chemin et gestionnaire. """


def main():
    """Démarre le faux serveur."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=5055, help="port d'écoute")
    port = parser.parse_args().port
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    LOGGER.info("Faux serveur Loxya sur http://localhost:%d (dev / dev)", port)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
