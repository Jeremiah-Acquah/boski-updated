Boski mobile update (includes the earlier admin-login update)
=============================================================
Extract this zip INTO your boski_market project folder (the one with manage.py)
and choose "Replace" when asked. 16 files change; nothing is deleted, and your
database, photos and .env are not touched.

What changed
- Product page: now fits phones properly (it used to stretch wider than the screen
  on products with several photos). Name, price and Preorder are visible on the first screen.
- Admin dashboard: on phones it has a bottom tab bar, product/banner/request cards with
  big on/off switches, and easy forms with a Save button that stays on screen.

If you have NOT yet applied the earlier login update: also change this line in .env
   DJANGO_ADMIN_URL=manage/   ->   DJANGO_ADMIN_URL=admin/
(manage/ now belongs to the dashboard.)

Then restart:  python manage.py runserver
Live site (PythonAnywhere): git push, then in the console: git pull,
   python manage.py collectstatic --noinput   and press Reload on the Web tab.
Tip: if the phone still shows the old look, refresh the page twice (it caches the old CSS).
