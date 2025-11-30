document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const messagesContainer = document.getElementById('messagesContainer');

    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value.trim() === '') {
            this.style.height = 'auto';
        }
    });

    // Handle Enter key
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        userInput.value = '';
        userInput.style.height = 'auto';

        showTypingIndicator();

        try {
            const resp = await fetch('/api/generate', {   
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt: text })
            });

            const data = await resp.json();
            removeTypingIndicator();

            if (!data.ok) {
                appendMessage('ai', 'Server error: ' + (data.error || 'Unknown error'));
                return;
            }

            streamResponse(data.text);

        } catch (err) {
            removeTypingIndicator();
            appendMessage('ai', 'Network error: ' + err.message);
        }
    }

    function appendMessage(role, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const avatar = role === 'ai' 
            ? '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2Z"/><path d="m9 12 2 2 4-4"/></svg>'
            : '<div style="width: 24px; height: 24px; background: #555; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px;">U</div>';

        const contentHtml = (role === 'ai' && text === '')
            ? '<div class="message-content"></div>'
            : `<div class="message-content"><p>${text}</p></div>`;

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            ${contentHtml}
        `;
        
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    }


    function showTypingIndicator() {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'message ai-message typing-indicator-container';
        indicatorDiv.id = 'typingIndicator';
        indicatorDiv.innerHTML = `
            <div class="message-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2Z"/><path d="m9 12 2 2 4-4"/></svg>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        messagesContainer.appendChild(indicatorDiv);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.remove();
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function streamResponse(fullText) {
        const messageDiv = appendMessage('ai', '');
        const contentDiv = messageDiv.querySelector('.message-content');

        const parts = fullText.trim().split(/\n\n+/);
        const rawTitle = (parts.shift() || '').trim();
        const titleText = rawTitle.replace(/^TITLE[:\-]?\s*/i, '');  // remove word TITLE:

        contentDiv.innerHTML = '';

        const titleEl = document.createElement('h3');
        titleEl.textContent = titleText;
        contentDiv.appendChild(titleEl);

        const paraInfos = (parts.length ? parts : [''])
            .map(p => p.trim())
            .filter(p => p.length > 0)
            .map(pText => {
                const pEl = document.createElement('p');
                pEl.textContent = '';
                contentDiv.appendChild(pEl);
                return { el: pEl, text: pText };
            });

        if (paraInfos.length === 0) {
            const pEl = document.createElement('p');
            pEl.textContent = '';
            contentDiv.appendChild(pEl);
            paraInfos.push({ el: pEl, text: fullText.trim() });
        }

        let paraIdx = 0;
        let charIdx = 0;

        const interval = setInterval(() => {
            const current = paraInfos[paraIdx];
            if (!current) {
                clearInterval(interval);
                return;
            }

            current.el.textContent = current.text.slice(0, charIdx);
            charIdx++;

            if (charIdx > current.text.length) {
                paraIdx++;
                charIdx = 0;
            }

            scrollToBottom();
        }, 10); // type speed
    }

});
