<template>
  <div class="chat-view">

    <!-- Context bar -->
    <div class="ctx-bar">
      <div class="ctx-role">
        <div class="ctx-dot" :style="{ background: store.activeRole?.color }" />
        <span>{{ store.activeRole?.name }}</span>
      </div>
      <div class="ctx-actions">
        <button class="ctx-btn" @click="store.clearChat()">Очистить</button>
        <button class="ctx-btn" @click="store.exportChat()">Экспорт</button>
      </div>
    </div>

    <!-- Messages area -->
    <div class="messages" ref="messagesEl">

      <!-- Welcome screen -->
      <WelcomeScreen v-if="!store.hasMessages" />

      <!-- Message list -->
      <template v-else>
        <ChatMessage
          v-for="msg in store.messages"
          :key="msg.id"
          :message="msg"
          :role="store.activeRole"
        />

        <!-- Typing indicator -->
        <div v-if="store.isLoading" class="msg assistant">
          <div class="msg-avatar">{{ store.activeRole?.emoji }}</div>
          <div class="msg-content">
            <div class="msg-meta">{{ store.activeRole?.name }}</div>
            <div class="msg-bubble typing">
              <span /><span /><span />
            </div>
          </div>
        </div>

        <!-- Error -->
        <div v-if="store.error" class="error-row">
          <div class="error-card">
            <span>⚠️</span>
            <span>{{ store.error }}</span>
            <button @click="store.error = null">✕</button>
          </div>
        </div>
      </template>

    </div>

    <!-- Input -->
    <ChatInput @send="onSend" />

  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import WelcomeScreen from '@/components/WelcomeScreen.vue'
import ChatMessage   from '@/components/ChatMessage.vue'
import ChatInput     from '@/components/ChatInput.vue'

const store      = useChatStore()
const messagesEl = ref(null)

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.isLoading,        scrollToBottom)

async function onSend(text) {
  await store.sendMessage(text)
}
</script>

<style scoped>
.chat-view {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; min-width: 0;
}

/* Context bar */
.ctx-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}
.ctx-role { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 500; }
.ctx-dot  { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ctx-actions { display: flex; gap: 6px; }
.ctx-btn {
  padding: 4px 12px; border-radius: 8px; font-size: 11.5px;
  border: 1px solid var(--border2); background: var(--surface2);
  color: var(--muted); cursor: pointer; transition: all 0.15s;
  font-family: 'DM Sans', sans-serif;
}
.ctx-btn:hover { color: var(--text); border-color: #38394f; }

/* Messages */
.messages {
  flex: 1; overflow-y: auto; padding: 28px 32px;
  display: flex; flex-direction: column; gap: 22px;
  scroll-behavior: smooth;
}
.messages::-webkit-scrollbar {
    width: 0.4em;
}
.messages::-webkit-scrollbar-track {
    -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.3);
}
.messages::-webkit-scrollbar-thumb {
  background-color: var(--rc, var(--accent));
  outline: 1px solid var(--rc, var(--accent));
}

/* Typing bubble */
.msg { display: flex; gap: 12px; }
/* .msg.assistant {} */
.msg-avatar {
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--accent), var(--accent-g));
  display: flex; align-items: center; justify-content: center; font-size: 15px;
}
.msg-content { flex: 1; min-width: 0; }
.msg-meta { font-size: 11px; color: var(--muted); margin-bottom: 5px; }
.msg-bubble.typing {
  display: inline-flex; gap: 5px; align-items: center;
  padding: 12px 16px; border-radius: 14px; border-top-left-radius: 4px;
  background: var(--surface); border: 1px solid var(--border);
}
.msg-bubble.typing span {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--muted); display: block;
  animation: bounce 1.1s infinite ease-in-out;
}
.msg-bubble.typing span:nth-child(2) { animation-delay: .15s; }
.msg-bubble.typing span:nth-child(3) { animation-delay: .30s; }
@keyframes bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-7px)} }

/* Error */
.error-row { display: flex; justify-content: center; }
.error-card {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; border-radius: 10px;
  background: rgba(251,113,133,0.08); border: 1px solid rgba(251,113,133,0.25);
  color: var(--danger); font-size: 13px; max-width: 500px;
}
.error-card button {
  margin-left: auto; background: none; border: none;
  color: var(--danger); cursor: pointer; font-size: 14px; padding: 0 4px;
}
</style>
