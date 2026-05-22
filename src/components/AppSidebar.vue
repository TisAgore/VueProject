<template>
  <aside class="sidebar">

    <!-- Role selector -->
    <section class="section">
      <h3 class="section-title">Роль ИИ</h3>
      <div class="roles">
        <RoleCard
          v-for="role in ROLES"
          :key="role.id"
          :role="role"
          :active="store.activeRoleId === role.id"
          @click="store.setRole(role.id)"
        />
      </div>
    </section>

    <!-- Checklist -->
    <section class="section">
      <h3 class="section-title">Чек-лист аудита</h3>
      <ul class="checklist">
        <li
          v-for="(item, i) in store.checklist"
          :key="i"
          class="check-item"
          :class="{ done: item.done }"
          @click="store.toggleCheck(i)"
        >
          <div class="check-box">
            <svg v-if="item.done" viewBox="0 0 12 12" fill="none">
              <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <span>{{ item.label }}</span>
        </li>
      </ul>
    </section>

    <!-- Progress -->
    <section class="section">
      <div class="progress-header">
        <span class="section-title" style="margin-bottom:0">Прогресс</span>
        <span class="progress-val syne">{{ store.progress }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: store.progress + '%' }" />
      </div>
    </section>

    <!-- Quick prompts -->
    <section class="section">
      <h3 class="section-title">Быстрый старт</h3>
      <div class="quick-list">
        <button
          v-for="p in QUICK_PROMPTS"
          :key="p.label"
          class="quick-btn"
          @click="store.inputText = p.text"
        >
          <span class="q-icon">{{ p.icon }}</span>
          {{ p.label }}
        </button>
      </div>
    </section>

  </aside>
</template>

<script setup>
import { useChatStore, ROLES, QUICK_PROMPTS } from '@/stores/chat'
import RoleCard from '@/components/RoleCard.vue'

const store = useChatStore()
</script>

<style scoped>
.sidebar {
  width: 100%; min-width: 220px; max-width: 320px;
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  overflow-y: scroll;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 8px 0px 20px;
}

.sidebar::-webkit-scrollbar {
    width: 0.2em;
}

.sidebar::-webkit-scrollbar-track {
    -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.3);
}

.sidebar::-webkit-scrollbar-thumb {
  background-color: var(--rc, var(--accent));
  outline: 1px solid var(--rc, var(--accent));
}

.section {
  padding: 16px 16px 0;
}
.section + .section { padding-top: 20px; }

.section-title {
  font-size: 10px; font-weight: 600;
  letter-spacing: 1.2px; text-transform: uppercase;
  color: var(--muted); margin-bottom: 10px;
  display: block;
}

/* Roles */
.roles { display: flex; flex-direction: column; gap: 6px; }

/* Checklist */
.checklist { list-style: none; display: flex; flex-direction: column; gap: 5px; }
.check-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 10px;
  background: var(--surface2); border: 1px solid var(--border);
  cursor: pointer; transition: all 0.15s;
  font-size: 12.5px; color: var(--muted2);
  user-select: none;
}
.check-item:hover { border-color: var(--border2); color: var(--text); }
.check-item.done { color: var(--muted); }
.check-item.done span { text-decoration: line-through; }
.check-box {
  width: 18px; height: 18px; border-radius: 5px; flex-shrink: 0;
  border: 1.5px solid var(--border2);
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; color: var(--bg);
}
.check-item.done .check-box {
  background: var(--accent-g); border-color: var(--accent-g);
}
.check-box svg { width: 12px; height: 12px; }

/* Progress */
.progress-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px;
}
.progress-val { font-size: 18px; font-weight: 800; color: var(--accent); }
.progress-track {
  height: 4px; background: var(--border2);
  border-radius: 2px; overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-g));
  border-radius: 2px;
  transition: width 0.5s cubic-bezier(.4,0,.2,1);
}

/* Quick */
.quick-list { display: flex; flex-direction: column; gap: 5px; }
.quick-btn {
  display: flex; align-items: center; gap: 9px;
  padding: 9px 12px; border-radius: 10px;
  background: var(--surface2); border: 1px solid var(--border);
  color: var(--muted2); font-size: 12.5px;
  font-family: 'DM Sans', sans-serif;
  cursor: pointer; transition: all 0.15s; text-align: left;
  width: 100%;
}
.quick-btn:hover {
  border-color: var(--border2); color: var(--text);
  transform: translateX(3px);
}
.q-icon { font-size: 14px; flex-shrink: 0; }
</style>
