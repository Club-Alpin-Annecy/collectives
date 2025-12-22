# Auth0 SSO - Documentation

La documentation Auth0 a été réorganisée dans le dossier `docs/auth0/`.

## 📚 Documentation disponible

### 🚀 [README.md](docs/auth0/README.md)
Guide complet de configuration et démarrage rapide
- Installation
- Configuration Auth0 Dashboard
- Variables d'environnement
- Modes de fonctionnement (optionnel, Force SSO, bypass admin)
- FAQ

### 🔄 [FLOWS.md](docs/auth0/FLOWS.md)
Diagrammes détaillés des 8 scénarios utilisateur
- Nouvel utilisateur (local/extranet)
- Utilisateur existant lie son compte
- Login Auth0
- Fallback mot de passe
- Webhook suppressions
- Admin bypass
- Social login
- Gestion d'erreurs

### 🚀 [DEPLOYMENT.md](docs/auth0/DEPLOYMENT.md)
Guide de déploiement production
- Configuration détaillée
- Migration base de données
- **Configuration du webhook Auth0** (étape par étape)
- Tests de validation
- Stratégie de déploiement progressif
- Troubleshooting
- Rollback

---

## ⚡ Quick Start

```bash
# 1. Configurer instance/config.py
AUTH0_ENABLED = True
AUTH0_DOMAIN = "your-tenant.eu.auth0.com"
AUTH0_CLIENT_ID = "your_client_id"
AUTH0_CLIENT_SECRET = "your_client_secret"

# Mode Force SSO (optionnel)
AUTH0_FORCE_SSO = True
AUTH0_BYPASS_ENABLED = True

# 2. Appliquer la migration
FLASK_APP=collectives:create_app uv run flask db upgrade

# 3. Démarrer
uv run python run.py
```

➡️ Consulter [docs/auth0/README.md](docs/auth0/README.md) pour plus de détails

---

## 🔑 Points importants

### Synchronisation des suppressions
**Auth0 → Collectives uniquement** (unidirectionnel)

- Supprimer un utilisateur dans Auth0 → désactive le compte Collectives
- Supprimer un utilisateur dans Collectives → AUCUN impact sur Auth0

Voir [DEPLOYMENT.md](docs/auth0/DEPLOYMENT.md) section "Webhooks" pour la configuration.

### Mot de passe
- **Mode extranet** : Pas de mot de passe (Auth0 uniquement)
- **Mode local** : Mot de passe saisi lors de l'inscription

### Rôles
Les rôles Collectives (encadrant, admin, etc.) restent gérés dans Collectives, pas dans Auth0.

---

## 📞 Support

Pour toute question :
1. Consulter la FAQ dans [docs/auth0/README.md](docs/auth0/README.md)
2. Vérifier le Troubleshooting dans [docs/auth0/DEPLOYMENT.md](docs/auth0/DEPLOYMENT.md)
3. Logs : `tail -f logs/collectives.log | grep auth0`

