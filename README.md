# Realtime Chat (Django + Channels)

Advanced real-time chat app ready for GitHub copy-paste & deploy.

Features:
- Django auth (register/login)
- Public + Private rooms, 1-on-1 chats
- Real-time messaging (Django Channels)
- Typing indicators, read receipts, online presence
- File attachments (media)
- Browser notifications

Deployment notes:
- Add Redis (set REDIS_URL)
- Set SECRET_KEY, DEBUG=False in production
- Run migrations, collectstatic
- Procfile uses daphne

Commands (after deploy/SSH or using web console):
- python manage.py migrate
- python manage.py createsuperuser
- python manage.py collectstatic --noinput
