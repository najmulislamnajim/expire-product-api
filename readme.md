# EXPIRE PRODUCT  API

## Technologies
-Django REST Framework, MySQL.

## Run this project

To initiaize project, run

```bash
pip install -r requirements.txt
```

To run on dev server,

```bash
python manage.py runserver
```

## API Docs

Go to the following path to view the docs.

```bash
/api/v1/docs
```

## Testing

### Create and seed database

Run the following command to create your database.

```bash
python manage.py makemigrations
python manage.py migrate
```

To create admin user,

```bash
python manage.py createsuperadmin

```
