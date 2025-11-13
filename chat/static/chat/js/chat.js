// chat.js — single file to handle websocket, typing, read receipts, file upload, presence, notifications

function initChat(wsPath, roomName, currentUser) {
    const chatSocket = new WebSocket(wsPath);
    const messagesDiv = document.getElementById('messages');
    const input = document.getElementById('message-input');
    const fileInput = document.getElementById('file-input');
    const form = document.getElementById('chat-form');
    const presenceList = document.getElementById('online-list');
    const loadMoreBtn = document.getElementById('load-more');

    // store online users
    const onlineUsers = new Set();

    chatSocket.onopen = function() {
        console.log('WebSocket connected');
    }

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'message') {
            appendMessage(data);
            notifyIfNeeded(data);
        } else if (data.type === 'typing') {
            // show typing indicator (simple)
            // optional: implement display
        } else if (data.type === 'read') {
            markMessageReadInUI(data.message_id, data.username);
        } else if (data.type === 'presence') {
            if (data.action === 'join') {
                onlineUsers.add(data.username);
            } else if (data.action === 'leave') {
                onlineUsers.delete(data.username);
            }
            updatePresenceUI();
        }
    }

    chatSocket.onclose = function() {
        console.log('WebSocket closed');
    }

    function appendMessage(msg) {
        const div = document.createElement('div');
        div.className = 'message';
        div.dataset.id = msg.id;
        let html = `<b>${escapeHtml(msg.username)}</b> <small>${new Date(msg.timestamp).toLocaleString()}</small><br>`;
        html += `<span class="content">${escapeHtml(msg.content)}</span>`;
        if (msg.attachment_url) {
            html += `<div><a href="${msg.attachment_url}" target="_blank">Attachment</a></div>`;
        }
        html += `<div class="read-by">Read by: <span class="read-list">you</span></div>`;
        div.innerHTML = html;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    function escapeHtml(text) {
        if (!text) return '';
        return text.replace(/[&<>"'`=\/]/g, function (s) {
            return ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;',
                '/': '&#x2F;',
                '`': '&#x60;',
                '=': '&#x3D;'
            })[s];
        });
    }

    function notifyIfNeeded(msg) {
        if (document.hidden && Notification && Notification.permission === 'granted' && msg.username !== currentUser) {
            new Notification(`New message from ${msg.username}`, { body: msg.content || 'Attachment' });
        }
    }

    // request permission for notifications
    if (window.Notification && Notification.permission !== 'granted') {
        Notification.requestPermission().then(function(permission) {
            console.log('Notification permission:', permission);
        });
    }

    // send a message or file
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const text = input.value.trim();
        if (fileInput.files.length > 0) {
            // upload file via endpoint
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            formData.append('text', text);
            const res = await fetch(`/rooms/${roomName}/upload/`, {
                method: 'POST',
                headers: {'X-CSRFToken': window.CSRF_TOKEN},
                body: formData
            });
            const json = await res.json();
            // the server will also broadcast the message via websocket when saved (if desired)
            input.value = '';
            fileInput.value = '';
            return;
        }
        if (text.length === 0) return;
        chatSocket.send(JSON.stringify({ type: 'message', message: text, username: currentUser }));
        input.value = '';
    });

    // typing indicator (throttle)
    let typingTimer;
    input.addEventListener('input', function() {
        clearTimeout(typingTimer);
        chatSocket.send(JSON.stringify({ type: 'typing', username: currentUser }));
        typingTimer = setTimeout(function(){}, 1000);
    });

    // load more messages (pagination)
    loadMoreBtn.addEventListener('click', async function() {
        let page = parseInt(loadMoreBtn.dataset.page) + 1;
        const res = await fetch(`/api/messages/${roomName}/?page=${page}&per_page=50`);
        const data = await res.json();
        if (data.messages && data.messages.length) {
            const prevScrollHeight = messagesDiv.scrollHeight;
            data.messages.forEach(m => {
                const div = document.createElement('div');
                div.className = 'message';
                div.dataset.id = m.id;
                div.innerHTML = `<b>${escapeHtml(m.username)}</b> <small>${new Date(m.timestamp).toLocaleString()}</small><br>
                    <span class="content">${escapeHtml(m.content)}</span>
                    ${m.attachment_url ? `<div><a href="${m.attachment_url}" target="_blank">Attachment</a></div>` : ''}
                    <div class="read-by">Read by: ${m.read_by.join(' ') || 'none'}</div>`;
                messagesDiv.insertBefore(div, messagesDiv.firstChild);
            });
            loadMoreBtn.dataset.page = page;
            // keep scroll at previous spot
            messagesDiv.scrollTop = messagesDiv.scrollHeight - prevScrollHeight;
        } else {
            loadMoreBtn.disabled = true;
            loadMoreBtn.innerText = 'No more';
        }
    });

    // mark messages visible as read (simple implementation)
    window.addEventListener('focus', function() {
        document.querySelectorAll('.message').forEach(div => {
            const id = div.dataset.id;
            if (id) {
                chatSocket.send(JSON.stringify({ type: 'read', message_id: parseInt(id) }));
            }
        });
    });

    function markMessageReadInUI(messageId, username) {
        const div = document.querySelector(`.message[data-id="${messageId}"]`);
        if (!div) return;
        const el = div.querySelector('.read-list');
        if (!el) return;
        let text = el.innerText || '';
        if (!text.includes(username)) {
            el.innerText = (text + ' ' + username).trim();
        }
    }

    function updatePresenceUI() {
        presenceList.innerText = Array.from(onlineUsers).join(', ');
    }
}
