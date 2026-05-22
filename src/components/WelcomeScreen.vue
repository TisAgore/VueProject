<template>
  <div class="welcome">
    <div class="welcome-glow" />
    <div class="welcome-icon">{{ store.activeRole?.emoji }}</div>
    <h1 class="welcome-title syne">
      Привет! Я <span class="gradient-text">AuditMate</span>
    </h1>
    <p class="welcome-desc">
      Выберите роль ИИ слева и опишите ваш стартап — помогу провести аудит за 20 минут.
    </p>
    <div class="welcome-role-badge" :style="{ borderColor: store.activeRole?.color + '44', color: store.activeRole?.color }">
      {{ store.activeRole?.emoji }} {{ store.activeRole?.name }}
    </div>
    <p class="welcome-tip">
      <strong>Совет:</strong> опишите идею одним абзацем — что за продукт, для кого, в чём уникальность.
    </p>
  </div>
</template>

<script setup>
import { useChatStore } from '@/stores/chat'
const store = useChatStore()
defineEmits(['quick'])
</script>

<style scoped>
.welcome {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center; padding: 48px 32px;
  gap: 14px; position: relative;
}
.welcome-glow {
  position: absolute;
  width: 400px; height: 300px;
  background: radial-gradient(ellipse, rgba(124,106,247,0.12) 0%, transparent 70%);
  top: 50%; left: 50%; transform: translate(-50%, -60%);
  pointer-events: none;
}
.welcome-icon {
  font-size: 56px; filter: drop-shadow(0 0 24px rgba(124,106,247,0.4));
  animation: float 4s ease-in-out infinite;
}
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }

.welcome-title { font-size: 30px; font-weight: 800; line-height: 1.1; margin-top: 4px; }

.welcome-desc {
  color: var(--muted2); font-size: 14px; max-width: 420px; line-height: 1.65;
}
.welcome-role-badge {
  padding: 6px 16px; border-radius: 20px; border: 1px solid;
  font-size: 12.5px; font-weight: 500;
  background: rgba(255,255,255,0.03);
}
.welcome-tip {
  margin-top: 8px;
  padding: 12px 20px; border-radius: 12px;
  border: 1px solid var(--border); background: var(--surface);
  font-size: 12.5px; color: var(--muted2); max-width: 380px; line-height: 1.6;
}
.welcome-tip strong { color: var(--text); }
</style>
