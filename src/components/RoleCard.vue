<template>
  <button
    class="role-card"
    :class="{ active }"
    :style="active ? `--rc: ${role.color}` : ''"
    @click="$emit('click')"
  >
    <span class="r-emoji">{{ role.emoji }}</span>
    <div class="r-body">
      <span class="r-name syne">{{ role.name }}</span>
      <span class="r-desc">{{ role.desc }}</span>
    </div>
    <span class="r-tag">{{ role.tag }}</span>
  </button>
</template>

<script setup>
defineProps({ role: Object, active: Boolean })
defineEmits(['click'])
</script>

<style scoped>
.role-card {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px; border-radius: var(--r);
  border: 1.5px solid var(--border);
  background: transparent; width: 100%;
  cursor: pointer; text-align: left;
  transition: all 0.2s; position: relative;
  overflow: hidden;
}
.role-card:hover { border-color: var(--border2); transform: translateY(-1px); }
.role-card.active {
  border-color: var(--rc, var(--accent));
  background: color-mix(in srgb, var(--rc, var(--accent)) 10%, transparent);
}

.r-emoji { font-size: 20px; flex-shrink: 0; line-height: 1; margin-top: 1px; }

.r-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.r-name { font-size: 12.5px; font-weight: 700; color: var(--text); line-height: 1.2; }
.r-desc { font-size: 11px; color: var(--muted); line-height: 1.45; }

.r-tag {
  flex-shrink: 0; align-self: flex-start;
  font-size: 10px; padding: 2px 7px; border-radius: 8px;
  background: var(--surface2); border: 1px solid var(--border2);
  color: var(--muted); white-space: nowrap;
}
.role-card.active .r-tag {
  background: color-mix(in srgb, var(--rc, var(--accent)) 15%, transparent);
  border-color: color-mix(in srgb, var(--rc, var(--accent)) 40%, transparent);
  color: var(--text);
}
</style>
