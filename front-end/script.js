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

    function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // Add User Message
        appendMessage('user', text);
        userInput.value = '';
        userInput.style.height = 'auto';

        // Simulate AI Response
        showTypingIndicator();
        
        // Mock API delay
        setTimeout(() => {
            removeTypingIndicator();
            const response = generateMockResponse(text);
            streamResponse(response);
        }, 1500);
    }

    function appendMessage(role, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const avatar = role === 'ai' 
            ? '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2Z"/><path d="m9 12 2 2 4-4"/></svg>'
            : '<div style="width: 24px; height: 24px; background: #555; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px;">U</div>';

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content"><p>${text}</p></div>
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
        const contentP = messageDiv.querySelector('.message-content p');
        let index = 0;

        const interval = setInterval(() => {
            if (index < fullText.length) {
                contentP.textContent += fullText.charAt(index);
                index++;
                scrollToBottom();
            } else {
                clearInterval(interval);
            }
        }, 20); // Typing speed
    }

    function generateMockResponse(input) {
        const responses = [
            "That's an interesting perspective! Tell me more.",
            "I can certainly help you with that. Here's what I found...",
            "Could you clarify what you mean by that?",
            "I'm just a mock AI, but I think your idea is great!",
            "Based on my training data, the answer is 42.",
            "Let's break this down step by step.",
            "I'm listening. Go on."
        ];
        return responses[Math.floor(Math.random() * responses.length)];
    }
});
