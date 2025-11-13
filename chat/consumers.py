import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Room, Message
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        # join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # notify presence
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'username': self.user.username if self.user.is_authenticated else 'Anonymous'
            }
        )

    async def disconnect(self, close_code):
        # leave group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'username': self.user.username if self.user.is_authenticated else 'Anonymous'
            }
        )

    async def receive(self, text_data):
        """
        Expected JSON:
        {
            "type": "message" | "typing" | "read",
            "message": "...",
            "username": "...",
            "message_id": 123 (for read),
        }
        """
        data = json.loads(text_data)
        action = data.get('type')

        if action == 'message':
            content = data.get('message', '')
            # optional: client can set 'attachment' via separate endpoint
            msg = await self.create_message(self.user, self.room_name, content)
            payload = {
                'type': 'chat_message',
                'id': msg['id'],
                'username': msg['username'],
                'content': msg['content'],
                'attachment_url': msg['attachment_url'],
                'timestamp': msg['timestamp'],
            }
            await self.channel_layer.group_send(self.room_group_name, payload)

        elif action == 'typing':
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'typing',
                'username': data.get('username'),
            })

        elif action == 'read':
            message_id = data.get('message_id')
            if message_id:
                await self.mark_read(self.user, message_id)
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'username': self.user.username,
                })

    # handlers for group_send events
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'username': event['username'],
            'content': event['content'],
            'attachment_url': event.get('attachment_url'),
            'timestamp': event['timestamp'],
        }))

    async def typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username'],
        }))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read',
            'message_id': event['message_id'],
            'username': event['username'],
        }))

    async def user_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'action': 'join',
            'username': event['username'],
        }))

    async def user_leave(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'action': 'leave',
            'username': event['username'],
        }))

    @database_sync_to_async
    def create_message(self, user, room_name, content):
        room, _ = Room.objects.get_or_create(name=room_name)
        msg = Message.objects.create(user=user, room=room, content=content, timestamp=timezone.now())
        return {
            'id': msg.id,
            'username': msg.user.username,
            'content': msg.content,
            'attachment_url': msg.attachment.url if msg.attachment else None,
            'timestamp': msg.timestamp.isoformat(),
        }

    @database_sync_to_async
    def mark_read(self, user, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            msg.read_by.add(user)
            return True
        except Message.DoesNotExist:
            return False
