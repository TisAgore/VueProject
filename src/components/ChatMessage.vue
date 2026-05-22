<template>
  <div class="msg" :class="message.role">
    <!-- Avatar -->
    <div class="msg-avatar" :class="message.role">
      <span v-if="message.role === 'assistant'">{{ role?.emoji }}</span>
      <span v-else>👤</span>
    </div>

    <!-- Content -->
    <div class="msg-content">
      <div class="msg-meta">
        <span class="msg-author">{{ message.role === 'user' ? 'Вы' : role?.name }}</span>
        <span class="msg-time">{{ formatTime(message.ts) }}</span>
        <span v-if="message.tokens" class="msg-tokens">{{ message.tokens }} токенов</span>
      </div>
      <div class="msg-bubble" v-html="rendered" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: Object,
  role: Object,
})

function formatTime(ts) {
  if (!ts) return ''
  return ts.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })
}

/* Light markdown renderer (no external deps) */
function renderMarkdown(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // bold, italic, code
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // headings
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm,  '<h3>$1</h3>')
    // lists
    .replace(/^(\d+)\. (.+)$/gm, '<li class="ol">$2</li>')
    .replace(/^[-•] (.+)$/gm,    '<li>$2</li>')
    // wrap adjacent <li> in <ul>
    .replace(/(<li[^>]*>[\s\S]*?<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    // paragraphs
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^(.+)$/, '<p>$1</p>')
}

const rendered = computed(() => renderMarkdown(props.message.content))
</script>

<style scoped>
.msg { display: flex; gap: 12px; max-width: 800px; }
.msg.user { flex-direction: row-reverse; align-self: flex-end; max-width: 640px; }

/* Avatar */
.msg-avatar {
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 15px;
}
.msg-avatar.assistant {
  background: linear-gradient(135deg, var(--accent), var(--accent-g));
}
.msg-avatar.user {
  background: var(--surface2); border: 1px solid var(--border2);
}

/* Content */
.msg-content { flex: 1; min-width: 0; }
.msg-meta {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 5px; font-size: 11px; color: var(--muted);
}
.msg.user .msg-meta { flex-direction: row-reverse; }
.msg-author { font-weight: 500; }
.msg-tokens {
  padding: 1px 6px; border-radius: 6px;
  background: var(--surface2); border: 1px solid var(--border);
  font-size: 10px;
}

/* Bubble */
.msg-bubble {
  padding: 12px 16px; border-radius: 14px;
  font-size: 14px; line-height: 1.65;
}
.msg.assistant .msg-bubble {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top-left-radius: 4px;
}
.msg.user .msg-bubble {
  background: rgba(124,106,247,0.1);
  border: 1px solid rgba(124,106,247,0.2);
  border-top-right-radius: 4px;
}

/* Markdown styles (deep) */
.msg-bubble :deep(p)      { margin-bottom: 10px; }
.msg-bubble :deep(p:last-child) { margin-bottom: 0; }
.msg-bubble :deep(strong) { color: #a89cf7; font-weight: 600; }
.msg-bubble :deep(em)     { color: var(--accent-g); font-style: normal; font-weight: 500; }
.msg-bubble :deep(code)   {
  background: rgba(255,255,255,0.06);
  padding: 1px 6px; border-radius: 4px;
  font-size: 12.5px; font-family: 'JetBrains Mono', monospace;
}
.msg-bubble :deep(h3),
.msg-bubble :deep(h4) {
  font-family: 'Syne', sans-serif; font-weight: 700;
  font-size: 13.5px; color: #a89cf7;
  margin: 12px 0 6px;
}
.msg-bubble :deep(ul),
.msg-bubble :deep(ol) {
  padding-left: 18px; margin-bottom: 10px;
}
.msg-bubble :deep(li) {
  margin-bottom: 4px;
  list-style: disc;
}
.msg-bubble :deep(li.ol) { list-style: decimal; }
</style>
