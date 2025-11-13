import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.conf import settings
from .models import Room, Message
from django.utils import timezone

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat:lobby')
    else:
        form = UserCreationForm()
    return render(request, 'chat/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('chat:lobby')
    else:
        form = AuthenticationForm()
    return render(request, 'chat/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('chat:login')

@login_required
def lobby(request):
    rooms = Room.objects.filter(is_private=False).order_by('-created_at')
    return render(request, 'chat/lobby.html', {'rooms': rooms})

@login_required
@require_POST
def create_room(request):
    data = request.POST
    name = data.get('name').strip()
    is_private = data.get('is_private') == 'on'
    if not name:
        return JsonResponse({'error': 'Room name required'}, status=400)
    room, created = Room.objects.get_or_create(name=name, defaults={'is_private': is_private})
    if is_private:
        # add creator as participant
        room.participants.add(request.user)
    return JsonResponse({'room': room.name, 'created': created})

@login_required
def room_view(request, room_name):
    room, created = Room.objects.get_or_create(name=room_name)
    if room.is_private and request.user not in room.participants.all():
        return HttpResponseForbidden("Private room. You are not invited.")
    # add user to participants for private or public (optional)
    room.participants.add(request.user)
    # initial messages
    messages = room.messages.select_related('user').all().order_by('-timestamp')[:50]
    messages = reversed(messages)  # oldest first
    return render(request, 'chat/room.html', {
        'room_name': room.name,
        'messages': messages,
        'user': request.user,
    })

@login_required
@require_POST
def upload_file(request, room_name):
    room = get_object_or_404(Room, name=room_name)
    if room.is_private and request.user not in room.participants.all():
        return HttpResponseForbidden("Not allowed")
    file = request.FILES.get('file')
    text = request.POST.get('text', '')
    if not file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
    msg = Message.objects.create(user=request.user, room=room, content=text, attachment=file, timestamp=timezone.now())
    data = {
        'id': msg.id,
        'username': msg.user.username,
        'content': msg.content,
        'attachment_url': msg.attachment.url if msg.attachment else None,
        'timestamp': msg.timestamp.isoformat(),
    }
    return JsonResponse(data)

@login_required
def messages_api(request, room_name):
    room = get_object_or_404(Room, name=room_name)
    if room.is_private and request.user not in room.participants.all():
        return HttpResponseForbidden("Not allowed")
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    messages_qs = room.messages.select_related('user').all().order_by('-timestamp')
    paginator = Paginator(messages_qs, per_page)
    page_obj = paginator.get_page(page)
    items = []
    for m in page_obj:
        items.append({
            'id': m.id,
            'username': m.user.username,
            'content': m.content,
            'attachment_url': m.attachment.url if m.attachment else None,
            'timestamp': m.timestamp.isoformat(),
            'read_by': [u.username for u in m.read_by.all()],
        })
    return JsonResponse({
        'messages': list(reversed(items)),  # oldest first in response
        'page': page,
        'num_pages': paginator.num_pages,
    })
