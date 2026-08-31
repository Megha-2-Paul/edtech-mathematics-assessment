# MySQL development database

The assessment platform now uses MySQL through SQLAlchemy.

## 1. Create the database

In MySQL Workbench or the MySQL client, run:

```sql
CREATE DATABASE edtech_assessment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 2. Configure local credentials

Copy `.env.example` to `.env` in the project root and set the local MySQL username/password. Never commit `.env`.

## 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 4. Initialize tables

From the project root:

```powershell
python -c "from database import initialize_database; initialize_database(); print('Database initialized')"
```

The schema creates students, academic profiles, chapter/improvement data, plans, subscriptions, payments, tests, questions, test-question mappings, attempts, responses, answer images, evaluation errors, and question history.

The application currently keeps a small in-process cache for compatibility with the existing MVP service interface, but MySQL is the persistent source of truth.
