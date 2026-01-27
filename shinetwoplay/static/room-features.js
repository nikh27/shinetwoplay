// Advanced Features for Room Page
// Voice Messages, Image Upload, Reactions, Reconnection, Error Handling

// ============= Global State =============
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let recordingTimer = null;
let selectedImage = null;
let reconnectAttempts = 0;
let reconnectTimeout = null;
let heartbeatInterval = null;
let messageQueue = [];
let tempMessageId = 0;

// ============= Voice Recording =============

function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const duration = Math.floor((Date.now() - recordingStartTime) / 1000);
            
            if (duration > 60) {
                showToast('Voice message too long. Maximum 60 seconds.', 'error');
                return;
            }
            
            await uploadVoiceMessage(audioBlob, duration);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        recordingStartTime = Date.now();
        
        // Show recording UI
        document.getElementById('recordingOverlay').classList.add('active');
        
        // Start timer
        updateRecordingTimer();
        recordingTimer = setInterval(updateRecordingTimer, 1000);
        
        // Send recording indicator
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                event: 'recording_voice'
            }));
        }
        
        // Auto-stop after 60 seconds
        setTimeout(() => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                stopRecording();
            }
        }, 60000);
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        showToast('Could not access microphone', 'error');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        clearInterval(recordingTimer);
        document.getElementById('recordingOverlay').classList.remove('active');
        
        // Send stopped recording indicator
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                event: 'stopped_recording'
            }));
        }
    }
}

function cancelRecording() {
    if (mediaRecorder) {
        mediaRecorder.stop();
        audioChunks = [];
        clearInterval(recordingTimer);
        document.getElementById('recordingOverlay').classList.remove('active');
    }
}

function updateRecordingTimer() {
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    document.getElementById('recordingTimer').textContent = 
        `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

async function uploadVoiceMessage(audioBlob, duration) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice.webm');
    formData.append('room_code', ROOM);
    formData.append('duration', duration);
    
    try {
        const response = await fetch('/api/upload/voice/', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Send via WebSocket
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    event: 'voice_message',
                    voice_url: data.data.voice_url,
                    duration: data.data.duration
                }));
            }
        } else {
            showToast('Failed to upload voice message', 'error');
        }
    } catch (error) {
        console.error('Voice upload error:', error);
        showToast('Failed to upload voice message', 'error');
    }
}

// ============= Image Upload =============

function selectImage() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            // Validate file size (10MB)
            if (file.size > 10 * 1024 * 1024) {
                showToast('Image too large. Maximum 10MB.', 'error');
                return;
            }
            
            // Validate file type
            if (!file.type.startsWith('image/')) {
                showToast('Please select an image file', 'error');
                return;
            }
            
            selectedImage = file;
            showImagePreview(file);
        }
    };
    input.click();
}

function showImagePreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('previewImg').src = e.target.result;
        document.getElementById('imagePreview').classList.add('active');
    };
    reader.readAsDataURL(file);
}

function cancelImage() {
    selectedImage = null;
    document.getElementById('imagePreview').classList.remove('active');
}

async function sendImage() {
    if (!selectedImage) return;
    
    const formData = new FormData();
    formData.append('image', selectedImage);
    formData.append('room_code', ROOM);
    
    // Show uploading indicator
    document.getElementById('imagePreview').classList.remove('active');
    showToast('Uploading image...', 'info');
    
    // Send uploading indicator
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            event: 'uploading_image'
        }));
    }
    
    try {
        const response = await fetch('/api/upload/image/', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Send via WebSocket
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    event: 'image_message',
                    image_url: data.data.image_url,
                    width: data.data.width,
                    height: data.data.height
                }));
            }
            selectedImage = null;
        } else {
            showToast('Failed to upload image', 'error');
        }
    } catch (error) {
        console.error('Image upload error:', error);
        showToast('Failed to upload image', 'error');
    }
}

// ============= Message Reactions =============

let currentReactionMessageId = null;

function showReactionPicker(messageId) {
    currentReactionMessageId = messageId;
    const picker = document.getElementById('reactionPicker');
    picker.classList.add('active');
    
    // Position picker near the message
    const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
    if (messageEl) {
        const rect = messageEl.getBoundingClientRect();
        picker.style.top = `${rect.top - 50}px`;
        picker.style.left = `${rect.left}px`;
    }
}

function hideReactionPicker() {
    document.getElementById('reactionPicker').classList.remove('active');
    currentReactionMessageId = null;
}

function addReaction(emoji) {
    if (!currentReactionMessageId) return;
    
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            event: 'react_message',
            message_id: currentReactionMessageId,
            emoji: emoji
        }));
    }
    
    hideReactionPicker();
}

function removeReaction(messageId, emoji) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            event: 'remove_reaction',
            message_id: messageId,
            emoji: emoji
        }));
    }
}

// ============= WebSocket Reconnection =============

function initializeWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(`${protocol}//${location.host}/ws/room/${ROOM}/?name=${USER}`);
    
    socket.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttempts = 0;
        hideReconnectOverlay();
        startHeartbeat();
        
        // Send queued messages
        while (messageQueue.length > 0) {
            const msg = messageQueue.shift();
            socket.send(JSON.stringify(msg));
        }
        
        // Sync state
        socket.send(JSON.stringify({ event: 'sync_state' }));
    };
    
    socket.onclose = () => {
        console.log('WebSocket disconnected');
        stopHeartbeat();
        attemptReconnect();
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        showToast('Connection error', 'error');
    };
    
    socket.onmessage = handleWebSocketMessage;
}

function attemptReconnect() {
    if (reconnectTimeout) return;
    
    showReconnectOverlay();
    
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
    reconnectAttempts++;
    
    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
    
    reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;
        initializeWebSocket();
    }, delay);
}

function showReconnectOverlay() {
    document.getElementById('reconnectOverlay').classList.add('active');
}

function hideReconnectOverlay() {
    document.getElementById('reconnectOverlay').classList.remove('active');
}

// ============= Heartbeat =============

function startHeartbeat() {
    heartbeatInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ event: 'ping' }));
        }
    }, 30000); // Every 30 seconds
}

function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
}

// ============= Optimistic Updates =============

function sendMessageWithOptimisticUpdate(message) {
    const tempId = `temp_${++tempMessageId}`;
    
    // Show message immediately
    displayMessage({
        id: tempId,
        sender: USER,
        msg: message,
        timestamp: new Date().toISOString(),
        message_type: 'chat',
        status: 'sending'
    });
    
    // Send to server
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            event: 'chat',
            msg: message,
            temp_id: tempId
        }));
    } else {
        // Queue if disconnected
        messageQueue.push({
            event: 'chat',
            msg: message,
            temp_id: tempId
        });
        updateMessageStatus(tempId, 'queued');
    }
}

function updateMessageStatus(tempId, status) {
    const messageEl = document.querySelector(`[data-temp-id="${tempId}"]`);
    if (messageEl) {
        messageEl.setAttribute('data-status', status);
        
        // Add status indicator
        let statusEl = messageEl.querySelector('.message-status');
        if (!statusEl) {
            statusEl = document.createElement('span');
            statusEl.className = 'message-status';
            messageEl.appendChild(statusEl);
        }
        
        if (status === 'sending') {
            statusEl.textContent = '⏳';
        } else if (status === 'sent') {
            statusEl.textContent = '✓';
        } else if (status === 'queued') {
            statusEl.textContent = '📤';
        } else if (status === 'error') {
            statusEl.textContent = '❌';
        }
    }
}

// ============= Enhanced WebSocket Message Handler =============

function handleWebSocketMessage(e) {
    const data = JSON.parse(e.data);
    const event = data.event;
    const payload = data.data || data;
    
    console.log('WebSocket message:', event, payload);
    
    switch (event) {
        case 'room_state':
            handleRoomState(payload);
            break;
        case 'player_join':
            handlePlayerJoin(payload);
            break;
        case 'player_disconnect':
            handlePlayerDisconnect(payload);
            break;
        case 'chat':
            handleChatMessage(payload);
            break;
        case 'voice_message':
            handleVoiceMessage(payload);
            break;
        case 'image_message':
            handleImageMessage(payload);
            break;
        case 'typing':
            handleTyping(payload);
            break;
        case 'ready_state':
            handleReadyState(payload);
            break;
        case 'game_selected':
            handleGameSelected(payload);
            break;
        case 'round_update':
            handleRoundUpdate(payload);
            break;
        case 'start_game':
            handleStartGame(payload);
            break;
        case 'message_reaction':
            handleMessageReaction(payload);
            break;
        case 'recording_voice':
            handleRecordingIndicator(payload);
            break;
        case 'uploading_image':
            handleUploadingIndicator(payload);
            break;
        case 'message_confirmed':
            handleMessageConfirmed(payload);
            break;
        case 'pong':
            // Heartbeat response
            break;
        case 'error':
            handleError(payload);
            break;
        default:
            console.warn('Unknown event:', event);
    }
}

function handleVoiceMessage(data) {
    displayVoiceMessage({
        id: data.message_id,
        sender: data.sender,
        voice_url: data.voice_url,
        duration: data.duration,
        timestamp: data.timestamp
    });
}

function handleImageMessage(data) {
    displayImageMessage({
        id: data.message_id,
        sender: data.sender,
        image_url: data.image_url,
        width: data.width,
        height: data.height,
        timestamp: data.timestamp
    });
}

function handleMessageReaction(data) {
    updateMessageReactions(data.message_id, data.user, data.emoji, data.action);
}

function handleRecordingIndicator(data) {
    if (data.user !== USER) {
        showToast(`${data.user} is recording...`, 'info');
    }
}

function handleUploadingIndicator(data) {
    if (data.user !== USER) {
        showToast(`${data.user} is uploading an image...`, 'info');
    }
}

function handleMessageConfirmed(data) {
    // Update temp message with real ID
    const messageEl = document.querySelector(`[data-temp-id="${data.temp_id}"]`);
    if (messageEl) {
        messageEl.setAttribute('data-message-id', data.message_id);
        messageEl.removeAttribute('data-temp-id');
        updateMessageStatus(data.temp_id, 'sent');
    }
}

function handleError(error) {
    showToast(error.message || 'An error occurred', 'error');
}

// ============= Display Functions =============

function displayVoiceMessage(data) {
    const chatBox = document.getElementById('chatBox');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${data.sender === USER ? 'sent' : 'received'}`;
    messageDiv.setAttribute('data-message-id', data.id);
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-sender">${data.sender}</span>
            <span class="message-time">${formatTime(data.timestamp)}</span>
        </div>
        <div class="voice-message">
            <audio controls src="${data.voice_url}"></audio>
            <span class="voice-duration">${formatDuration(data.duration)}</span>
        </div>
        <button class="reaction-btn" onclick="showReactionPicker('${data.id}')">😊</button>
    `;
    
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function displayImageMessage(data) {
    const chatBox = document.getElementById('chatBox');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${data.sender === USER ? 'sent' : 'received'}`;
    messageDiv.setAttribute('data-message-id', data.id);
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-sender">${data.sender}</span>
            <span class="message-time">${formatTime(data.timestamp)}</span>
        </div>
        <div class="image-message" onclick="openLightbox('${data.image_url}')">
            <img src="${data.image_url}" alt="Image" style="max-width: 200px; border-radius: 12px;">
        </div>
        <button class="reaction-btn" onclick="showReactionPicker('${data.id}')">😊</button>
    `;
    
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function updateMessageReactions(messageId, user, emoji, action) {
    const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
    if (!messageEl) return;
    
    let reactionsEl = messageEl.querySelector('.message-reactions');
    if (!reactionsEl) {
        reactionsEl = document.createElement('div');
        reactionsEl.className = 'message-reactions';
        messageEl.appendChild(reactionsEl);
    }
    
    if (action === 'add') {
        const reactionSpan = document.createElement('span');
        reactionSpan.className = 'reaction';
        reactionSpan.textContent = emoji;
        reactionSpan.onclick = () => removeReaction(messageId, emoji);
        reactionsEl.appendChild(reactionSpan);
    } else if (action === 'remove') {
        const reactions = reactionsEl.querySelectorAll('.reaction');
        reactions.forEach(r => {
            if (r.textContent === emoji) r.remove();
        });
    }
}

// ============= Toast Notifications =============

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} active`;
    
    setTimeout(() => {
        toast.classList.remove('active');
    }, 3000);
}

// ============= Utility Functions =============

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
}

function openLightbox(imageUrl) {
    const lightbox = document.getElementById('lightbox');
    document.getElementById('lightboxImg').src = imageUrl;
    lightbox.classList.add('active');
}

function closeLightbox() {
    document.getElementById('lightbox').classList.remove('active');
}

// ============= Enhanced Typing Indicator =============

let typingTimeout = null;
let lastTypingEvent = 0;

function handleTypingInput() {
    const now = Date.now();
    
    // Throttle to max once per 2 seconds
    if (now - lastTypingEvent < 2000) return;
    
    lastTypingEvent = now;
    
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ event: 'typing' }));
    }
    
    // Auto-stop typing after 5 seconds
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ event: 'stop_typing' }));
        }
    }, 5000);
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    initializeWebSocket();
    
    // Add typing event listener to input
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('input', handleTypingInput);
    }
});
