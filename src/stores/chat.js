import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/* ── Role definitions ── */
export const ROLES = [
  {
    id: 'founder',
    name: 'Помощник основателя',
    emoji: '🚀',
    color: '#7c6af7',
    tag: 'Для фаундеров',
    desc: 'Помогает оценить идею, найти точки роста и подготовиться к питчу',
  },
  {
    id: 'investor',
    name: 'Оценщик инвестора',
    emoji: '💼',
    color: '#5eead4',
    tag: 'Для инвесторов',
    desc: 'Анализирует стартап с позиции VC: рынок, трекшн, unit economics',
  },
  {
    id: 'mentor',
    name: 'Ментор акселератора',
    emoji: '🎓',
    color: '#fbbf24',
    tag: 'Для команд',
    desc: 'Задаёт правильные вопросы и готовит команду к Demo Day',
  },
  {
    id: 'critic',
    name: 'Жёсткий критик',
    emoji: '🔍',
    color: '#fb7185',
    tag: 'Для проверки',
    desc: 'Находит все слабые места, риски и типичные ошибки без прикрас',
  },
]

/* ── Checklist items ── */
const CHECKLIST_ITEMS = [
  'Проблема описана чётко',
  'Целевая аудитория определена',
  'Уникальность решения',
  'Конкуренты проанализированы',
  'Бизнес-модель понятна',
  'Финансовая модель готова',
  'Команда сформирована',
  'MVP готов или описан',
]

/* ── Quick prompts ── */
export const QUICK_PROMPTS = [
  { icon: '▶', label: 'Начать аудит с нуля',     text: 'Помоги провести полный аудит моего стартапа. С чего начать?' },
  { icon: '💡', label: 'Оценить идею',             text: 'Оцени мою идею: ' },
  { icon: '⚠️', label: 'Анализ рисков',            text: 'Какие риски есть у моего стартапа?' },
  { icon: '🎯', label: 'Подготовка к питчу',       text: 'Как подготовиться к питчу перед инвесторами?' },
  { icon: '🔎', label: 'Анализ конкурентов',       text: 'Помоги проанализировать конкурентов в моей нише' },
]

/* ── Store ── */
export const useChatStore = defineStore('chat', () => {
  // state
  const activeRoleId  = ref('founder')
  const messages      = ref([])          // { id, role: 'user'|'assistant', content, ts }
  const isLoading     = ref(false)
  const error         = ref(null)
  const checklist     = ref(CHECKLIST_ITEMS.map(label => ({ label, done: false })))
  const inputText     = ref('')          // shared bus: sidebar → chat input

  // getters
  const activeRole    = computed(() => ROLES.find(r => r.id === activeRoleId.value))
  const progress      = computed(() => {
    const done = checklist.value.filter(i => i.done).length
    return Math.round((done / checklist.value.length) * 100)
  })
  const hasMessages   = computed(() => messages.value.length > 0)

  // actions
  function setRole(id) {
    if (activeRoleId.value === id) return
    activeRoleId.value = id
    clearChat()
  }

  function clearChat() {
    messages.value = []
    error.value    = null
  }

  function toggleCheck(idx) {
    checklist.value[idx].done = !checklist.value[idx].done
  }

  async function sendMessage(text) {
    if (!text.trim() || isLoading.value) return
    error.value = null

    // Add user message
    messages.value.push({
      id:      Date.now(),
      role:    'user',
      content: text.trim(),
      ts:      new Date(),
    })

    isLoading.value = true

    try {
      const res = await fetch('/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          role:     activeRoleId.value,
          messages: messages.value.map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `HTTP ${res.status}`)
      }

      const data = await res.json()
      messages.value.push({
        id:      Date.now() + 1,
        role:    'assistant',
        content: data.reply,
        model:   data.model,
        tokens:  data.total_tokens,
        ts:      new Date(),
      })
    } catch (e) {
      error.value = e.message || 'Сервер недоступен'
      // Remove the user message so they can retry
      messages.value.pop()
    } finally {
      isLoading.value = false
    }
  }

  function exportChat() {
    if (!messages.value.length) return
    const role = activeRole.value
    let out = `AuditMate — Экспорт чата\nРоль: ${role.name}\nДата: ${new Date().toLocaleString('ru')}\n${'─'.repeat(48)}\n\n`
    messages.value.forEach(m => {
      out += `[${m.role === 'user' ? 'ВЫ' : 'AUDITMATE'}] ${m.ts?.toLocaleTimeString('ru') ?? ''}\n${m.content}\n\n`
    })
    const blob = new Blob([out], { type: 'text/plain;charset=utf-8' })
    const a    = document.createElement('a')
    a.href     = URL.createObjectURL(blob)
    a.download = `auditmate-${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return {
    activeRoleId, messages, isLoading, error, checklist, inputText,
    activeRole, progress, hasMessages,
    setRole, clearChat, toggleCheck, sendMessage, exportChat,
  }
})
