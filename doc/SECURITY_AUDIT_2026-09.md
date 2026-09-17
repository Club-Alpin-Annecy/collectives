# Audit de sécurité du site Collectives — septembre 2026

Audit de code statique (revue manuelle + vérifications ciblées avec le client de
test Flask) réalisé le 18 septembre 2026 sur la branche `security-audit`
(commit de départ `8de595c`). Périmètre : application Flask `collectives/`,
configuration, déploiement (`Dockerfile`, `deployment/`), CI, dépendances.

Méthode : passage systématique du top 10 OWASP 2021 (A01 contrôle d'accès,
A02 cryptographie, A03 injection, A04 conception, A05 configuration,
A06 composants vulnérables, A07 authentification, A08 intégrité, A09 journalisation,
A10 SSRF), puis axes complémentaires (CSRF, IDOR, mass assignment, rate limiting,
secrets, en-têtes HTTP, cookies, uploads, redirections, exposition d'informations,
CI/CD, Docker).

Les numéros de ligne renvoient à l'état du code au commit `8de595c`.

## Synthèse

| Sévérité | Nombre | Corrigé dans cette branche |
|----------|--------|----------------------------|
| Critique | 3      | C1, C2 corrigés ; C3 partiellement (avertissement au démarrage) |
| Haute    | 4      | H1, H2, H3 corrigés ; H4 documenté |
| Moyenne  | 8      | M1, M2 (partiel), M4 (partiel), M5, M6, M7 corrigés |
| Faible   | 12     | F1 corrigé ; reste documenté |

Points positifs relevés : protection CSRF globale (`CSRFProtect`), mots de
passe hachés en argon2 (`PasswordType`), requêtes SQL paramétrées via l'ORM
(la seule requête brute, `api/reservation.py:484`, est paramétrée),
Markdown rendu sans `CMARK_OPT_UNSAFE` (HTML brut et liens `javascript:`
neutralisés), autoescape Jinja actif, images utilisateur ré-encodées par
Flask-Images, `send_from_directory`/`secure_filename` utilisés pour les fichiers,
`pip-audit` sans vulnérabilité connue sur les paquets PyPI.

---

## Critique

### C1 — Décorateurs d'accès inopérants (placés au-dessus de `@blueprint.route`)

**Fichiers** : `collectives/routes/reservation.py:55-187` (7 routes),
`collectives/api/upload.py:17-199` (4 routes).

En Flask, `@blueprint.route` enregistre la fonction qu'il reçoit et la renvoie
inchangée. Un décorateur placé *au-dessus* de `@blueprint.route` enveloppe donc
une fonction qui n'est plus celle enregistrée : le contrôle n'est jamais exécuté.

```python
@user_is("can_manage_reservation")   # inopérant
@blueprint.route("/", methods=["GET"])
def view_reservations():
```

**Exploitation vérifiée** (client de test) : un utilisateur sans aucun rôle,
ayant signé la charte RGPD, obtient `200` sur `/reservation/` et
`/reservation/new`. Il peut lister toutes les locations (nom + licence des
emprunteurs), créer, valider, clôturer ou annuler des locations
(`cancel_rental` supprime en base).

Pour `api/upload.py`, `@valid_user(api=True)` est également inopérant. Les
routes restent protégées par effet de bord (`is_active` faux pour un anonyme,
ou `AttributeError` → 500), ce qui n'est pas une protection fiable.

**Recommandation** : placer `@blueprint.route` en premier (le plus haut), les
décorateurs d'accès en dessous. Ajouter un test de non-régression qui vérifie
qu'un utilisateur sans rôle est refusé sur ces routes. **Corrigé.**

### C2 — Endpoints API sans aucune authentification

**Fichiers** : `collectives/api/reservation.py` (toutes les routes),
`collectives/api/equipment.py` (toutes les routes).

Le blueprint `api` n'a pas de `before_request`. Ces routes n'ont aucun décorateur :

- `GET /api/reservations`, `/api/reservations_of_day`,
  `/api/reservations_returns_of_day`, `/api/reservation/<id>`,
  `/api/reservation/new_rental/<id>`, `/api/reservation/ligne/<id>`,
  `/api/reservation/lignerented/<id>`, `/api/reservation/lignereturned/<id>`,
  `/api/reservation/histo_reservations_for_an_equipment<id>`,
  `/api/reservation/autocomplete` : lecture anonyme.
- `POST /api/set_available_equipment/<id>`,
  `POST /api/remove_reservation_equipment/<id>/<id>`,
  `POST /api/remove_reservationLine_equipment/<id>/<id>`,
  `POST /api/remove_reservation_equipment_decreasing_quantity/<id>/<id>`,
  `POST /api/modelEdit/<id>/<name>/<manufacturer>`,
  `POST /api/modelDelete/<id>` : modification et suppression anonymes.
- `GET /api/my_reservations/`, `/api/my_reservations_completed/`,
  `/api/my_reservation/<id>` : le dernier renvoie les lignes de n'importe
  quelle réservation (IDOR), les deux premiers provoquent un 500 pour un anonyme.

**Exploitation vérifiée** : `GET /api/reservations` anonyme renvoie
`user_licence` et `user_full_name` de tous les emprunteurs ;
`POST /api/modelDelete/<id>` anonyme supprime un modèle d'équipement.
Le jeton CSRF est obtenu par n'importe quelle session anonyme (page de login).

**Recommandation** : `@valid_user(True)` + `@confidentiality_agreement(True)` +
`@user_is("can_manage_reservation", True)` (ou `can_manage_equipment`) sur
toutes ces routes ; vérification de propriété sur `my_reservation/<id>`.
**Corrigé.**

### C3 — `SECRET_KEY` et `ADMINPWD` par défaut codés en dur

**Fichier** : `config.py:35` (`SECRET_KEY = environ.get("SECRET_KEY") or "'@GU^..."`),
`config.py:52` (`ADMINPWD = ... or "foobar2"`).

Si l'exploitant ne surcharge pas ces valeurs (variable d'environnement ou
`instance/config.py`), la clé publique du dépôt permet :

- de forger le cookie de session Flask-Login (`_user_id`) et donc d'usurper
  **n'importe quel compte, y compris l'administrateur** (id 1) ;
- de se connecter avec `admin` / `foobar2` (`utils/init.py:157-165` réinitialise
  le mot de passe admin à chaque démarrage à partir de `ADMINPWD`) ;
- de forger les signatures Flask-Images, dont la route accepte un paramètre
  `url` distant (`http`, `https`, `ftp`) : **SSRF** depuis le serveur
  (`flask_images/core.py:323-343`) ;
- de forger les `profile_token` (`utils/profile_token.py`).

L'exemple `deployment/systemd/collectives.service` ne définit pas `SECRET_KEY`.
L'exemple Kubernetes le fait correctement.

**Recommandation** : refuser de démarrer hors `TESTING`/`DEBUG` si ces valeurs
sont celles par défaut ; documenter dans `deployment/`. **Partiellement
corrigé** : un message `CRITICAL` est journalisé au démarrage. Le refus de
démarrage n'a pas été appliqué pour ne pas casser les environnements de
développement lancés via `run.py` (où `DEBUG` n'est positionné qu'après
`create_app`). À faire manuellement une fois les déploiements vérifiés.

---

## Haute

### H1 — Numéros de licence des encadrants exposés aux anonymes

**Fichier** : `collectives/api/autocomplete_user.py:21-31, 111-188`.

`/api/leaders/autocomplete/?q=xx` et `/api/available_leaders/autocomplete/`
sont publics et sérialisent `AutocompleteUserSchema`, qui inclut `license`.
Un anonyme énumère, deux lettres à la fois, nom complet + numéro de licence de
tous les encadrants. La licence est l'identifiant de connexion et un des trois
facteurs de récupération de compte (avec l'e-mail et la date de naissance).

**Recommandation** : schéma sans `license` pour l'endpoint public ; exiger un
utilisateur connecté pour `available_leaders`. **Corrigé.**

### H2 — Énumération de tous les adhérents par tout utilisateur connecté

**Fichier** : `collectives/api/autocomplete_user.py:45-73`.

`/api/users/autocomplete/create_rental` n'exige que `valid_user` +
charte signée : n'importe quel adhérent récupère nom + licence + statut de
n'importe quel autre adhérent. La route sœur `/api/users/autocomplete/`
exige au moins `can_create_events`.

**Recommandation** : `@user_is("can_manage_reservation", True)`. **Corrigé.**

### H3 — XSS stocké via upload de SVG servi en statique

**Fichiers** : `collectives/models/upload.py:16`
(`UploadSet("documents", DOCUMENTS + IMAGES + ("gpx",))`),
`collectives/models/equipment.py:16`.

`IMAGES` de Flask-Uploads contient `svg`. Les documents d'événement et
d'activité sont servis tels quels depuis `/static/uploads/documents/` ;
un SVG contenant `<script>` s'exécute dans l'origine du site lorsqu'il est
ouvert directement (lien « document » de l'événement). Les uploaders sont des
encadrants ou superviseurs (semi-confiance), les victimes tout visiteur.
Les avatars et photos passent par Flask-Images (ré-encodage) et ne sont pas
concernés.

**Recommandation** : exclure `svg` des jeux d'extensions servis en statique ;
servir les uploads avec `Content-Disposition: attachment` et
`X-Content-Type-Options: nosniff`. **Corrigé** (exclusion de `svg` + `nosniff`).

### H4 — Documents uploadés publics et aux noms prévisibles

**Fichier** : `collectives/models/upload.py:158-159, 184`.

Les documents d'événement/activité sont stockés dans `static/uploads/documents/`
sous `AA_MM_JJ_nomoriginal.ext` et servis sans contrôle d'accès. Un événement à
visibilité « Activité » peut avoir des documents accessibles à qui devine
l'URL (listes de participants exportées, fichiers GPX de rendez-vous, etc.).

**Recommandation** : servir les documents via une route contrôlant
`event.is_visible_to(current_user)` (ou droits d'activité), stocker hors de
`static/`, ou au minimum ajouter un suffixe aléatoire au nom de fichier.
**Non corrigé** (changement de structure de stockage et de migration).

---

## Moyenne

### M1 — Redirection ouverte après connexion

**Fichier** : `collectives/routes/auth/login.py:155-158`.

Le paramètre `next` est validé par `urlparse(next).netloc == ""`. La valeur
`/\evil.com` a un `netloc` vide pour `urllib` mais est normalisée en
`//evil.com` par les navigateurs. Vérifié : Werkzeug conserve `Location: /\evil.com`.
Permet du phishing post-connexion.

**Recommandation** : n'accepter que les chemins commençant par un unique `/`
non suivi de `/` ou `\`. **Corrigé.**

### M2 — Cookies et en-têtes HTTP de sécurité absents

**Fichier** : `config.py`, `collectives/__init__.py`.

Aucune des options `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`,
`REMEMBER_COOKIE_SECURE`, `REMEMBER_COOKIE_HTTPONLY`, `REMEMBER_COOKIE_SAMESITE`
n'est définie ; le cookie « se souvenir de moi » dure 365 jours par défaut.
Aucun en-tête `Strict-Transport-Security`, `X-Content-Type-Options`,
`X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, `Content-Security-Policy`.

**Recommandation** : positionner ces options ; ajouter les en-têtes.
**Partiellement corrigé** : cookies `Secure` (hors `FLASK_DEBUG`), `HttpOnly`,
`SameSite=Lax` ; en-têtes `X-Content-Type-Options`, `Referrer-Policy`,
`Strict-Transport-Security` (uniquement en HTTPS). `X-Frame-Options` et une
CSP restent à décider (le site est-il intégré en iframe ailleurs ? les scripts
inline sont nombreux).

### M3 — Limitation des tentatives de connexion insuffisante

**Fichiers** : `collectives/routes/auth/login.py:76-88`,
`collectives/routes/auth/signup.py:391-431`.

Le throttling est par compte (`AUTH_FAILURE_WAIT` secondes entre deux essais),
sans limite par IP, sans verrouillage progressif ni journalisation des échecs
avec adresse source. `/auth/check_token/<licence>` révèle publiquement si un
jeton d'activation existe pour une licence.

**Recommandation** : limite par IP (reverse proxy ou Flask-Limiter), backoff
exponentiel, journaliser IP + identifiant en cas d'échec. **Non corrigé.**

### M4 — Injections HTML/JS via `|safe` sur des données modifiables

**Fichiers** :
- `collectives/templates/administration/user_list.html:10-11` :
  `{{ filters|safe }}` insère la `repr()` Python d'un dict contenant les noms
  d'activités. Ces noms sont modifiables par les superviseurs
  (`routes/activity_supervison.py:337-379`). Un nom contenant `</script>`
  exécute du JS chez la hotline/l'admin (élévation superviseur → admin).
- `collectives/forms/user_group.py:343-386` : titres d'événements et noms
  d'activités enveloppés dans `Markup()` puis injectés `|safe` dans
  `partials/user-group-form.html`.
- `collectives/routes/auth/login.py:52-56` : `u.full_name()` non échappé dans
  un `Markup` (exploitable seulement avec plusieurs comptes de même e-mail et
  mot de passe).
- `collectives/templates/index.html:73` : `BANNER_MESSAGE` dans un template
  literal JS (technicien, confiance).

**Recommandation** : `|tojson` au lieu de `|safe` pour les données
structurées ; échapper les noms. **Partiellement corrigé** (`user_list.html`
et `login.py`).

### M5 — Mode « mock » Payline actif dès que `PAYLINE_MERCHANT_ID` est vide

**Fichier** : `collectives/utils/payline.py:521-535, 592`,
`collectives/routes/payment.py:590-604, 649-698`.

Quand `PAYLINE_MERCHANT_ID` est vide, `get_web_payment_details` construit un
résultat à partir des paramètres d'URL `message` et `amount` fournis par le
client. Un acheteur connaissant son `processor_token` (affiché par
`/payment/do_mock_payment/<token>`) approuve son propre paiement avec
`/payment/process?paylinetoken=…&message=ACCEPTED&amount=…`. Sur une instance
de production où les paiements sont activés mais Payline mal configuré, les
inscriptions payantes deviennent gratuites.

**Recommandation** : n'autoriser le mock qu'en `DEBUG`/`TESTING`. **Corrigé.**

### M6 — Export des rôles hors périmètre supervisé

**Fichier** : `collectives/routes/activity_supervison.py:152-178`.

`export_role` instancie `ActivityTypeSelectionForm()` sans restreindre la liste
aux activités supervisées : un superviseur exporte les encadrants (nom, e-mail,
téléphone) de n'importe quelle activité.

**Recommandation** : `activity_list=current_user.get_supervised_activities()`.
**Corrigé.**

### M7 — Filtre admin sur attribut arbitraire

**Fichier** : `collectives/api/admin.py:65-66`, `:153-157`.

`getattr(User, field).ilike(...)` accepte n'importe quel attribut, dont
`password` (oracle sur le hachage) ou des relations (500). Le tri passe une
chaîne brute à `order_by`. Réservé à la hotline.

**Recommandation** : liste blanche de colonnes. **Corrigé.**

### M8 — Erreurs 500 sur entrées non validées

`int(request.args.get("page"))` sans valeur (`api/admin.py:160`,
`api/payment.py:214`), `int(user_id)` (`api/userevent.py:155`),
`getattr(EventStatus, value)` (`api/event.py:164`, ex. `value=__class__`),
`RoleIds(int(None))` (`routes/reservation.py:234`). Impact : robustesse et
bruit dans les logs. **Non corrigé.**

---

## Faible

- **F1** — `login.py:67-73` : en cas de comptes multiples, le mot de passe est
  renvoyé en clair dans le HTML (`password=form.password.data`,
  `hide_value = False`). Le flux nécessite ce comportement ; un jeton temporaire
  serait préférable. **Non corrigé** (fonctionnel), l'échappement du nom l'est.
- **F2** — `/auth/logout` en `GET` : déconnexion forçable par lien.
- **F3** — `api/userevent.py:68` : `print()` de debug en production.
- **F4** — `Dockerfile` : conteneur exécuté en root, `instance/` copié dans
  l'image (peut contenir des secrets) ; `run.py` lance en `debug=True`
  (développement uniquement).
- **F5** — Dépendances Git non figées : `flask-images` sur `rev=master`
  (chaîne d'approvisionnement) ; `flask-login`, `flask-uploads`, `pysimplesoap`
  sur des commits hors PyPI donc invisibles pour `pip-audit`.
- **F6** — `/api/events/` renvoie `Access-Control-Allow-Origin: *` alors que
  la réponse dépend de la session (sans credentials, risque nul aujourd'hui).
- **F7** — `ReverseProxied` accepte `X-Forwarded-Proto` de toute source.
- **F8** — `technician.py:192-206` : `update_configuration` poursuit après un
  échec de validation ; `redirect(...)` sans `return` ligne 206.
- **F9** — `utils/csv.py:77` : `template.format(**row)` — un superviseur peut
  lire des attributs Python via `{titre.__class__}` (pas d'exécution).
- **F10** — `profile_token` tronqué à 64 bits (acceptable).
- **F11** — `api/event.py` : `Event.title.like(f"%{value}%")` sans échappement
  des jokers `%`/`_` (recherche élargie, pas d'injection).
- **F12** — `flash(f"Page inconnue: {request.path}")` dans `utils/error.py`
  stocke le chemin dans le cookie de session (échappé à l'affichage).

---

## Correctifs appliqués dans cette branche

Un commit par correction, dans l'ordre :

1. C1 — ordre des décorateurs `routes/reservation.py` et `api/upload.py`.
2. C2 — authentification/autorisation des API réservation et équipement.
3. H1/H2 — licences retirées des autocomplétions publiques, rôle requis pour
   `create_rental`.
4. H3 — exclusion de `svg` des uploads servis en statique.
5. M1 — validation stricte de `next`.
6. M2 — options cookies et en-têtes de sécurité.
7. M4 — `|tojson` dans `user_list.html`, échappement dans `login.py`.
8. M5 — mock Payline limité à `DEBUG`/`TESTING`.
9. M6 — périmètre de `export_role`.
10. M7 — liste blanche des filtres admin.
11. C3 — avertissement critique au démarrage sur les secrets par défaut.

## À traiter manuellement

- **C3** : décider du refus de démarrage avec secrets par défaut ; vérifier les
  déploiements existants (systemd) ; faire tourner la `SECRET_KEY` si elle a
  déjà été exposée.
- **H4** : contrôle d'accès sur les documents uploadés.
- **M2** : `X-Frame-Options`/CSP.
- **M3** : rate limiting par IP.
- **M4** : `forms/user_group.py` (`Markup` sur titres/noms).
- **M8**, **F2** à **F12**.
- Ajouter un test automatique qui parcourt `app.url_map` et vérifie qu'un
  client anonyme est refusé (302/401/403) sur toute route non listée comme
  publique, pour éviter le retour de C1/C2.
