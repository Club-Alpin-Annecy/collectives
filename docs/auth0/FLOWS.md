# Auth0 Process Flows Documentation

Ce document décrit en détail les différents scénarios d'authentification et de gestion des utilisateurs avec Auth0.

## Table des matières

1. [Nouvel utilisateur via Auth0 (mode local)](#1-nouvel-utilisateur-via-auth0-mode-local)
2. [Nouvel utilisateur via Auth0 (mode extranet)](#2-nouvel-utilisateur-via-auth0-mode-extranet)
3. [Utilisateur existant lie son compte à Auth0](#3-utilisateur-existant-lie-son-compte-à-auth0)
4. [Utilisateur déjà lié se connecte via Auth0](#4-utilisateur-déjà-lié-se-connecte-via-auth0)
5. [Utilisateur avec Auth0 se connecte avec mot de passe (fallback)](#5-utilisateur-avec-auth0-se-connecte-avec-mot-de-passe-fallback)
6. [Suppression de compte Auth0 → impact sur Collectives](#6-suppression-de-compte-auth0--impact-sur-collectives)
7. [Connexion admin de secours (bypass)](#7-connexion-admin-de-secours-bypass)
8. [Social login avec différents providers](#8-social-login-avec-différents-providers)

---

## 1. Nouvel utilisateur via Auth0 (mode local)

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- `Configuration.EXTRANET_ACCOUNT_ID` est vide (mode local)
- L'utilisateur n'a pas de compte Collectives existant
- L'utilisateur n'a jamais utilisé Auth0 avec Collectives

### Diagramme de flux

```
Utilisateur
    │
    ├─> Clique sur "Se connecter avec Auth0" (/auth/login)
    │
    ├─> Redirigé vers Auth0 (/auth/login/auth0)
    │   └─> Auth0 génère state CSRF
    │
    ├─> Authentification Auth0 (choix du provider)
    │   └─> Google / Microsoft / Email-Password / etc.
    │
    ├─> Callback Auth0 (/auth/callback/auth0)
    │   ├─> Vérifie state CSRF
    │   ├─> Récupère userinfo (sub, email, picture, etc.)
    │   ├─> Vérifie si auth0_id existe en DB → NON
    │   ├─> Vérifie si email existe en DB → NON
    │   └─> Redirige vers /auth/signup/auth0/complete
    │
    ├─> Formulaire de complétion (mode local)
    │   ├─> Email pré-rempli (readonly)
    │   ├─> Nom, prénom pré-remplis depuis Auth0
    │   ├─> Demande : numéro de licence, date de naissance, mot de passe
    │   └─> Validation du formulaire
    │
    ├─> Création du compte
    │   ├─> Type: UserType.Local
    │   ├─> auth0_id: défini
    │   ├─> enabled: true
    │   ├─> Téléchargement avatar si picture_url disponible
    │   └─> Signature mentions légales
    │
    └─> Connexion automatique + redirection
        └─> Si mentions légales non signées → /legal
        └─> Sinon → page demandée ou "/"
```

### Étapes détaillées

1. **Initiation login Auth0** (`/auth/login/auth0`)
   - Génère `state` CSRF et stocke dans session
   - Stocke `next` URL dans session
   - Redirige vers Auth0 avec `redirect_uri=/auth/callback/auth0`

2. **Callback Auth0** (`/auth/callback/auth0`)
   - Vérifie `state` CSRF
   - Échange authorization code contre token
   - Récupère `userinfo` : `sub`, `email`, `picture`, `given_name`, `family_name`
   - Vérifie si `auth0_id` existe → NON
   - Vérifie si `email` existe → NON
   - Stocke données Auth0 en session (`auth0_pending`)
   - Redirige vers `/auth/signup/auth0/complete`

3. **Complétion signup local** (`/auth/signup/auth0/complete`)
   - Détecte mode local
   - Affiche `LocalAccountCreationForm`
   - Pré-remplit : email (Auth0), nom/prénom (si disponibles)
   - Utilisateur saisit : numéro de licence, date de naissance, mot de passe
   - Validation : email doit correspondre à Auth0

4. **Création utilisateur**
   - Crée `User` avec `auth0_id`
   - Type: `UserType.Local`
   - `enabled=True`
   - Télécharge avatar depuis `picture_url` si disponible
   - Sauvegarde en DB

5. **Login automatique**
   - `login_user(user, remember=True)`
   - Nettoie session (`auth0_pending`, `oauth_next`)
   - Redirige vers page demandée

### Résultat attendu
- ✅ Utilisateur créé avec `auth0_id` renseigné
- ✅ Utilisateur connecté automatiquement
- ✅ Avatar téléchargé si disponible

### Cas d'erreur
- **Email déjà utilisé** : Redirige vers `/auth/link/auth0` (scénario 3)
- **State CSRF invalide** : Message d'erreur + redirection `/auth/login`
- **Données Auth0 incomplètes** : Message d'erreur + redirection `/auth/login`
- **Session expirée** : Message d'erreur + redirection `/auth/login`

---

## 2. Nouvel utilisateur via Auth0 (mode extranet)

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- `Configuration.EXTRANET_ACCOUNT_ID` est défini (mode extranet)
- L'utilisateur n'a pas de compte Collectives existant
- L'utilisateur a une licence FFCAM valide

### Diagramme de flux

```
Utilisateur
    │
    ├─> Clique sur "Se connecter avec Auth0" (/auth/login)
    │
    ├─> Redirigé vers Auth0 (/auth/login/auth0)
    │
    ├─> Authentification Auth0
    │
    ├─> Callback Auth0 (/auth/callback/auth0)
    │   ├─> auth0_id n'existe pas
    │   ├─> email n'existe pas
    │   └─> Redirige vers /auth/signup/auth0/complete
    │
    ├─> Formulaire de complétion (mode extranet)
    │   ├─> Email pré-rempli (readonly)
    │   ├─> Demande : numéro de licence, date de naissance
    │   └─> Vérification FFCAM Extranet
    │
    ├─> Création du compte
    │   ├─> Type: UserType.Extranet
    │   ├─> Génération mot de passe aléatoire
    │   ├─> Synchronisation données FFCAM
    │   └─> Téléchargement avatar Auth0
    │
    └─> Connexion automatique
```

### Étapes détaillées

1-2. **Initiation et Callback** : Identiques au scénario 1

3. **Complétion signup extranet** (`/auth/signup/auth0/complete`)
   - Détecte mode extranet
   - Affiche `ExtranetAccountCreationForm`
   - Pré-remplit email (Auth0)
   - Utilisateur saisit : numéro de licence, date de naissance
   - Validation avec API FFCAM Extranet

4. **Création utilisateur**
   - Crée `User` avec `auth0_id`
   - Type: `UserType.Extranet`
   - **Génère mot de passe aléatoire** (16 caractères)
   - Synchronise données FFCAM : nom, prénom, club, etc.
   - Télécharge avatar depuis Auth0
   - Sauvegarde en DB

5. **Login automatique**
   - Message : "Compte créé. Mot de passe de secours généré."
   - Connexion automatique

### Résultat attendu
- ✅ Utilisateur créé avec données FFCAM synchronisées
- ✅ Mot de passe de secours généré
- ✅ Avatar téléchargé

### Cas d'erreur
- **Licence invalide** : Message d'erreur + rechargement formulaire
- **Licence déjà utilisée** : Redirige vers `/auth/link/auth0`
- **API FFCAM indisponible** : Message d'erreur

---

## 3. Utilisateur existant lie son compte à Auth0

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- L'utilisateur a un compte Collectives avec email X
- L'utilisateur n'a pas encore `auth0_id` défini
- L'utilisateur se connecte via Auth0 avec le même email X

### Diagramme de flux

```
Utilisateur
    │
    ├─> Connexion Auth0
    │
    ├─> Callback Auth0
    │   ├─> auth0_id n'existe pas en DB
    │   ├─> email EXISTE en DB
    │   └─> Redirige vers /auth/link/auth0
    │
    ├─> Page de liaison de compte
    │   ├─> Affiche email Auth0
    │   ├─> Message : "Un compte existe avec cet email"
    │   ├─> Demande mot de passe pour vérification
    │   └─> Validation mot de passe
    │
    ├─> Liaison du compte
    │   ├─> user.auth0_id = auth0_id
    │   ├─> db.session.commit()
    │   └─> Téléchargement avatar si disponible
    │
    └─> Connexion automatique
```

### Étapes détaillées

1. **Callback détecte compte existant**
   - `auth0_id` n'existe pas
   - `email` EXISTE dans la DB
   - Stocke `auth0_pending` en session
   - Redirige vers `/auth/link/auth0`

2. **Page de liaison** (`/auth/link/auth0`)
   - Affiche `LoginForm` (seulement mot de passe)
   - Affiche email Auth0
   - Message explicatif

3. **Validation mot de passe**
   - Recherche utilisateur par email
   - Vérifie mot de passe
   - Si plusieurs utilisateurs avec même email : filtre par mot de passe

4. **Liaison**
   - `user.auth0_id = auth0_id`
   - Commit DB
   - Message : "Compte lié avec succès à Auth0"

5. **Login**
   - Connexion automatique
   - Redirection vers page demandée

### Résultat attendu
- ✅ `user.auth0_id` renseigné
- ✅ Utilisateur peut maintenant se connecter via Auth0 ou mot de passe

### Cas d'erreur
- **Mot de passe incorrect** : Message d'erreur + rechargement formulaire
- **Aucun utilisateur trouvé** : Message d'erreur (ne devrait pas arriver)
- **Session expirée** : Redirection `/auth/login`

---

## 4. Utilisateur déjà lié se connecte via Auth0

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- L'utilisateur a `auth0_id` défini dans Collectives
- L'utilisateur se connecte via Auth0

### Diagramme de flux

```
Utilisateur
    │
    ├─> Connexion Auth0
    │
    ├─> Callback Auth0
    │   ├─> auth0_id EXISTE en DB
    │   ├─> Récupère user depuis DB
    │   └─> Appelle login_existing_auth0_user()
    │
    ├─> Vérifications
    │   ├─> user.enabled ? → Si NON : erreur
    │   ├─> user.type != UnverifiedLocal ? → Si OUI : erreur
    │   ├─> user.is_active ? → Si NON : sync extranet + vérif
    │   └─> Toutes OK : continue
    │
    ├─> Login
    │   └─> login_user(user, remember=True)
    │
    └─> Redirection
        ├─> Si mentions légales non signées → /legal
        └─> Sinon → page demandée ou "/"
```

### Étapes détaillées

1. **Callback trouve utilisateur**
   - `User.query.filter_by(auth0_id=auth0_id).first()` → EXISTE
   - Appelle `login_existing_auth0_user(user)`

2. **Vérifications**
   - **user.enabled** : Si `False` → Erreur "Compte désactivé"
   - **user.type == UnverifiedLocal** : Si `True` → Erreur "Compte non validé"
   - **user.is_active** : Si `False` → Erreur "Licence inactive"

3. **Login via complete_login()**
   - `login_user(user, remember=True)`
   - Vérifie mentions légales signées
   - Nettoie session
   - Récupère `next` URL

4. **Redirection**
   - Si mentions légales non signées → `/legal`
   - Sinon → page demandée ou `"/"`

### Résultat attendu
- ✅ Utilisateur connecté rapidement
- ✅ Pas de formulaire supplémentaire
- ✅ Session persistante (`remember=True`)

### Cas d'erreur
- **Compte désactivé** : Message + lien récupération
- **Compte non vérifié** : Message + lien récupération
- **Licence inactive** : Message + lien récupération

---

## 5. Utilisateur avec Auth0 se connecte avec mot de passe (fallback)

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- `AUTH0_FORCE_SSO=false` (ou admin bypass activé)
- L'utilisateur a `auth0_id` défini
- L'utilisateur utilise le login classique (email + mot de passe)

### Diagramme de flux

```
Utilisateur
    │
    ├─> Va sur /auth/login
    │   └─> Formulaire classique visible (AUTH0_FORCE_SSO=false)
    │
    ├─> Saisit email + mot de passe
    │
    ├─> POST /auth/login
    │   ├─> Vérifie utilisateur existe
    │   ├─> Vérifie mot de passe
    │   ├─> Vérifie enabled, active, etc.
    │   └─> login_user(user)
    │
    ├─> Logout
    │   ├─> Détecte user.auth0_id != None
    │   ├─> Appelle logout_user()
    │   └─> Redirige vers /auth/logout/auth0
    │
    └─> Logout Auth0
        └─> Redirige vers Auth0 logout URL
        └─> Auth0 redirige vers /auth/login
```

### Étapes détaillées

1. **Login classique fonctionne normalement**
   - Aucune différence avec un utilisateur sans Auth0
   - `auth0_id` n'affecte pas le login par mot de passe

2. **Logout géré différemment**
   - Route `/auth/logout` détecte `user.auth0_id`
   - Si `auth0_id` existe ET `AUTH0_ENABLED=true` :
     - Appelle `logout_user()`
     - Redirige vers `/auth/logout/auth0`
   - Sinon : logout classique

3. **Logout Auth0**
   - Construit URL : `https://{AUTH0_DOMAIN}/v2/logout?client_id=...&returnTo=.../auth/login`
   - Redirige vers Auth0
   - Auth0 déconnecte et redirige vers `/auth/login`

### Résultat attendu
- ✅ Utilisateur peut se connecter avec mot de passe même s'il a Auth0
- ✅ Logout déconnecte aussi d'Auth0

### Cas d'erreur
- **Mot de passe oublié** : Lien vers `/auth/recover`
- **Compte désactivé** : Message d'erreur standard

---

## 6. Suppression de compte Auth0 → impact sur Collectives

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- `AUTH0_WEBHOOK_SECRET` configuré
- Webhook configuré dans Auth0 Dashboard
- Admin Auth0 supprime un utilisateur

### Diagramme de flux

```
Admin Auth0
    │
    ├─> Supprime utilisateur dans Auth0 Dashboard
    │
    └─> Auth0 envoie webhook → POST /api/webhooks/auth0
        │
        ├─> Vérifie signature HMAC
        │   └─> Si invalide : Erreur 401
        │
        ├─> Parse JSON payload
        │   ├─> type: "user.deleted"
        │   └─> data.user_id: "auth0|12345..."
        │
        ├─> Recherche utilisateur
        │   └─> User.query.filter_by(auth0_id=user_id).first()
        │
        ├─> Si utilisateur trouvé :
        │   ├─> user.enabled = False
        │   ├─> user.auth0_id = None
        │   ├─> db.session.commit()
        │   └─> Log : "Disabled user X after Auth0 deletion"
        │
        └─> Réponse 200 OK
```

### Étapes détaillées

1. **Configuration webhook Auth0**
   - Dashboard Auth0 → Monitoring → Streams
   - Créer webhook vers `https://collectives.example.com/api/webhooks/auth0`
   - Définir secret dans `AUTH0_WEBHOOK_SECRET`
   - Activer événement `user.deleted`

2. **Réception webhook**
   - Vérifie `AUTH0_ENABLED=true`
   - Vérifie signature HMAC avec `AUTH0_WEBHOOK_SECRET`
   - Parse payload JSON

3. **Traitement user.deleted**
   - Extrait `user_id` (auth0_id)
   - Recherche utilisateur en DB
   - Si trouvé :
     - `user.enabled = False`
     - `user.auth0_id = None` (délie le compte)
     - Commit
   - Si non trouvé : Log warning mais retourne 200

4. **Conséquences**
   - L'utilisateur ne peut plus se connecter via Auth0 (auth0_id = None)
   - L'utilisateur ne peut plus se connecter par mot de passe (enabled = False)
   - L'utilisateur peut réactiver son compte via `/auth/recover`

### Résultat attendu
- ✅ Utilisateur désactivé automatiquement
- ✅ `auth0_id` supprimé
- ✅ Données utilisateur préservées (pas de suppression en cascade)

### Cas d'erreur
- **Signature invalide** : Erreur 401, logged
- **Utilisateur introuvable** : Log warning, retourne 200 OK
- **Erreur DB** : Rollback, erreur 500

---

## 7. Connexion admin de secours (bypass)

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- `AUTH0_FORCE_SSO=true` (login classique masqué)
- `AUTH0_BYPASS_ENABLED=true`
- Auth0 est indisponible ou admin a besoin d'accès d'urgence

### Diagramme de flux

```
Administrateur
    │
    ├─> Va sur /auth/login
    │   ├─> Voit uniquement bouton Auth0 (FORCE_SSO)
    │   └─> Voit lien "Connexion administrateur" en bas
    │
    ├─> Clique sur "Connexion administrateur"
    │   └─> Redirige vers /auth/admin/login
    │
    ├─> Vérifie AUTH0_BYPASS_ENABLED
    │   ├─> Si False : Message d'erreur + redirect /auth/login
    │   └─> Si True : Affiche formulaire
    │
    ├─> Formulaire admin login
    │   ├─> Avertissement : "Mode de secours"
    │   ├─> Email + mot de passe
    │   └─> Lien retour vers login normal
    │
    ├─> POST /auth/admin/login
    │   ├─> Vérifie utilisateur + mot de passe
    │   ├─> Vérifie enabled, active, etc.
    │   └─> login_user(user)
    │
    └─> Connexion réussie
        └─> Flash: "Connecté en mode administrateur"
```

### Étapes détaillées

1. **Accès au bypass**
   - Sur `/auth/login` avec `AUTH0_FORCE_SSO=true` :
     - Seul bouton Auth0 visible
     - Lien discret en bas : "Connexion administrateur"
   - Lien pointe vers `/auth/admin/login`

2. **Vérification bypass activé**
   - Route `/auth/admin/login` vérifie `AUTH0_BYPASS_ENABLED`
   - Si `False` : Message + redirection
   - Si `True` : Affiche formulaire

3. **Page admin login**
   - Template `auth/admin_login.html`
   - Alert warning : "Mode de connexion de secours"
   - Formulaire identique au login classique
   - Lien "Retour à la connexion normale"

4. **Authentification**
   - Logique identique à `/auth/login`
   - Message de succès différent : "Connecté en mode administrateur"

5. **Usage recommandé**
   - **Urgence** : Auth0 indisponible
   - **Maintenance** : Configuration Auth0
   - **Support** : Déblocage compte

### Résultat attendu
- ✅ Admin peut se connecter même si Auth0 down
- ✅ Accessible uniquement si `AUTH0_BYPASS_ENABLED=true`
- ✅ Traçabilité : flash message différent

### Cas d'erreur
- **Bypass désactivé** : Message + redirection
- **Mot de passe incorrect** : Erreur standard
- **Compte non admin** : Fonctionne quand même (pas de vérification role)

### Recommandations production
- Garder `AUTH0_BYPASS_ENABLED=false` en temps normal
- Activer temporairement si Auth0 indisponible
- Surveiller logs pour détecter utilisation du bypass
- Envisager rate limiting strict sur `/auth/admin/login`

---

## 8. Social login avec différents providers

### Conditions d'entrée
- `AUTH0_ENABLED=true`
- Auth0 configuré avec plusieurs providers sociaux
  - Google, Microsoft, Facebook, GitHub, etc.

### Diagramme de flux

```
Utilisateur
    │
    ├─> Clique "Se connecter avec Auth0"
    │
    ├─> Auth0 Universal Login
    │   ├─> Google
    │   ├─> Microsoft
    │   ├─> Facebook
    │   ├─> GitHub
    │   └─> Email/Password
    │
    ├─> Utilisateur choisit Google
    │
    ├─> Callback Auth0
    │   └─> userinfo.sub = "google-oauth2|108234..."
    │
    ├─> Complete signup
    │   ├─> Récupère picture (avatar Google)
    │   ├─> Récupère given_name, family_name
    │   ├─> Pré-remplit formulaire
    │   └─> Télécharge avatar Google
    │
    └─> Compte créé avec avatar social
```

### Étapes détaillées

1. **Configuration Auth0**
   - Dashboard Auth0 → Authentication → Social
   - Activer providers : Google, Microsoft, etc.
   - Configurer Client ID / Secret pour chaque provider

2. **Détection du provider**
   - Auth0 retourne `userinfo.sub` au format : `{provider}|{provider_user_id}`
   - Exemples :
     - `"google-oauth2|108234567890"`
     - `"microsoft|abc123..."`
     - `"auth0|def456..."` (Email/Password)
     - `"github|789..."` (GitHub)

3. **Extraction données spécifiques**
   - **Google** :
     - `picture` : URL avatar Google
     - `given_name` / `family_name` : Nom complet
     - `email_verified` : true
   - **Microsoft** :
     - `picture` : URL avatar Microsoft
     - `name` : Nom complet
     - `email_verified` : true
   - **Facebook** :
     - `picture` : URL avatar Facebook
     - `name` : Nom complet
   - **GitHub** :
     - `avatar_url` : URL avatar GitHub
     - `name` : Nom complet

4. **Traitement avatar**
   - Fonction `download_and_save_avatar(picture_url, user_id)`
   - Télécharge image depuis URL
   - Sauvegarde dans `uploads/avatars/auth0_avatar_{user_id}.{ext}`
   - Assigne à `user.avatar`

5. **Pré-remplissage formulaire**
   - `form.mail.data = userinfo.email`
   - `form.first_name.data = userinfo.given_name`
   - `form.last_name.data = userinfo.family_name`

### Résultat attendu
- ✅ Avatar social automatiquement récupéré
- ✅ Nom/prénom pré-remplis
- ✅ Expérience utilisateur fluide

### Cas d'erreur
- **Avatar download failed** : Log erreur, continue sans avatar
- **Picture URL invalide** : Ignore, pas d'avatar
- **Timeout download** : Ignore après 10s

### Providers supportés

| Provider  | Sub prefix       | Avatar | Nom complet | Email verified |
|-----------|------------------|--------|-------------|----------------|
| Google    | google-oauth2    | ✅      | ✅           | ✅              |
| Microsoft | microsoft        | ✅      | ✅           | ✅              |
| Facebook  | facebook         | ✅      | ✅           | Partiel        |
| GitHub    | github           | ✅      | ✅           | ✅              |
| Auth0     | auth0            | ❌      | ❌           | Partiel        |

---

## Configuration globale

### Variables d'environnement

```bash
# Activation Auth0
AUTH0_ENABLED=true
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=xxxxx
AUTH0_CLIENT_SECRET=xxxxx

# Mode Force SSO
AUTH0_FORCE_SSO=false  # true = masque login classique

# Bypass admin
AUTH0_BYPASS_ENABLED=false  # true = /auth/admin/login accessible

# Webhook
AUTH0_WEBHOOK_SECRET=your_webhook_secret  # Pour signature HMAC
```

### URLs importantes

- **Login Auth0** : `/auth/login/auth0`
- **Callback Auth0** : `/auth/callback/auth0`
- **Complete signup** : `/auth/signup/auth0/complete`
- **Link account** : `/auth/link/auth0`
- **Logout Auth0** : `/auth/logout/auth0`
- **Admin bypass** : `/auth/admin/login`
- **Webhook** : `/api/webhooks/auth0`

### Callbacks Auth0 à configurer

Dans Auth0 Dashboard → Applications → Settings :

```
Allowed Callback URLs:
https://your-domain.com/auth/callback/auth0

Allowed Logout URLs:
https://your-domain.com/auth/login

Allowed Web Origins:
https://your-domain.com
```

---

## Glossaire

- **auth0_id** : Identifiant unique Auth0 (format: `provider|id`)
- **State** : Token CSRF pour sécuriser le callback OAuth
- **userinfo** : Données utilisateur retournées par Auth0
- **Force SSO** : Mode où seul Auth0 est affiché (login classique masqué)
- **Bypass admin** : Route de secours pour admin si Auth0 down
- **Webhook** : Notification HTTP envoyée par Auth0 lors d'événements

---

## Support et dépannage

Voir [AUTH0_TROUBLESHOOTING.md](AUTH0_TROUBLESHOOTING.md) pour les problèmes courants et leurs solutions.

