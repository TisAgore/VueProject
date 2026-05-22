<template>
  <header class="header">
    <div class="logo">
      <div class="logo-mark">
        <span>AM</span>
        <div class="logo-glow" />
      </div>
      <div class="logo-text">
        <span class="logo-name syne">AuditMate</span>
        <span class="logo-sub">Умный аудит стартапа</span>
      </div>
    </div>

    <div class="header-center">
      <div class="model-badge">
        <span class="model-dot" />
        <span>AI активен</span>
      </div>
    </div>

    <nav class="header-nav">
      <button class="nav-btn" :class="{ active: tab === 'chat' }" @click="tab = 'chat'">
        💬 Чат
      </button>
      <button class="nav-btn" :class="{ active: tab === 'about' }" @click="tab = 'about'">
        📋 О сервисе
      </button>
    </nav>
  </header>
</template>

<script setup>
import { ref } from 'vue'
const tab = ref('chat')
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}

/* Logo */
.logo { display: flex; align-items: center; gap: 12px; }
.logo-mark {
  position: relative;
  width: 36px; height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--accent), var(--accent-g));
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.logo-mark span {
  font-family: 'Syne', sans-serif;
  font-weight: 800; font-size: 13px;
  color: #09090f; position: relative; z-index: 1;
}
.logo-glow {
  position: absolute; inset: -4px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--accent), var(--accent-g));
  opacity: 0.25;
  filter: blur(8px);
  z-index: 0;
}
.logo-text { display: flex; flex-direction: column; gap: 0; }
.logo-name  { font-weight: 700; font-size: 16px; letter-spacing: -0.3px; line-height: 1.2; }
.logo-sub   { font-size: 10px; color: var(--muted); letter-spacing: 0.4px; line-height: 1; }

/* Status */
.model-badge {
  display: flex; align-items: center; gap: 7px;
  padding: 5px 14px; border-radius: 20px;
  border: 1px solid rgba(124,106,247,0.25);
  background: rgba(124,106,247,0.08);
  font-size: 12px; color: #a89cf7;
}
.model-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(1.4)} }

/* Nav */
.header-nav { display: flex; gap: 4px; }
.nav-btn {
  padding: 6px 14px; border-radius: 8px;
  border: 1px solid transparent;
  background: transparent; color: var(--muted);
  font-size: 12px; font-family: 'DM Sans', sans-serif;
  cursor: pointer; transition: all 0.15s;
}
.nav-btn:hover { color: var(--text); border-color: var(--border2); }
.nav-btn.active {
  color: var(--text); background: var(--surface2);
  border-color: var(--border2);
}
</style>
