# Techorbyte Central Project Preview Portal

## URLs after installation
- Client login: `https://demo.techorbyte.com/`
- Central project-access admin: `https://demo.techorbyte.com/portal-admin/`
- Zenvibe preview: `https://demo.techorbyte.com/projects/zenvibe/`
- Zenvibe's own admin: `https://demo.techorbyte.com/projects/zenvibe/admin/`

## Safe installation
1. Back up the complete live `demo_portal` folder and database.
2. Upload and merge this package into `public_html/demo_portal`.
3. Do not delete or overwrite your live `zenvibe_site/db.sqlite3` unless intentionally restoring the packaged database.
4. Activate the WHC virtual environment and run:

```bash
source /home/utwsig55/virtualenv/public_html/demo_portal/3.10/bin/activate
cd ~/public_html/demo_portal/zenvibe_site
python manage.py migrate
python manage.py collectstatic --noinput
touch ~/public_html/demo_portal/tmp/restart.txt
```

## First project record
Open `/portal-admin/` with your existing Django superuser and add:
- Project name: Zenvibe
- Project ID: your chosen ID
- Set/reset password: your chosen password
- Folder: zenvibe
- Preview URL: `/projects/zenvibe/`
- Admin URL: `/projects/zenvibe/admin/`
- Active: enabled

The client portal password only unlocks the assigned project. The project's own Django admin still uses its existing Django admin username and password.

## Adding future projects
A future project must first be routed by Django or Passenger at its `/projects/<folder>/` path. Then create its access record in `/portal-admin/`. The central portal does not automatically deploy arbitrary application code simply by creating a database record.
