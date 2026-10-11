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

- un ``DELETE`` sur un bénéficiaire déjà à la corbeille le **purge** ;
- ``GET`` et ``PUT`` sur un bénéficiaire à la corbeille répondent 404 ;
- ``PUT`` remplace l'objet entier : un champ absent est effacé ;
- la recherche se fait par sous-chaîne.

Les comptes de connexion ne sont pas reproduits : l'intégration n'en crée pas.
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

STATE = {"tokens": set(), "beneficiaries": {}, "next_id": 1}
""" État en mémoire. """


def live(key: int) -> dict:
    """Renvoie le bénéficiaire s'il existe et n'est pas à la corbeille."""
    beneficiary = STATE["beneficiaries"].get(key)
    return beneficiary if beneficiary and not beneficiary["deleted"] else None


def beneficiary_payload(beneficiary: dict) -> dict:
    """Représentation d'un bénéficiaire, dans la forme renvoyée par Loxya."""
    return {
        **{field: beneficiary.get(field) for field in BENEFICIARY_FIELDS},
        "id": beneficiary["id"],
        "user_id": None,
        "is_deleted": beneficiary["deleted"],
    }


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
            return self._reply(200, {"beneficiaries": STATE["beneficiaries"]})
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

    def create_beneficiary(self, query):
        """Crée un bénéficiaire."""
        body = self._body()
        beneficiary = {"id": STATE["next_id"], "deleted": False}
        beneficiary.update({field: body.get(field) for field in BENEFICIARY_FIELDS})
        STATE["next_id"] += 1
        STATE["beneficiaries"][beneficiary["id"]] = beneficiary
        return self._reply(201, beneficiary_payload(beneficiary))

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
        beneficiary = live(beneficiary_id)
        if beneficiary is None:
            return self._error(404, "Not found.")
        return self._reply(200, beneficiary_payload(beneficiary))

    def replace_beneficiary(self, beneficiary_id, query):
        """Remplace un bénéficiaire : les champs absents sont effacés."""
        beneficiary = live(beneficiary_id)
        if beneficiary is None:
            return self._error(404, "Not found.")
        body = self._body()
        beneficiary.update({field: body.get(field) for field in BENEFICIARY_FIELDS})
        return self._reply(200, beneficiary_payload(beneficiary))

    def delete_beneficiary(self, beneficiary_id, query):
        """Met à la corbeille, ou purge un bénéficiaire déjà à la corbeille."""
        beneficiary = STATE["beneficiaries"].get(beneficiary_id)
        if beneficiary is None:
            return self._error(404, "Not found.")
        if beneficiary["deleted"]:
            del STATE["beneficiaries"][beneficiary_id]
            LOGGER.warning("Bénéficiaire %d PURGÉ (second DELETE)", beneficiary_id)
        else:
            beneficiary["deleted"] = True
        return self._reply(204)

    def restore_beneficiary(self, beneficiary_id, query):
        """Sort un bénéficiaire de la corbeille ; 404 s'il a été purgé."""
        beneficiary = STATE["beneficiaries"].get(beneficiary_id)
        if beneficiary is None:
            return self._error(404, "Not found.")
        beneficiary["deleted"] = False
        return self._reply(200, beneficiary_payload(beneficiary))


ROUTES = {
    "GET": [
        (r"/api/beneficiaries", Handler.list_beneficiaries),
        (r"/api/beneficiaries/(\d+)", Handler.get_beneficiary),
    ],
    "POST": [(r"/api/beneficiaries", Handler.create_beneficiary)],
    "PUT": [
        (r"/api/beneficiaries/restore/(\d+)", Handler.restore_beneficiary),
        (r"/api/beneficiaries/(\d+)", Handler.replace_beneficiary),
    ],
    "DELETE": [(r"/api/beneficiaries/(\d+)", Handler.delete_beneficiary)],
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
