# Plan: Activités Suivies avec Notifications

## Objectif
Permettre aux utilisateurs de suivrese des activités et recevoir une notification email lorsqu'une collective est publiée. Auto-subscription lors de l'inscription, sauf si désabonnement explicite.

## Architecture

### 1. Modèle de données

**Table** `user_followed_activities` :
- `user_id` (Integer, FK users.id, PK)
- `activity_type_id` (Integer, FK activity_types.id, PK)
- `followed_at` (DateTime, default=current_time)
- `explicitly_unfollowed` (Boolean, default=False)
- `unfollowed_at` (DateTime, nullable)

**Relations** :
- `User.followed_activities` → ActivityType (activités suivies, filter explicitly_unfollowed=False)
- `ActivityType.followers` → User (utilisateurs suivant l'activité)

### 2. Migration Alembic

**Fichier** : `migrations/versions/XXX_add_followed_activities.py`

**Actions** :
1. Créer la table `user_followed_activities`
2. Créer les index sur `user_id` et `activity_type_id`
3. Peupler rétroactivement avec les couples (user, activity) des inscriptions passées
4. Toutes les entrées auront `explicitly_unfollowed = False`

**Requête de peuplement** :
```sql
INSERT INTO user_followed_activities (user_id, activity_type_id, followed_at, explicitly_unfollowed)
SELECT DISTINCT r.user_id, eat.activity_id, NOW(), False
FROM registrations r
JOIN events e ON r.event_id = e.id
JOIN event_activity_types eat ON e.id = eat.event_id
WHERE r.status IN (0, 1, 4)  -- Active, Waiting, PaymentPending
ON CONFLICT (user_id, activity_type_id) DO NOTHING;
```

### 3. Auto-subscription conditionnelle

**Fichiers modifiés** :
- `collectives/routes/event.py` : fonctions `self_register()` et `register_user()`

**Logique** :
```python
for activity in event.activity_types:
    # Vérifier si l'utilisateur s'est explicitement désabonné
    existing = UserFollowedActivity.query.filter_by(
        user_id=current_user.id,
        activity_type_id=activity.id
    ).first()

    if existing:
        if not existing.explicitly_unfollowed:
            # Met à jour la date
            existing.followed_at = current_time()
    else:
        # Crée une nouvelle entrée
        new_follow = UserFollowedActivity(
            user_id=current_user.id,
            activity_type_id=activity.id,
            followed_at=current_time(),
            explicitly_unfollowed=False
        )
        db.session.add(new_follow)
```

### 4. Interface profil utilisateur

**Fichiers créés/modifiés** :
- `collectives/routes/profile.py` : nouvelles routes
- `collectives/templates/profile/followed_activities.html` : nouveau template
- `collectives/forms/user.py` : ajout du champ dans les formulaires utilisateur

**Routes** :
- `GET /profile/followed-activities` : Affiche la liste des activités suivies
- `POST /profile/unfollow-activity/<int:activity_id>` : Désabonnement (avec confirmation page)

### 5. Bouton notification dans événement

**Fichiers modifiés** :
- `collectives/routes/event.py` : nouvelle route
- `collectives/templates/event/event.html` : ajout du bouton

**Route** :
- `POST /event/<int:event_id>/notify-followers` (nécessite d'être leader/admin)

**Logique** :
1. Vérifie que l'utilisateur est leader/admin de l'événement
2. Récupère tous les followers des activités de l'événement
3. Déduplique par utilisateur (une seule notif par utilisateur)
4. Envoie l'email de notification
5. Flash message de confirmation avec nombre de notifications envoyées

### 6. Email de notification

**Fichier** : `collectives/email_templates.py`

**Fonction** : `send_activity_notification_to_followers(event, sender_user)`

**Contenu email** :
- Objet : "Nouvelle collective : {event_title}"
- Corps :
  - Nom de l'activité
  - Détails de l'événement (titre, date, lieu, description)
  - Lien vers l'événement
  - Lien de désabonnement sécurisé

**Lien de désabonnement** :
- URL : `/profile/unfollow-activity/<activity_id>?token=<signed_token>`
- Token signé avec `URLSafeTimedSerializer` (secret key, salt='unfollow-activity')
- Contenu : `{"user_id": X, "activity_id": Y}`
- Validité : 30 jours

### 7. Route de désabonnement sécurisé

**Fichier** : `collectives/routes/profile.py`

**Route** : `GET /profile/unfollow-activity/<int:activity_id>`

**Logique** :
1. Récupère le token depuis les query params
2. Décode et vérifie le token signé (user_id doit correspondre au current_user)
3. Vérifie que activity_id correspond
4. Met à jour l'entrée : `explicitly_unfollowed = True`, `unfollowed_at = now()`
5. Flash message : "Vous ne suivez plus l'activité {activity_name}"
6. Redirige vers `/profile/followed-activities`

### 8. Modèles à créer/modifier

**Nouveau fichier** : `collectives/models/user_followed_activity.py`

```python
class UserFollowedActivity(db.Model):
    """Association entre utilisateur et activité suivie"""
    __tablename__ = "user_followed_activities"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    activity_type_id = db.Column(db.Integer, db.ForeignKey("activity_types.id"), primary_key=True)
    followed_at = db.Column(db.DateTime, nullable=False, default=current_time)
    explicitly_unfollowed = db.Column(db.Boolean, default=False)
    unfollowed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="followed_activities_assoc")
    activity_type = db.relationship("ActivityType", back_populates="followers_assoc")
```

**Modifications** :
- `collectives/models/user/__init__.py` : ajout de la relation
- `collectives/models/activity_type.py` : ajout de la relation inverse
- `collectives/models/__init__.py` : export du nouveau modèle

### 9. Dépendances

**Modules utilisés** :
- `itsdangerous.URLSafeTimedSerializer` pour les tokens signés
- `flask.url_for` pour générer les liens
- `collectives.utils.time.current_time` pour les timestamps
- `collectives.utils.mail.send_mail` pour l'envoi d'emails

### 10. Tests

**Fichiers de test** :
- `tests/unit/test_followed_activities.py` : tests unitaires du modèle
- `tests/events/test_notifications.py` : tests d'intégration des notifications

**Scénarios de test** :
1. Auto-subscription lors de l'inscription
2. Non réabonnement après désabonnement explicite
3. Envoi de notification par un leader
4. Désabonnement via lien sécurisé
5. Token expiré/invalid

## Ordre d'implémentation

1. ✅ Créer ce plan
2. Créer le modèle `UserFollowedActivity`
3. Créer la migration Alembic
4. Modifier les routes d'inscription pour auto-subscription
5. Créer les routes de profil (liste et désabonnement)
6. Créer le template de gestion des activités suivies
7. Modifier le template d'événement pour ajouter le bouton
8. Créer la route de notification
9. Créer le template d'email
10. Tester et valider

## Notes

- Une seule notification par utilisateur par événement (même si plusieurs activités suivies)
- Respect strict du désabonnement explicite
- Token de désabonnement valide 30 jours
- Le lien de désabonnement dans l'email doit être clair et accessible

## Status

**TERMINÉ** - Toutes les fonctionnalités ont été implémentées et testées.

### Fichiers créés/modifiés

**Modèles:**
- collectives/models/user_followed_activity.py (nouveau)
- collectives/models/user/model.py (ajout relations et méthodes)
- collectives/models/activity_type.py (ajout relation inverse)
- collectives/models/__init__.py (export UserFollowedActivity)

**Migration:**
- migrations/versions/c84f9ec33732_add_user_followed_activities.py

**Routes:**
- collectives/routes/event.py (auto-subscription + route notification)
- collectives/routes/profile.py (routes gestion activités suivies)

**Templates:**
- collectives/templates/profile/followed_activities.html (nouveau)
- collectives/templates/event/partials/admin.html (bouton notification)
- collectives/templates/partials/main-navigation.html (lien menu)

**Emails:**
- collectives/email_templates.py (fonction send_event_notification_to_followers)
- collectives/configuration.yaml (templates de messages)

**Tests:**
- tests/unit/test_followed_activities.py (5 tests unitaires)

### Fonctionnalités livrées

1. Table user_followed_activities avec clé composite (user_id, activity_type_id)
2. Migration rétroactive qui peuple automatiquement depuis les inscriptions existantes
3. Auto-subscription lors de l'inscription à une collective (respecte le désabonnement explicite)
4. Interface profil pour voir/gérer les activités suivies (/profile/followed-activities)
5. Bouton "Notifier les abonnés" sur les événements publiés (visible aux leaders)
6. Envoi d'emails aux abonnés avec lien de désabonnement sécurisé (token valide 30 jours)
7. Désabonnement via lien sécurisé dans l'email

### Tests

37 tests unitaires passent, dont 5 nouveaux tests pour UserFollowedActivity.
