# Auth0 SSO - Guide complet

Ce document explique comment configurer et utiliser l'authentification SSO avec Auth0 pour l'application Collectives.

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Installation rapide](#installation-rapide)
4. [Configuration détaillée](#configuration-détaillée)
5. [Architecture](#architecture)
6. [Modes de fonctionnement](#modes-de-fonctionnement)
7. [FAQ](#faq)

---

## Vue d'ensemble

L'intégration Auth0 permet aux utilisateurs de se connecter via :
- **Social login** (Google, Microsoft, Facebook, etc.)
- **Email/Password Auth0**
- **Connexion classique** (fallback, si Force SSO désactivé)

### Avantages

- Connexion unifiée avec les comptes sociaux
- Gestion centralisée des utilisateurs dans Auth0
- Sécurité renforcée (MFA, détection de fraude)
- Liaison automatique avec comptes existants

---

## Prérequis

1. **Compte Auth0** configuré (gratuit : https://auth0.com/signup)
2. **Application Auth0** créée (type : Regular Web Application)
3. **Python 3.9+** avec `uv` installé
4. **Dépendances** : `authlib`, `cryptography`

---

## Installation rapide

### 1. Installer les dépendances

```bash
cd /Users/tatooine/Desktop/dev/collectives
uv add authlib cryptography
```

### 2. Configurer Auth0 Dashboard

1. Créer une application "Regular Web Application"
2. Noter le **Domain**, **Client ID**, et **Client Secret**
3. Configurer les URLs :
   - **Allowed Callback URLs** : 
     ```
     http://localhost:5000/auth/callback/auth0
     https://votre-domaine.fr/auth/callback/auth0
     ```
   - **Allowed Logout URLs** : 
     ```
     http://localhost:5000/auth/login
     https://votre-domaine.fr/auth/login
     ```
   
   ⚠️ **Important** : Le préfixe `/auth` est obligatoire (blueprint routing).

### 3. Configurer l'application

Modifier `instance/config.py` :

```python
# Auth0 SSO Configuration
AUTH0_ENABLED = True
AUTH0_DOMAIN = "your-tenant.eu.auth0.com"  # SANS https://
AUTH0_CLIENT_ID = "votre_client_id"
AUTH0_CLIENT_SECRET = "votre_client_secret"

# Mode Force SSO (optionnel)
AUTH0_FORCE_SSO = False  # True = masque le login classique
AUTH0_BYPASS_ENABLED = False  # True = active /auth/admin/login
```

### 4. Appliquer la migration

```bash
FLASK_APP=collectives:create_app uv run flask db upgrade
```

Cela ajoute la colonne `auth0_id` à la table `users`.

### 5. Démarrer l'application

```bash
uv run python run.py
```

Accéder à http://localhost:5000/auth/login

✅ Vous verrez un bouton **"Se connecter avec Auth0"** !

---

## Configuration détaillée

### Variables d'environnement disponibles

| Variable | Type | Défaut | Description |
|----------|------|--------|-------------|
| `AUTH0_ENABLED` | Boolean | `False` | Active/désactive Auth0 |
| `AUTH0_DOMAIN` | String | - | Domain Auth0 (ex: `tenant.eu.auth0.com`) |
| `AUTH0_CLIENT_ID` | String | - | Client ID de l'application Auth0 |
| `AUTH0_CLIENT_SECRET` | String | - | Client Secret (à garder confidentiel) |
| `AUTH0_FORCE_SSO` | Boolean | `False` | Masque le login classique |
| `AUTH0_BYPASS_ENABLED` | Boolean | `False` | Active la connexion admin de secours |
| `AUTH0_WEBHOOK_SECRET` | String | `""` | Secret pour signature webhook |

### Configuration des Social Connections

Dans Auth0 Dashboard → **Authentication** → **Social** :

1. Activer les providers souhaités (Google, Microsoft, etc.)
2. Pour chaque provider :
   - Créer une OAuth App sur le provider (ex: Google Cloud Console)
   - Copier Client ID / Secret
   - Configurer dans Auth0

**Exemple Google** :
1. Console Google Cloud → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Authorized redirect URIs : `https://your-tenant.eu.auth0.com/login/callback`
4. Copier Client ID/Secret dans Auth0

---

## Architecture

### Flux d'authentification

```
Utilisateur
    │
    ├─> Clique "Se connecter avec Auth0"
    │
    ├─> Redirigé vers Auth0 (/auth/login/auth0)
    │   └─> Génération state CSRF
    │
    ├─> Auth0 Universal Login
    │   └─> Choix : Google / Microsoft / Email / etc.
    │
    ├─> Callback (/auth/callback/auth0)
    │   ├─> Vérification state CSRF
    │   ├─> Récupération userinfo (sub, email, picture)
    │   └─> Décision :
    │       ├─> Utilisateur existe avec auth0_id → Login direct
    │       ├─> Email existe sans auth0_id → Liaison de compte
    │       └─> Nouvel utilisateur → Complétion inscription
    │
    └─> Application Collectives (authentifié)
```

### Base de données

**Modification du modèle User** :
```python
class User:
    # ... champs existants ...
    auth0_id = db.Column(
        db.String(255),
        nullable=True,
        unique=True,
        index=True
    )
```

- `auth0_id` : Identifiant unique Auth0 (format: `provider|id`)
  - Exemples : `auth0|12345`, `google-oauth2|108234`, `microsoft|abc123`
- `nullable=True` : Les comptes existants peuvent ne pas avoir d'Auth0
- `unique=True` : Un compte Auth0 ne peut être lié qu'à un seul utilisateur Collectives

---

## Modes de fonctionnement

### Mode 1 : Auth0 optionnel (par défaut)

```python
AUTH0_ENABLED = True
AUTH0_FORCE_SSO = False
```

- Bouton Auth0 visible sur la page de login
- Formulaire classique email/password toujours disponible
- Les utilisateurs choisissent leur méthode préférée

**Idéal pour** : Déploiement progressif, migration douce

### Mode 2 : Force SSO

```python
AUTH0_ENABLED = True
AUTH0_FORCE_SSO = True
AUTH0_BYPASS_ENABLED = True  # Recommandé
```

- Seul le bouton Auth0 est affiché
- Formulaire classique masqué
- Lien "Connexion administrateur" en bas de page (si bypass activé)

**Idéal pour** : Production, après migration complète

### Mode 3 : Bypass admin (urgence)

Accessible uniquement si `AUTH0_BYPASS_ENABLED = True`

URL : `/auth/admin/login`

- Formulaire classique email/password
- Avertissement "Mode de secours"
- Lien retour vers login normal

**Utiliser si** :
- Auth0 est indisponible
- Configuration Auth0 à corriger
- Urgence administrateur

---

## FAQ

### Processus d'inscription

**Q: Que se passe-t-il quand un nouvel utilisateur s'inscrit via Auth0 ?**

**En mode extranet** (production) :
1. L'utilisateur se connecte via Auth0 (Google, etc.)
2. Il doit fournir : numéro de licence + date de naissance
3. Le système vérifie via l'API FFCAM Extranet
4. Un compte de type `Extranet` est créé
5. **Pas de mot de passe** : authentification via Auth0 uniquement

**En mode local** (développement) :
1. L'utilisateur se connecte via Auth0
2. Il doit fournir : prénom, nom, licence, date de naissance, mot de passe
3. Un compte de type `Local` est créé
4. **Avec mot de passe** : peut se connecter via Auth0 OU mot de passe

### Liaison de compte

**Q: Un utilisateur existant peut-il lier son compte à Auth0 ?**

Oui ! Si un email existe déjà :
1. L'utilisateur tente de se connecter via Auth0
2. Le système détecte que l'email existe
3. Il demande le mot de passe pour vérifier l'identité
4. Le compte est lié (`auth0_id` ajouté)
5. Désormais, connexion possible via Auth0 OU mot de passe

### Synchronisation des suppressions

**Q: Quel est le sens de synchronisation pour les suppressions ?**

**Auth0 → Collectives uniquement** (unidirectionnel)

- Suppression utilisateur dans Auth0 Dashboard → Webhook désactive le compte Collectives
- Suppression utilisateur dans Collectives → AUCUN impact sur Auth0

Pour activer, voir `docs/auth0/DEPLOYMENT.md` section "Webhooks".

### Mot de passe

**Q: Les comptes créés via Auth0 ont-ils un mot de passe ?**

- **Mode extranet** : NON, authentification via Auth0 uniquement
- **Mode local** : OUI, saisi lors de l'inscription

**Q: Puis-je réinitialiser mon mot de passe si j'utilise Auth0 ?**

Non, la gestion du mot de passe se fait dans Auth0 (Forgot Password).

### Rôles et permissions

**Q: Les rôles Collectives sont-ils gérés dans Auth0 ?**

**Non.** Auth0 gère uniquement l'authentification (qui est l'utilisateur).
Les rôles et permissions (encadrant, admin, etc.) restent dans Collectives.

Workflow :
1. Auth0 authentifie l'utilisateur
2. Collectives récupère le compte via `auth0_id`
3. Les rôles du compte Collectives sont appliqués

### Force SSO

**Q: Si j'active Force SSO, comment les admins se connectent-ils en cas d'urgence ?**

Avec `AUTH0_BYPASS_ENABLED = True`, accéder à `/auth/admin/login`.

Cette route affiche le formulaire classique même en mode Force SSO.

### Webhook

**Q: Le webhook Auth0 est-il déjà configuré ?**

**Non**, le code est prêt mais vous devez configurer le webhook dans Auth0 Dashboard :
1. Consulter [DEPLOYMENT.md](DEPLOYMENT.md) section "Configuration des webhooks"
2. Créer un Custom Webhook Stream dans Auth0
3. URL : `https://votre-domaine.com/api/webhooks/auth0`
4. Activer l'événement `user.deleted`
5. Configurer le secret HMAC dans `AUTH0_WEBHOOK_SECRET`

⚠️ **Sans cette configuration, les suppressions Auth0 ne seront pas synchronisées vers Collectives.**

---

## Ressources complémentaires

- [FLOWS.md](FLOWS.md) - Diagrammes détaillés des 8 scénarios utilisateur
- [DEPLOYMENT.md](DEPLOYMENT.md) - Guide de déploiement production
- [Auth0 Documentation](https://auth0.com/docs/)

---

## Support

Pour toute question ou problème :
1. Consulter `DEPLOYMENT.md` section Troubleshooting
2. Vérifier les logs : `tail -f logs/collectives.log | grep auth0`
3. Contacter l'équipe technique

