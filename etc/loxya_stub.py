#! /usr/bin/env python
"""Faux serveur Loxya pour le développement local.

Reproduit le sous-ensemble de l'API Loxya utilisé par l'intégration, avec un état en
mémoire : aucun appel ne sort de la machine, aucun identifiant réel n'est nécessaire.

Les routes et les formes de réponse ont été relevées sur l'instance réelle
(https://caf-annecy.loxya.app, Loxya v1.3.11-premium) en observant les appels du
front-end. Voir le plan d'intégration, phase 0.

Usage::

    ./tasks.py stub [-- --token-ttl 30]

Puis, côté application : ``LOXYA_URL=http://localhost:<port>``, identifiants ``dev``/``dev``.

Routes implémentées :

- ``POST   /api/session``                   authentification, renvoie l'utilisateur + un JWT
- ``POST   /api/beneficiaries``             création d'un bénéficiaire (+ son compte)
- ``GET    /api/beneficiaries``             liste paginée, filtrée par ``deleted``
- ``GET    /api/beneficiaries/{id}``        fiche d'un bénéficiaire
- ``PUT    /api/beneficiaries/{id}``        mise à jour — REMPLACEMENT COMPLET
- ``DELETE /api/beneficiaries/{id}``        corbeille, puis suppression définitive
- ``PUT    /api/beneficiaries/restore/{id}` sortie de corbeille
- ``GET    /api/users/{id}``                fiche d'un compte
- ``PUT    /api/users/{id}``                mise à jour (``group``)
- ``DELETE /api/users/{id}``                corbeille, puis suppression définitive
- ``PUT    /api/users/restore/{id}``        sortie de corbeille

Routes de contrôle, propres au stub :

- ``POST   /_stub/reset``                   vide l'état
- ``GET    /_stub/state``                   renvoie l'état complet
- ``POST   /_stub/fail-next``               fait échouer les N prochains appels API

Trois comportements sont reproduits volontairement parce qu'ils sont des pièges :

1. **Un second DELETE supprime définitivement.** Sur une ressource déjà en corbeille,
   ``DELETE`` purge sans retour possible : une désactivation rejouée détruit le compte
   et son historique. C'est ce qui justifie la colonne ``loxya_active``.
2. **L'id du bénéficiaire et celui de son compte diffèrent.** Sur l'instance réelle ils
   coïncidaient, ce qui masque le fait que ce sont deux entités distinctes. Le stub les
   sépare pour que le code qui confond les deux échoue ici plutôt qu'en production.
3. **``PUT`` est un remplacement complet**, pas une fusion : les champs absents du corps
   sont remis à leur valeur par défaut.
"""

import argparse
import base64
import hashlib
import hmac
import json
import logging
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

LOGGER = logging.getLogger("loxya_stub")

SECRET = b"stub-signing-key"
"""Clé de signature des JWT émis par le stub. Sans valeur de sécurité."""

USERNAME = "dev"
PASSWORD = "dev"
"""Identifiants acceptés par ``POST /api/session``."""

TOKEN_TTL = 43200
"""Durée de validité du JWT, en secondes. 12 h, comme l'instance réelle."""

DEFAULT_GROUP = "external"
"""Groupe attribué par Loxya à un compte de bénéficiaire fraîchement créé."""


class State:
    """État en mémoire du faux serveur."""

    def __init__(self):
        """Initialise un état vide."""
        self.beneficiaries: dict = {}
        self.users: dict = {}
        self.next_beneficiary_id: int = 1
        self.next_user_id: int = 101
        """Séquences distinctes : voir le point 2 de la docstring du module."""
        self.fail_next: int = 0

    def reset(self):
        """Vide l'état, comme au démarrage."""
        self.__init__()


STATE = State()


def _b64(payload: bytes) -> str:
    """Encode en base64url sans padding, comme un JWT."""
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()


def make_token(ttl: int) -> str:
    """Forge un JWT HS256 avec les claims de l'instance réelle.

    L'``exp`` est authentique : il permet de développer et de tester le décodage
    d'échéance et la réauthentification côté client.

    :param ttl: durée de validité en secondes
    :return: le JWT encodé
    """
    now = int(time.time())
    header = _b64(json.dumps({"typ": "JWT", "alg": "HS256"}).encode())
    payload = _b64(
        json.dumps(
            {"scope": "auth", "iat": now, "exp": now + ttl, "type": "user", "sub": 1}
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{_b64(hmac.new(SECRET, signing_input, hashlib.sha256).digest())}"


def token_is_valid(token: str) -> bool:
    """Vérifie la signature et l'échéance d'un JWT émis par le stub."""
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        return False

    expected = _b64(
        hmac.new(SECRET, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(signature, expected):
        return False

    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded)).get("exp", 0) > time.time()


def beneficiary_payload(beneficiary: dict) -> dict:
    """Représentation d'un bénéficiaire, dans la forme renvoyée par Loxya."""
    user = STATE.users.get(beneficiary["user_id"])
    return {
        "id": beneficiary["id"],
        "reference": beneficiary["reference"],
        "company_id": None,
        "color": None,
        "can_make_reservation": beneficiary["can_make_reservation"],
        "note": beneficiary["note"],
        "first_name": beneficiary["first_name"],
        "last_name": beneficiary["last_name"],
        "full_name": f"{beneficiary['first_name']} {beneficiary['last_name']}",
        "email": beneficiary["email"],
        "phone": None,
        "street": None,
        "additional_street": None,
        "postal_code": None,
        "administrative_area": None,
        "locality": None,
        "address": None,
        "country": beneficiary.get("country", "FR"),
        "language": "fr",
        "user_id": beneficiary["user_id"],
        "is_invoiceable": True,
        "is_deleted": beneficiary["deleted"],
        "company": None,
        "user": None if user is None else user_payload(user),
        "stats": {"borrowings": 0},
    }


def user_payload(user: dict) -> dict:
    """Représentation d'un compte, dans la forme renvoyée par Loxya."""
    return {
        "id": user["id"],
        "pseudo": user["pseudo"],
        "email": user["email"],
        "group": user["group"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "full_name": f"{user['first_name']} {user['last_name']}",
        "phone": None,
    }


class Handler(BaseHTTPRequestHandler):
    """Routeur HTTP du faux serveur."""

    # pylint: disable=invalid-name

    def log_message(self, format, *args):
        """Redirige les logs du serveur vers le logger du module."""
        LOGGER.info("%s - %s", self.address_string(), format % args)

    # -- utilitaires -------------------------------------------------------

    def _body(self) -> dict:
        """Lit et décode le corps JSON de la requête."""
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else {}

    def _reply(self, status: int, payload=None):
        """Écrit une réponse JSON, ou une réponse vide pour un 204."""
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _error(self, status: int, message: str, details: dict = None):
        """Écrit une erreur dans l'enveloppe utilisée par Loxya."""
        error = {"code": status, "message": message}
        if details is not None:
            error["details"] = details
        return self._reply(status, {"success": False, "error": error})

    def _authenticated(self) -> bool:
        """Vérifie l'en-tête ``Authorization``, et répond 401 si invalide."""
        header = self.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if token and token_is_valid(token):
            return True
        self._error(401, "Unauthenticated.")
        return False

    def _should_fail(self) -> bool:
        """Consomme un échec programmé par ``/_stub/fail-next``, s'il y en a un."""
        if STATE.fail_next > 0:
            STATE.fail_next -= 1
            self._error(500, "Injected failure.")
            return True
        return False

    def _ready(self) -> bool:
        """Raccourci : requête authentifiée et pas d'échec programmé."""
        return self._authenticated() and not self._should_fail()

    # -- routage -----------------------------------------------------------

    def do_POST(self):
        """Traite les requêtes POST."""
        path = urlparse(self.path).path

        if path == "/_stub/reset":
            STATE.reset()
            return self._reply(200, {"reset": True})

        if path == "/_stub/fail-next":
            STATE.fail_next = self._body().get("count", 1)
            return self._reply(200, {"fail_next": STATE.fail_next})

        if path == "/api/session":
            body = self._body()
            if body.get("identifier") != USERNAME or body.get("password") != PASSWORD:
                return self._error(401, "Bad credentials.")
            return self._reply(
                200,
                {
                    "id": 1,
                    "pseudo": USERNAME,
                    "email": f"{USERNAME}@example.org",
                    "group": "administration",
                    "language": "fr",
                    "first_name": "Dev",
                    "last_name": "Stub",
                    "full_name": "Dev Stub",
                    "token": make_token(TOKEN_TTL),
                },
            )

        if not self._ready():
            return None

        if path == "/api/beneficiaries":
            return self._create_beneficiary(self._body())

        return self._error(404, f"No route for POST {path}")

    def do_GET(self):
        """Traite les requêtes GET."""
        parsed = urlparse(self.path)

        if parsed.path == "/_stub/state":
            return self._reply(
                200, {"beneficiaries": STATE.beneficiaries, "users": STATE.users}
            )

        if not self._ready():
            return None

        if parsed.path == "/api/beneficiaries":
            return self._list_beneficiaries(parse_qs(parsed.query))

        match = re.fullmatch(r"/api/beneficiaries/(\d+)", parsed.path)
        if match:
            beneficiary = STATE.beneficiaries.get(int(match.group(1)))
            if beneficiary is None or beneficiary["deleted"]:
                return self._error(404, "Beneficiary not found.")
            return self._reply(200, beneficiary_payload(beneficiary))

        match = re.fullmatch(r"/api/users/(\d+)", parsed.path)
        if match:
            user = STATE.users.get(int(match.group(1)))
            if user is None or user["deleted"]:
                return self._error(404, "User not found.")
            return self._reply(200, user_payload(user))

        return self._error(404, f"No route for GET {parsed.path}")

    def do_PUT(self):
        """Traite les requêtes PUT."""
        path = urlparse(self.path).path

        if not self._ready():
            return None

        # L'id est APRÈS « restore » : c'est la convention de Loxya, pas l'inverse.
        match = re.fullmatch(r"/api/beneficiaries/restore/(\d+)", path)
        if match:
            return self._restore(STATE.beneficiaries, int(match.group(1)), "Beneficiary")

        match = re.fullmatch(r"/api/users/restore/(\d+)", path)
        if match:
            return self._restore(STATE.users, int(match.group(1)), "User")

        match = re.fullmatch(r"/api/beneficiaries/(\d+)", path)
        if match:
            return self._replace_beneficiary(int(match.group(1)), self._body())

        match = re.fullmatch(r"/api/users/(\d+)", path)
        if match:
            user = STATE.users.get(int(match.group(1)))
            if user is None or user["deleted"]:
                return self._error(404, "User not found.")
            user["group"] = self._body().get("group", user["group"])
            return self._reply(200, user_payload(user))

        return self._error(404, f"No route for PUT {path}")

    def do_DELETE(self):
        """Traite les requêtes DELETE."""
        path = urlparse(self.path).path

        if not self._ready():
            return None

        match = re.fullmatch(r"/api/beneficiaries/(\d+)", path)
        if match:
            return self._delete(STATE.beneficiaries, int(match.group(1)), "Beneficiary")

        match = re.fullmatch(r"/api/users/(\d+)", path)
        if match:
            return self._delete(STATE.users, int(match.group(1)), "User")

        return self._error(404, f"No route for DELETE {path}")

    # -- ressources --------------------------------------------------------

    def _create_beneficiary(self, body: dict):
        """Crée un bénéficiaire et, si les réservations sont permises, son compte.

        Reproduit la validation observée : activer ``can_make_reservation`` rend
        ``pseudo``, ``email`` et ``password`` obligatoires.
        """
        details = {}
        if body.get("can_make_reservation"):
            for field in ("pseudo", "email", "password"):
                if not body.get(field):
                    details[field] = "Ce champ est obligatoire."
        if details:
            return self._error(400, "Validation failed.", details)

        email = body.get("email")
        pseudo = body.get("pseudo")
        for user in STATE.users.values():
            if email and user["email"] == email:
                return self._error(409, "Email already in use.")
            if pseudo and user["pseudo"] == pseudo:
                return self._error(409, "Pseudo already in use.")

        user_id = STATE.next_user_id
        STATE.next_user_id += 1
        beneficiary_id = STATE.next_beneficiary_id
        STATE.next_beneficiary_id += 1

        STATE.users[user_id] = {
            "id": user_id,
            "email": email,
            "pseudo": pseudo,
            "group": DEFAULT_GROUP,
            "first_name": body.get("first_name"),
            "last_name": body.get("last_name"),
            "deleted": False,
        }
        STATE.beneficiaries[beneficiary_id] = {
            "id": beneficiary_id,
            "user_id": user_id,
            "first_name": body.get("first_name"),
            "last_name": body.get("last_name"),
            "email": email,
            "reference": body.get("reference"),
            "note": body.get("note"),
            "country": body.get("country", "FR"),
            "can_make_reservation": bool(body.get("can_make_reservation")),
            "deleted": False,
        }
        return self._reply(201, beneficiary_payload(STATE.beneficiaries[beneficiary_id]))

    def _replace_beneficiary(self, beneficiary_id: int, body: dict):
        """Remplace un bénéficiaire. Les champs absents reprennent leur défaut.

        C'est bien un remplacement et non une fusion : envoyer seulement
        ``can_make_reservation`` efface ``reference`` et ``note``.
        """
        beneficiary = STATE.beneficiaries.get(beneficiary_id)
        if beneficiary is None or beneficiary["deleted"]:
            return self._error(404, "Beneficiary not found.")

        beneficiary.update(
            {
                "first_name": body.get("first_name"),
                "last_name": body.get("last_name"),
                "email": body.get("email"),
                "reference": body.get("reference"),
                "note": body.get("note"),
                "country": body.get("country", "FR"),
                "can_make_reservation": bool(body.get("can_make_reservation")),
            }
        )
        return self._reply(200, beneficiary_payload(beneficiary))

    def _delete(self, store: dict, key: int, label: str):
        """Met à la corbeille, ou supprime définitivement si déjà en corbeille.

        Le second appel est irréversible : c'est le comportement de l'instance réelle,
        et le principal risque de l'intégration.
        """
        item = store.get(key)
        if item is None:
            return self._error(404, f"{label} not found.")

        if item["deleted"]:
            del store[key]
            LOGGER.warning(
                "%s %d supprimé DÉFINITIVEMENT (second DELETE sur un élément "
                "déjà en corbeille)",
                label,
                key,
            )
        else:
            item["deleted"] = True
        return self._reply(204)

    def _restore(self, store: dict, key: int, label: str):
        """Sort une ressource de la corbeille."""
        item = store.get(key)
        if item is None:
            return self._error(404, f"{label} not found.")
        item["deleted"] = False
        payload = beneficiary_payload(item) if label == "Beneficiary" else user_payload(item)
        return self._reply(200, payload)

    def _list_beneficiaries(self, query: dict):
        """Liste paginée des bénéficiaires, filtrée par ``deleted`` et ``search``."""
        deleted = query.get("deleted", ["0"])[0] == "1"
        terms = query.get("search[]", []) + query.get("search", [])
        limit = int(query.get("limit", ["100"])[0])
        page = int(query.get("page", ["1"])[0])

        matches = [
            beneficiary_payload(b)
            for b in STATE.beneficiaries.values()
            if b["deleted"] == deleted
            and (
                not terms
                or any(
                    t in ((b["email"] or "") + (b["reference"] or "") + b["last_name"])
                    for t in terms
                )
            )
        ]
        start = (page - 1) * limit
        return self._reply(
            200,
            {
                "data": matches[start : start + limit],
                "pagination": {
                    "perPage": limit,
                    "currentPage": page,
                    "total": {"items": len(matches)},
                },
            },
        )


def main():
    """Point d'entrée : analyse les options et démarre le serveur."""
    # pylint: disable=global-statement
    global TOKEN_TTL

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=5055, help="port d'écoute")
    parser.add_argument(
        "--token-ttl",
        type=int,
        default=TOKEN_TTL,
        help="durée de vie du JWT en secondes (défaut : 43200, comme la prod) ; "
        "une valeur courte permet de tester la réauthentification",
    )
    args = parser.parse_args()
    TOKEN_TTL = args.token_ttl

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    LOGGER.info(
        "Faux serveur Loxya sur http://localhost:%d (identifiants %s/%s, JWT %ds)",
        args.port,
        USERNAME,
        PASSWORD,
        TOKEN_TTL,
    )
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
