# YeshuaBot

Bot Discord en français pour lire la Bible, suivre la liturgie catholique et
recevoir chaque jour un verset ou l'Évangile dans un salon.

Texte biblique : **Louis Segond 1910** (domaine public), stocké dans MySQL/MariaDB.

## Fonctionnalités

- Lecture d'un verset ou d'un chapitre entier, avec pagination par boutons
- Recherche plein texte dans toute la Bible ou dans un seul livre
- Verset du jour (le même pour tout le monde le même jour) et verset aléatoire
- Célébration liturgique du jour et lectures de la messe (Évangile ou lectures complètes)
- Envois automatiques planifiés par serveur, à l'heure et dans le fuseau horaire choisis
- Saisie assistée : autocomplétion des livres et des fuseaux horaires

## Commandes

| Commande | Rôle |
|---|---|
| `/verse` | affiche un verset (ex. Jean 3 16) |
| `/chapter` | affiche un chapitre, page par page |
| `/search` | cherche un texte dans la Bible et affiche les références |
| `/randomverse` | verset aléatoire |
| `/dailyverse` | verset du jour |
| `/infobook` | nombre de chapitres d'un livre |
| `/infoverse` | nombre de versets d'un chapitre |
| `/today` | célébration liturgique du jour (calendrier catholique) |
| `/gospel` | Évangile du jour |
| `/readings` | lectures complètes de la messe du jour |
| `/setdailyverse` · `/removedailyverse` | active / désactive l'envoi quotidien du verset |
| `/setdailygospel` · `/removedailygospel` | active / désactive l'envoi quotidien de l'Évangile |
| `/setdailyreadings` · `/removedailyreadings` | active / désactive l'envoi quotidien des lectures |
| `/help` | liste des commandes |
| `/reload` | recharge un module sans redémarrer (propriétaire du bot uniquement) |

## Technologies

- **Python 3.10 à 3.13** avec [py-cord](https://pycord.dev) (commandes slash, vues à boutons)
- **MySQL / MariaDB** via `mysql-connector-python`, requêtes paramétrées
- **Docker** : `Dockerfile` (image `python:3.13-slim`) et `docker-compose.yml` fournis
- **APScheduler** pour les envois quotidiens, **pytz** pour les fuseaux horaires
- API externes : [AELF](https://api.aelf.org) (lectures de la messe) et
  [Church Calendar API](http://calapi.inadiutorium.cz) (calendrier liturgique)

## Installation

### 1. Base de données

```bash
mysql -u root -p -e "CREATE DATABASE biblebot CHARACTER SET utf8mb4;
  CREATE USER 'bibleuser'@'localhost' IDENTIFIED BY 'motdepasse';
  GRANT ALL PRIVILEGES ON biblebot.* TO 'bibleuser'@'localhost';"
mysql -u root -p biblebot < segond_1910.sql
```

Puis créer les tables de configuration des envois automatiques :

```sql
CREATE TABLE IF NOT EXISTS daily_verse_settings (
    guild_id   BIGINT UNSIGNED PRIMARY KEY,
    channel_id BIGINT UNSIGNED NOT NULL,
    hour       TINYINT UNSIGNED NOT NULL,
    minute     TINYINT UNSIGNED NOT NULL,
    timezone   VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS daily_gospel_settings   LIKE daily_verse_settings;
CREATE TABLE IF NOT EXISTS daily_readings_settings LIKE daily_verse_settings;
```

### 2. Bot Discord

1. Créer une application sur le [portail développeur Discord](https://discord.com/developers/applications),
   puis un bot, et copier son jeton.
2. L'inviter sur un serveur avec les scopes `bot` et `applications.commands`.

### 3. Lancement

#### Avec Docker (méthode utilisée en production)

1. Copier `.env.example` en `.env` et renseigner `DISCORD_TOKEN` et `DB_PASSWORD`.
2. Le `docker-compose.yml` fourni se connecte à un réseau Docker **externe** nommé `mariadb_default`,
   dans lequel un conteneur `mariadb` héberge la base (`DB_HOST: mariadb`). Adaptez ces lignes à votre
   installation (autre réseau, autre hôte, ou base installée sur la machine).
3. Construire et lancer :

```bash
docker compose up -d --build
docker compose logs -f
```

#### Sans Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Le bot lit sa configuration dans les variables d'environnement (voir `.env.example`) :

| Variable | Valeur |
|---|---|
| `DISCORD_TOKEN` | jeton du bot |
| `DB_HOST` | hôte MySQL (défaut : `localhost`) |
| `DB_USER` | utilisateur (défaut : `bibleuser`) |
| `DB_PASSWORD` | mot de passe (obligatoire) |
| `DB_NAME` | base (défaut : `biblebot`) |

```bash
set -a; source .env; set +a
python yeshuabot.py
```

Les commandes `/set…` et `/remove…` ne vérifient pas les permissions de
l'utilisateur : pensez à les réserver aux modérateurs dans
*Paramètres du serveur → Intégrations → YeshuaBot*.

## Structure

```
yeshuabot.py            démarrage, chargement des modules, planificateur
config.py               configuration et correspondance noms de livres ↔ numéros
database.py             accès à la base (versets, recherche, réglages des envois)
bible_utils.py          analyse des références, mise en forme, pagination
liturgical_calendar.py  célébration du jour (traduction des rangs et couleurs)
liturgical_readings.py  lectures de la messe via l'API AELF
cogs/                   commandes Discord regroupées par thème
segond_1910.sql         texte de la Bible Louis Segond 1910
Dockerfile              image Docker du bot
docker-compose.yml      lancement avec Docker
.env.example            modèle de configuration (variables d'environnement)
```

## Licence

Code sous [licence MIT](LICENSE). Le texte de la Bible Louis Segond 1910 est dans le domaine public.

## Voir aussi

- [AlHudaBot](https://github.com/jejcqr/AlHudaBot), le bot équivalent pour le Coran et les hadiths
