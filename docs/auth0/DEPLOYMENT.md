# Auth0 - Guide de Déploiement Production

Ce guide vous accompagne dans le déploiement d'Auth0 en production pour l'application Collectives.

## Table des matières

1. [Pré-requis](#pré-requis)
2. [Configuration Auth0 Dashboard](#configuration-auth0-dashboard)
3. [Variables d'environnement](#variables-denvironnement)
4. [Migration de la base de données](#migration-de-la-base-de-données)
5. [Configuration des webhooks](#configuration-des-webhooks)
6. [Tests de validation](#tests-de-validation)
7. [Déploiement progressif](#déploiement-progressif)
8. [Monitoring](#monitoring)
9. [Rollback](#rollback)
10. [Checklist finale](#checklist-finale)

---

## Pré-requis

### Infrastructure

- ✅ Application Collectives déployée et fonctionnelle
- ✅ HTTPS configuré sur le domaine (obligatoire pour OAuth2)
- ✅ Accès SSH ou déploiement automatisé
- ✅ Accès à la base de données de production

### Auth0

- ✅ Compte Auth0 (plan adapté : Free, Developer, ou supérieur)
- ✅ Tenant Auth0 créé (ex: `collectives-prod.auth0.com`)
- ✅ Rôle Admin sur le tenant

### Dépendances Python

- ✅ `authlib>=1.2.0`
- ✅ `cryptography>=41.0.0`
- ✅ `requests` (pour téléchargement avatars)

Vérifier avec :
```bash
uv add authlib cryptography
```

---

## Configuration Auth0 Dashboard

### 1. Créer une Application

1. Aller sur **Auth0 Dashboard** → **Applications** → **Create Application**
2. Nom : `Collectives Production`
3. Type : **Regular Web Application**
4. Cliquer sur **Create**

### 2. Configurer l'application

Dans l'onglet **Settings** :

#### Application URIs

```
Application Login URI:
https://collectives.example.com/auth/login

Allowed Callback URLs:
https://collectives.example.com/auth/callback/auth0

Allowed Logout URLs:
https://collectives.example.com/auth/login

Allowed Web Origins:
https://collectives.example.com
```

⚠️ **Important** : Remplacer `collectives.example.com` par votre domaine réel.

#### Récupérer les credentials

- **Domain** : `your-tenant.auth0.com`
- **Client ID** : `abc123...` (copier)
- **Client Secret** : `xyz789...` (copier et sécuriser !)

#### Paramètres recommandés

- **Token Endpoint Authentication Method** : `Post`
- **Application Type** : `Regular Web App`
- **Refresh Token Rotation** : `Enabled`
- **Refresh Token Expiration** : `Absolute` - 30 jours

### 3. Configurer les Social Connections

1. Aller sur **Authentication** → **Social**
2. Activer les providers souhaités :
   - **Google** (recommandé)
   - **Microsoft** (recommandé)
   - Facebook, GitHub, etc. (optionnel)
3. Pour chaque provider :
   - Créer OAuth App sur le provider
   - Copier Client ID / Secret
   - Configurer dans Auth0

**Exemple Google** :
1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un projet "Collectives SSO"
3. Activer Google+ API
4. Créer OAuth 2.0 credentials
5. Authorized redirect URIs : `https://your-tenant.auth0.com/login/callback`

### 4. Configurer les règles de sécurité

#### Brute-force Protection

1. Aller sur **Security** → **Attack Protection**
2. Activer **Brute-force Protection**
3. Paramètres :
   - Threshold : 10 tentatives
   - Duration : 1 heure
   - Email notification : Activé

#### Suspicious IP Throttling

1. Activer **Suspicious IP Throttling**
2. Threshold : 100 requêtes / heure

### 5. Personnalisation (optionnel)

#### Universal Login

1. Aller sur **Branding** → **Universal Login**
2. Personnaliser :
   - Logo
   - Couleurs primaires
   - Page de login
   - Textes (Français)

#### Emails

1. Aller sur **Branding** → **Email Templates**
2. Personnaliser les templates :
   - Welcome Email
   - Password Reset
   - etc.

---

## Variables d'environnement

### Fichier `.env` ou configuration serveur

```bash
# ========================================
# Auth0 Configuration
# ========================================

# Enable Auth0
AUTH0_ENABLED=true

# Auth0 Credentials
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_client_id_here
AUTH0_CLIENT_SECRET=your_client_secret_here

# ========================================
# Auth0 Modes
# ========================================

# Force SSO Mode (hide classic login)
# Set to true to only show Auth0 login button
AUTH0_FORCE_SSO=false

# Admin Bypass (emergency fallback)
# Set to true to enable /auth/admin/login
AUTH0_BYPASS_ENABLED=false

# ========================================
# Auth0 Webhooks
# ========================================

# Webhook Secret for signature verification
# Generate with: openssl rand -hex 32
AUTH0_WEBHOOK_SECRET=your_webhook_secret_here

# ========================================
# Application Settings (existing)
# ========================================

# These should already be configured
SECRET_KEY=your_secret_key_here
EXTRANET_ACCOUNT_ID=your_extranet_id
# ...
```

### Génération du Webhook Secret

```bash
openssl rand -hex 32
```

Copier le résultat dans `AUTH0_WEBHOOK_SECRET`.

### Validation des variables

Créer un script `check_auth0_config.py` :

```python
import os

required_vars = [
    "AUTH0_ENABLED",
    "AUTH0_DOMAIN",
    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
]

optional_vars = [
    "AUTH0_FORCE_SSO",
    "AUTH0_BYPASS_ENABLED",
    "AUTH0_WEBHOOK_SECRET",
]

print("Checking Auth0 configuration...")
print("=" * 50)

for var in required_vars:
    value = os.environ.get(var)
    if value:
        print(f"✅ {var}: {'*' * 20} (set)")
    else:
        print(f"❌ {var}: NOT SET (required)")

print()
for var in optional_vars:
    value = os.environ.get(var)
    if value:
        print(f"✅ {var}: {'*' * 20} (set)")
    else:
        print(f"⚠️  {var}: not set (optional)")
```

Exécuter :
```bash
uv run python check_auth0_config.py
```

---

## Migration de la base de données

### 1. Vérifier la migration

```bash
cd /path/to/collectives
uv run flask db current
```

Doit afficher la migration actuelle.

### 2. Appliquer la migration Auth0

```bash
uv run flask db upgrade
```

Cette commande applique la migration `4d25910e8aa5_add_auth0_id_to_user_model.py` qui :
- Ajoute la colonne `auth0_id` à la table `users`
- Crée un index unique sur `auth0_id`

### 3. Vérifier la migration

```bash
uv run flask db current
```

Doit afficher : `4d25910e8aa5 (head)`

### 4. Vérification en base

```sql
-- PostgreSQL
\d users

-- MySQL
DESCRIBE users;

-- SQLite
.schema users
```

Vérifier la présence de :
- Colonne `auth0_id VARCHAR(255) NULL`
- Index `ix_users_auth0_id` (UNIQUE)

### 5. Rollback (si besoin)

En cas de problème :
```bash
uv run flask db downgrade -1
```

---

## Configuration des webhooks

⚠️ **Configuration requise** : Cette fonctionnalité nécessite une configuration manuelle dans Auth0 Dashboard. Sans cette configuration, les suppressions de compte Auth0 ne seront PAS synchronisées vers Collectives.

⚠️ **Important** : La synchronisation des suppressions est **unidirectionnelle** : Auth0 → Collectives uniquement.
- Supprimer un utilisateur dans Auth0 → désactive le compte Collectives (via webhook)
- Supprimer un utilisateur dans Collectives → AUCUN impact sur Auth0

### 1. Créer un webhook dans Auth0 Dashboard

#### Étape par étape :

1. **Accéder aux Streams**
   - Aller sur Auth0 Dashboard
   - Menu : **Monitoring** → **Streams**
   - Cliquer **+ Create Stream**

2. **Choisir le type**
   - Sélectionner **Custom Webhook**
   - Cliquer **Continue**

3. **Configuration du Stream**
   - **Name** : `Collectives User Sync`
   - **Endpoint URL** : `https://collectives.example.com/api/webhooks/auth0`
     
     ⚠️ Remplacer `collectives.example.com` par votre domaine réel
     
     ⚠️ L'URL doit être en **HTTPS** (Auth0 n'accepte pas HTTP en production)
   
   - **Authorization** (optionnel) : Laisser vide ou `Bearer <votre_token>`
   
   - **Content Type** : `application/json` (par défaut)

4. **Configuration du Secret**
   
   Le secret sert à signer les webhooks pour vérifier leur authenticité.
   
   - Générer un secret fort :
     ```bash
     openssl rand -hex 32
     ```
   
   - Copier le résultat (64 caractères hexadécimaux)
   
   - Dans Auth0, section **Signing Key** :
     - Coller le secret
     - Algorithme : **HS256** (par défaut)
   
   - Ajouter ce même secret dans votre configuration Collectives :
     ```bash
     AUTH0_WEBHOOK_SECRET="le_secret_généré"
     ```

5. **Sauvegarder**
   - Cliquer **Save**
   - Le stream est créé mais pas encore actif

### 2. Configurer les événements

Par défaut, aucun événement n'est activé. Nous n'avons besoin que de `user.deleted`.

1. Dans votre Stream nouvellement créé, cliquer **Configure Events**

2. **Événements disponibles** :
   - `user.created` ❌ Non nécessaire
   - `user.updated` ❌ Non nécessaire
   - `user.deleted` ✅ **Activer celui-ci**
   - `user.blocked` ❌ Non nécessaire
   - etc.

3. Cocher uniquement **user.deleted**

4. Cliquer **Save**

### 3. Activer le Stream

1. Retour sur la page du Stream
2. Toggle **Status** : OFF → **ON**
3. Le stream est maintenant actif ✅

**Que fait le webhook** :
- Quand un admin Auth0 supprime un utilisateur
- Auth0 envoie un POST vers `/api/webhooks/auth0`
- Le webhook vérifie la signature HMAC
- Si valide, désactive le compte Collectives (`enabled = False`, `auth0_id = None`)
- Les données utilisateur sont préservées (pas de suppression en cascade)

### 3. Test du webhook

#### Méthode 1 : Interface Auth0

1. Dans le stream créé, cliquer **Test**
2. Choisir événement `user.deleted`
3. Vérifier la réponse : `200 OK`

#### Méthode 2 : cURL

```bash
# Générer signature HMAC
PAYLOAD='{"type":"user.deleted","data":{"user_id":"auth0|test123"}}'
SECRET="your_webhook_secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

# Envoyer webhook
curl -X POST https://collectives.example.com/api/webhooks/auth0 \
  -H "Content-Type: application/json" \
  -H "X-Auth0-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

Réponse attendue :
```json
{"status": "not_found", "message": "User not found"}
```

(Normal : l'utilisateur test n'existe pas)

### 4. Vérifier les logs

```bash
tail -f logs/collectives.log | grep "auth0_webhook"
```

Doit afficher :
```
INFO: Received Auth0 webhook event: user.deleted
WARNING: User with auth0_id auth0|test123 not found
```

---

## Tests de validation

### Phase 1 : Tests en environnement de test

#### Test 1 : Login Auth0 basique

1. Aller sur `https://collectives.example.com/auth/login`
2. Cliquer "Se connecter avec Auth0"
3. Se connecter avec un compte test
4. Vérifier redirection vers `/`
5. Vérifier compte créé dans la base

```sql
SELECT id, mail, auth0_id, type, enabled 
FROM users 
WHERE mail = 'test@example.com';
```

#### Test 2 : Liaison de compte existant

1. Créer un utilisateur avec email `existing@example.com`
2. Se connecter via Auth0 avec le même email
3. Vérifier demande de mot de passe
4. Saisir mot de passe
5. Vérifier `auth0_id` renseigné dans la base

#### Test 3 : Webhook user.deleted

1. Créer un utilisateur via Auth0
2. Noter son `auth0_id`
3. Supprimer l'utilisateur dans Auth0 Dashboard
4. Vérifier webhook reçu dans les logs
5. Vérifier utilisateur désactivé :

```sql
SELECT enabled, auth0_id 
FROM users 
WHERE mail = 'deleted@example.com';
-- Doit retourner: enabled=FALSE, auth0_id=NULL
```

#### Test 4 : Admin bypass

1. Configurer `AUTH0_BYPASS_ENABLED=true`
2. Redémarrer l'application
3. Aller sur `/auth/admin/login`
4. Se connecter avec email + mot de passe
5. Vérifier connexion réussie

#### Test 5 : Force SSO

1. Configurer `AUTH0_FORCE_SSO=true`
2. Redémarrer l'application
3. Aller sur `/auth/login`
4. Vérifier seul bouton Auth0 visible
5. Vérifier lien "Connexion administrateur" présent

### Phase 2 : Tests en production

⚠️ **Attention** : Tester avec un compte réel mais non-critique d'abord.

```bash
# Checklist pré-prod
- [ ] Backup de la base de données effectué
- [ ] Variables d'environnement configurées
- [ ] Migration appliquée
- [ ] Webhook configuré
- [ ] Tests en environnement de test réussis
- [ ] Plan de rollback prêt
```

---

## Déploiement progressif

### Stratégie recommandée : Feature Toggle

#### Phase 1 : Déploiement "silencieux"

```bash
AUTH0_ENABLED=true
AUTH0_FORCE_SSO=false
AUTH0_BYPASS_ENABLED=false
```

- Auth0 disponible mais optionnel
- Login classique toujours visible
- Communiquer aux utilisateurs : "Nouveau mode de connexion disponible"

**Durée** : 2-4 semaines

#### Phase 2 : Encouragement

- Ajouter banner sur login classique : "Essayez la connexion Auth0 !"
- Envoyer email aux utilisateurs
- Statistiques : combien d'utilisateurs ont lié leur compte ?

```sql
SELECT COUNT(*) AS total_users,
       COUNT(auth0_id) AS auth0_users,
       (COUNT(auth0_id) * 100.0 / COUNT(*)) AS percentage
FROM users;
```

**Durée** : 4-6 semaines

#### Phase 3 : Force SSO (optionnel)

Si >80% des utilisateurs ont migré :

```bash
AUTH0_FORCE_SSO=true
AUTH0_BYPASS_ENABLED=true  # Fallback pour les 20% restants
```

- Login classique masqué
- Admin bypass disponible
- Communiquer clairement le changement

**Durée** : Permanent ou jusqu'à 100% de migration

### Rollback rapide

En cas de problème majeur :

```bash
# 1. Désactiver Auth0
AUTH0_ENABLED=false

# 2. Redémarrer l'application
systemctl restart collectives

# 3. Communiquer aux utilisateurs
```

---

## Monitoring

### Logs à surveiller

```bash
# Logs Auth0
tail -f logs/collectives.log | grep -E "auth0|Auth0"

# Erreurs Auth0
tail -f logs/collectives.log | grep -E "ERROR.*auth0"

# Webhooks
tail -f logs/collectives.log | grep "webhook"
```

### Métriques importantes

1. **Taux d'adoption Auth0**
   ```sql
   SELECT 
     COUNT(*) AS total_users,
     COUNT(auth0_id) AS auth0_linked,
     (COUNT(auth0_id) * 100.0 / COUNT(*)) AS percentage
   FROM users
   WHERE enabled = TRUE;
   ```

2. **Connexions Auth0 vs classiques**
   - Parser les logs
   - Compter les accès `/auth/login/auth0` vs `/auth/login`

3. **Erreurs Auth0**
   ```bash
   grep "ERROR.*auth0" logs/collectives.log | wc -l
   ```

4. **Webhooks reçus**
   ```bash
   grep "Received Auth0 webhook" logs/collectives.log | wc -l
   ```

### Dashboard de monitoring (optionnel)

Intégrer avec :
- **Prometheus** + **Grafana** pour métriques
- **Sentry** pour erreurs
- **Auth0 Dashboard** → **Monitoring** pour stats Auth0

---

## Rollback

### Procédure d'urgence

#### Étape 1 : Désactiver Auth0

```bash
# Dans .env ou configuration serveur
AUTH0_ENABLED=false
```

#### Étape 2 : Redémarrer l'application

```bash
# Systemd
sudo systemctl restart collectives

# Docker
docker-compose restart

# Manual
pkill -f "flask run" && flask run --host=0.0.0.0
```

#### Étape 3 : Vérifier

```bash
curl https://collectives.example.com/auth/login
# Ne doit plus afficher le bouton Auth0
```

#### Étape 4 : Rollback base de données (si nécessaire)

```bash
cd /path/to/collectives
uv run flask db downgrade 4d25910e8aa5
```

⚠️ **Attention** : Cela supprime la colonne `auth0_id`. Les liaisons seront perdues.

#### Étape 5 : Communiquer

- Informer les utilisateurs du retour au login classique
- Expliquer la raison du rollback
- Indiquer le délai avant nouvelle tentative

### Problèmes courants et solutions

| Problème | Cause probable | Solution |
|----------|----------------|----------|
| "Callback URL mismatch" | URL mal configurée dans Auth0 | Vérifier Allowed Callback URLs |
| Webhook 401 Unauthorized | Secret incorrect | Vérifier AUTH0_WEBHOOK_SECRET |
| "Auth0 not enabled" | Variable d'env non chargée | Vérifier .env et redémarrer |
| Utilisateurs ne peuvent plus se connecter | Force SSO activé trop tôt | Activer AUTH0_BYPASS_ENABLED |

---

## Checklist finale

### Avant déploiement

- [ ] Auth0 Application créée et configurée
- [ ] Callback URLs correctement définis
- [ ] Social Connections configurés (si utilisés)
- [ ] Variables d'environnement définies et vérifiées
- [ ] Migration de la base de données testée
- [ ] Webhook configuré et testé
- [ ] Tests de validation réussis en environnement de test
- [ ] Backup de la base de données effectué
- [ ] Plan de rollback documenté et compris
- [ ] Équipe technique informée

### Après déploiement

- [ ] Vérifier bouton Auth0 visible sur `/auth/login`
- [ ] Tester connexion Auth0 avec compte test
- [ ] Vérifier logs pour erreurs
- [ ] Tester webhook avec suppression d'un compte test
- [ ] Vérifier métriques d'adoption (après quelques jours)
- [ ] Communiquer aux utilisateurs

### Après 1 semaine

- [ ] Analyser les logs d'erreurs
- [ ] Vérifier taux d'adoption
- [ ] Collecter feedback utilisateurs
- [ ] Ajuster configuration si nécessaire

### Après 1 mois

- [ ] Décision : activer Force SSO ?
- [ ] Bilan : Auth0 apporte-t-il de la valeur ?
- [ ] Optimisations éventuelles

---

## Support

### Contacts

- **Auth0 Support** : https://support.auth0.com/
- **Documentation Auth0** : https://auth0.com/docs/
- **Collectives Team** : [Interne]

### Ressources complémentaires

- [AUTH0_SETUP.md](AUTH0_SETUP.md) - Configuration initiale
- [AUTH0_FLOWS.md](AUTH0_FLOWS.md) - Diagrammes des flux utilisateur
- [AUTH0_TROUBLESHOOTING.md](AUTH0_TROUBLESHOOTING.md) - Dépannage

---

## Conclusion

Le déploiement d'Auth0 doit être **progressif** et **réversible**. 

Recommandations finales :
1. Ne jamais forcer Force SSO tant que <80% des utilisateurs n'ont pas migré
2. Toujours garder le bypass admin activé en production (au cas où)
3. Monitorer activement les premiers jours
4. Être prêt à rollback rapidement si problème majeur

Bonne chance ! 🚀

