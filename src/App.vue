<script setup>
import { computed, ref, watch } from 'vue'
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleCheck,
  CircleX,
  Download,
  Flame,
  LayoutDashboard,
  ListChecks,
  Moon,
  Play,
  RotateCcw,
  Settings2,
  Sparkles,
  Sun,
  Target,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
import wordBank from './data/wordBank.json'

const STORAGE_KEY = 'cet6-wordlab-wrong-answers-v1'
const THEME_KEY = 'cet6-wordlab-theme-v1'

const navItems = [
  { id: 'practice', label: '练习工作台', icon: LayoutDashboard },
  { id: 'mistakes', label: '错题档案', icon: AlertTriangle },
]

const activeView = ref('practice')
const selectedList = ref(1)
const mode = ref('choice')
const questionCount = ref(10)
const session = ref(null)
const typedAnswer = ref('')
const wrongRecords = ref(loadWrongRecords())
const toast = ref('')
const fileInput = ref(null)
const theme = ref(loadTheme())
let toastTimer

if (typeof document !== 'undefined') document.documentElement.dataset.theme = theme.value

const lists = computed(() => {
  return Array.from({ length: 20 }, (_, index) => {
    const number = index + 1
    const words = wordBank.filter((item) => item.list === number)
    return { number, words, progress: words.filter((item) => wrongRecords.value[recordKey(item)]).length }
  })
})

const activeList = computed(() => lists.value.find((item) => item.number === selectedList.value) || lists.value[0])
const activeListWords = computed(() => activeList.value?.words || [])
const currentWord = computed(() => session.value?.queue?.[session.value.index] || null)
const currentOptions = computed(() => session.value?.options || [])
const wrongEntries = computed(() => Object.values(wrongRecords.value).sort((a, b) => {
  if (b.count !== a.count) return b.count - a.count
  return a.word.localeCompare(b.word)
}))
const totalMistakes = computed(() => wrongEntries.value.reduce((sum, item) => sum + item.count, 0))
const sessionPercent = computed(() => {
  if (!session.value?.queue?.length) return 0
  return Math.round(((session.value.index + (session.value.completed ? 1 : 0)) / session.value.queue.length) * 100)
})
const hintPattern = computed(() => {
  if (!currentWord.value) return ''
  const word = currentWord.value.word
  return word.split('').map((letter, index) => {
    const visible = index === 0 || index === word.length - 1 || index % 3 === 0
    return visible ? letter : '_'
  }).join(' ')
})
const accuracy = computed(() => {
  if (!session.value?.answered) return 0
  return Math.round((session.value.score / session.value.answered) * 100)
})

watch(selectedList, () => {
  questionCount.value = Math.min(Math.max(Number(questionCount.value) || 10, 1), activeListWords.value.length)
  session.value = null
  typedAnswer.value = ''
})

watch(questionCount, (value) => {
  const capped = Math.min(Math.max(Number(value) || 1, 1), activeListWords.value.length)
  if (capped !== value) questionCount.value = capped
})

watch(wrongRecords, (value) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
}, { deep: true })

watch(theme, (value) => {
  document.documentElement.dataset.theme = value
  localStorage.setItem(THEME_KEY, value)
})

function loadTheme() {
  return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light'
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

function loadWrongRecords() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') || {}
  } catch {
    return {}
  }
}

function recordKey(item) {
  return `${item.list}:${item.word.toLowerCase()}`
}

function shuffle(items) {
  return [...items].sort(() => Math.random() - 0.5)
}

function makeOptions(word) {
  const alternatives = shuffle(wordBank.filter((item) => item.id !== word.id && item.meaning !== word.meaning))
    .slice(0, 3)
    .map((item) => item.meaning)
  return shuffle([word.meaning, ...alternatives])
}

function startSession() {
  const count = Math.min(Math.max(Number(questionCount.value) || 1, 1), activeListWords.value.length)
  questionCount.value = count
  const queue = shuffle(activeListWords.value).slice(0, count)
  session.value = {
    queue,
    index: 0,
    score: 0,
    answered: 0,
    streak: 0,
    selectedAnswer: null,
    feedback: null,
    options: makeOptions(queue[0]),
    completed: false,
  }
  typedAnswer.value = ''
}

function evaluate(isCorrect, answer) {
  if (!session.value || session.value.feedback) return
  session.value.selectedAnswer = answer
  session.value.feedback = isCorrect ? 'correct' : 'incorrect'
  session.value.answered += 1
  if (isCorrect) {
    session.value.score += 1
    session.value.streak += 1
  } else {
    session.value.streak = 0
    saveMistake(currentWord.value)
  }
}

function chooseAnswer(answer) {
  evaluate(answer === currentWord.value.meaning, answer)
}

function submitFill() {
  const normalized = typedAnswer.value.trim().toLowerCase().replace(/[^a-z]/g, '')
  evaluate(normalized === currentWord.value.word.toLowerCase(), typedAnswer.value.trim())
}

function nextQuestion() {
  if (!session.value) return
  if (session.value.index >= session.value.queue.length - 1) {
    session.value.completed = true
    return
  }
  session.value.index += 1
  session.value.options = makeOptions(session.value.queue[session.value.index])
  session.value.selectedAnswer = null
  session.value.feedback = null
  typedAnswer.value = ''
}

function saveMistake(word) {
  if (!word) return
  const key = recordKey(word)
  const existing = wrongRecords.value[key]
  wrongRecords.value = {
    ...wrongRecords.value,
    [key]: {
      word: word.word,
      meaning: word.meaning,
      list: word.list,
      count: (existing?.count || 0) + 1,
      lastSeen: new Date().toISOString(),
    },
  }
}

function chooseList(number) {
  selectedList.value = number
  activeView.value = 'practice'
}

function showToast(message) {
  toast.value = message
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toast.value = '' }, 2800)
}

function exportMistakes() {
  const payload = {
    format: 'cet6-wordlab-wrong-answers',
    version: 1,
    exportedAt: new Date().toISOString(),
    records: wrongEntries.value,
  }
  const safeJson = JSON.stringify(payload, null, 2).replace(/</g, '\\u003c')
  const closingScript = '<' + '/script>'
  const rows = wrongEntries.value.map((item) => `
    <tr><td>${escapeHtml(item.word)}</td><td>${escapeHtml(item.meaning)}</td><td>List ${item.list}</td><td>${item.count}</td></tr>
  `).join('')
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><title>Wordlab 错题档案</title><style>body{font-family:Arial,"Microsoft YaHei",sans-serif;max-width:900px;margin:40px auto;padding:0 20px;color:#25231f}h1{font-size:28px}table{width:100%;border-collapse:collapse;margin-top:24px}th,td{text-align:left;padding:12px;border-bottom:1px solid #ddd}th{background:#f1ede6}</style></head><body><h1>Wordlab 错题档案</h1><p>导出时间：${new Date().toLocaleString('zh-CN')}</p><table><thead><tr><th>单词</th><th>释义</th><th>List</th><th>错误次数</th></tr></thead><tbody>${rows || '<tr><td colspan="4">暂无错题</td></tr>'}</tbody></table><script type="application/json" id="wordlab-data">${safeJson}${closingScript}</body></html>`
  downloadFile('wordlab-wrong-answers.html', html, 'text/html;charset=utf-8')
  showToast('错题档案已导出')
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]))
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function openImport() {
  fileInput.value?.click()
}

async function importMistakes(event) {
  const file = event.target.files?.[0]
  if (!file) return
  try {
    const html = await file.text()
    const match = html.match(/<script[^>]+id=["']wordlab-data["'][^>]*>([\s\S]*?)<\/script>/i)
    if (!match) throw new Error('missing data')
    const payload = JSON.parse(match[1])
    const imported = Array.isArray(payload.records) ? payload.records : Object.values(payload.records || {})
    const merged = { ...wrongRecords.value }
    imported.forEach((item) => {
      if (!item?.word) return
      const key = `${item.list || 1}:${item.word.toLowerCase()}`
      const current = merged[key]
      merged[key] = {
        word: item.word,
        meaning: item.meaning || '暂无释义',
        list: Number(item.list) || 1,
        count: Math.max(Number(item.count) || 1, current?.count || 0),
        lastSeen: item.lastSeen || new Date().toISOString(),
      }
    })
    wrongRecords.value = merged
    showToast(`已导入 ${imported.length} 条错题记录`)
  } catch {
    showToast('导入失败，请选择 Wordlab 导出的 HTML')
  } finally {
    event.target.value = ''
  }
}

function clearMistakes() {
  if (!wrongEntries.value.length) return
  wrongRecords.value = {}
  showToast('错题记录已清空')
}

function formatDate(value) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(new Date(value))
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-lockup">
        <div class="brand-mark"><BookOpen :size="19" stroke-width="2.2" /></div>
        <div>
          <strong>WORDLAB</strong>
          <span>CET-6 / 2024</span>
        </div>
      </div>

      <div class="nav-label">学习空间</div>
      <nav class="primary-nav" aria-label="主导航">
        <button v-for="item in navItems" :key="item.id" class="nav-item" :class="{ active: activeView === item.id }" @click="activeView = item.id">
          <component :is="item.icon" :size="17" />
          <span>{{ item.label }}</span>
          <span v-if="item.id === 'mistakes' && wrongEntries.length" class="nav-count">{{ wrongEntries.length }}</span>
        </button>
      </nav>

      <div class="sidebar-note">
        <Sparkles :size="16" />
        <p>每天 10 分钟，让遗忘慢一点。</p>
      </div>
      <div class="sidebar-footer"><span class="status-dot"></span> 离线可用 · 数据在本机</div>
    </aside>

    <main class="app-main">
      <header class="topbar">
        <div class="mobile-brand"><span class="mobile-mark">W</span><strong>WORDLAB</strong></div>
        <div class="breadcrumb"><span>六级词汇</span><ChevronRight :size="14" /><strong>{{ activeView === 'practice' ? '练习工作台' : '错题档案' }}</strong></div>
        <div class="topbar-actions">
          <button class="icon-button" title="重新开始当前练习" aria-label="重新开始当前练习" @click="startSession"><RotateCcw :size="17" /></button>
          <button class="icon-button theme-toggle" :title="theme === 'dark' ? '切换到亮色主题' : '切换到暗色主题'" :aria-label="theme === 'dark' ? '切换到亮色主题' : '切换到暗色主题'" @click="toggleTheme"><Sun v-if="theme === 'dark'" :size="17" /><Moon v-else :size="17" /></button>
          <div class="profile-chip"><span class="profile-avatar">W</span><span class="profile-name">Word learner</span></div>
        </div>
      </header>

      <section v-if="activeView === 'practice'" class="page-content">
        <div class="page-intro">
          <div>
            <div class="eyebrow"><span class="eyebrow-line"></span> DAILY RECALL / CET-6</div>
            <h1>把单词，变成你的语感。</h1>
            <p class="intro-copy">从一个 List 开始，用几分钟把陌生感变成熟悉。</p>
          </div>
          <div class="date-stamp"><span>今日练习</span><strong>{{ new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric' }).format(new Date()) }}</strong></div>
        </div>

        <div class="stat-strip">
          <div class="stat-item"><span class="stat-icon coral"><Target :size="16" /></span><div><small>词库总量</small><strong>{{ wordBank.length.toLocaleString() }}</strong><em>20 个 List</em></div></div>
          <div class="stat-item"><span class="stat-icon lime"><Flame :size="16" /></span><div><small>累计错题</small><strong>{{ totalMistakes }}</strong><em>{{ wrongEntries.length ? '持续复习中' : '今天还没有记录' }}</em></div></div>
          <div class="stat-item"><span class="stat-icon ink"><ListChecks :size="16" /></span><div><small>当前选择</small><strong>List {{ selectedList }}</strong><em>{{ activeListWords.length }} 个词</em></div></div>
        </div>

        <div class="workspace-grid">
          <section class="practice-card">
            <div class="card-topline">
              <div><span class="section-kicker">PRACTICE LAB</span><h2>{{ session?.completed ? '这一轮完成了。' : session ? '保持这个节奏。' : '准备好开始了吗？' }}</h2></div>
              <div class="mode-switch" role="tablist" aria-label="练习模式">
                <button :class="{ selected: mode === 'choice' }" :disabled="!!session && !session.completed" @click="mode = 'choice'"><ListChecks :size="14" /> 选择题</button>
                <button :class="{ selected: mode === 'fill' }" :disabled="!!session && !session.completed" @click="mode = 'fill'"><Settings2 :size="14" /> 填空题</button>
              </div>
            </div>

            <div v-if="!session" class="session-ready">
              <div class="ready-orbit"><span></span><span></span><span></span><BookOpen :size="30" /></div>
              <p class="ready-label">LIST {{ String(selectedList).padStart(2, '0') }} / {{ activeListWords.length }} WORDS</p>
              <h3>今天，先记住 {{ questionCount }} 个。</h3>
              <p>题目会从当前 List 中随机抽取，答错的单词会自动进入错题档案。</p>
              <button class="primary-button" @click="startSession"><Play :size="17" fill="currentColor" /> 开始练习 <ArrowRight :size="16" /></button>
            </div>

            <div v-else-if="session.completed" class="session-complete">
              <div class="complete-mark"><Check :size="29" /></div>
              <span class="section-kicker">SESSION COMPLETE</span>
              <h3>{{ session.score }} / {{ session.queue.length }}，完成得很漂亮。</h3>
              <p>本轮正确率 {{ accuracy }}%，错题已经同步到你的档案。</p>
              <div class="result-metrics"><span><strong>{{ session.score }}</strong><small>答对</small></span><span><strong>{{ session.queue.length - session.score }}</strong><small>待复习</small></span><span><strong>{{ session.streak }}</strong><small>连对峰值</small></span></div>
              <button class="primary-button" @click="startSession"><RotateCcw :size="16" /> 再来一轮</button>
            </div>

            <div v-else class="question-area">
              <div class="question-header"><div><span class="question-index">{{ String(session.index + 1).padStart(2, '0') }} <i>/</i> {{ String(session.queue.length).padStart(2, '0') }}</span><span class="question-list">LIST {{ selectedList }}</span></div><span class="streak"><Flame :size="14" /> {{ session.streak }} 连对</span></div>
              <div class="progress-track"><span :style="{ width: `${sessionPercent}%` }"></span></div>

              <div v-if="mode === 'choice'" class="prompt-block"><span class="prompt-label">选择最贴切的中文释义</span><h3 class="word-prompt">{{ currentWord.word }}</h3><span class="word-syllable">WORD · {{ currentWord.word.length }} LETTERS</span></div>
              <div v-else class="prompt-block"><span class="prompt-label">根据释义，拼出对应的单词</span><h3 class="meaning-prompt">{{ currentWord.meaning }}</h3><div class="hint-line"><span>字母提示</span><strong>{{ hintPattern }}</strong></div></div>

              <div v-if="mode === 'choice'" class="answer-grid">
                <button v-for="(option, index) in currentOptions" :key="option" class="answer-option" :class="{ picked: session.selectedAnswer === option, correct: session.feedback && option === currentWord.meaning, wrong: session.feedback === 'incorrect' && session.selectedAnswer === option }" :disabled="!!session.feedback" @click="chooseAnswer(option)"><span class="option-letter">{{ ['A', 'B', 'C', 'D'][index] }}</span><span>{{ option }}</span><Check v-if="session.feedback && option === currentWord.meaning" :size="17" /><X v-else-if="session.feedback === 'incorrect' && session.selectedAnswer === option" :size="17" /></button>
              </div>
              <form v-else class="fill-form" @submit.prevent="submitFill"><input v-model="typedAnswer" :disabled="!!session.feedback" autofocus autocomplete="off" placeholder="输入单词" /><button class="small-action" type="submit" :disabled="!!session.feedback || !typedAnswer.trim()" aria-label="提交答案" title="提交答案"><ArrowRight :size="18" /></button></form>

              <div v-if="session.feedback" class="feedback-row" :class="session.feedback"><div class="feedback-symbol"><Check v-if="session.feedback === 'correct'" :size="17" /><X v-else :size="17" /></div><div><strong>{{ session.feedback === 'correct' ? '答对了，继续保持。' : `答案是 ${currentWord.word}` }}</strong><span>{{ currentWord.meaning }}</span></div><button class="next-button" @click="nextQuestion">{{ session.index === session.queue.length - 1 ? '查看结果' : '下一题' }} <ArrowRight :size="15" /></button></div>
            </div>
          </section>

          <aside class="right-rail">
            <section class="list-panel">
              <div class="panel-heading"><div><span class="section-kicker">WORD BANK</span><h2>选择一个 List</h2></div><span class="panel-count">20</span></div>
              <div class="list-grid"><button v-for="list in lists" :key="list.number" class="list-tile" :class="{ active: selectedList === list.number }" @click="chooseList(list.number)"><span>List {{ String(list.number).padStart(2, '0') }}</span><small>{{ list.words.length }}</small><i :style="{ '--progress': `${Math.min(list.progress * 12, 100)}%` }"></i></button></div>
              <div class="control-row"><label for="question-count">本轮题数</label><div class="number-control"><button @click="questionCount = Math.max(1, questionCount - 1)" aria-label="减少题数">−</button><input id="question-count" v-model.number="questionCount" type="number" min="1" :max="activeListWords.length" /><button @click="questionCount = Math.min(activeListWords.length, questionCount + 1)" aria-label="增加题数">+</button></div></div>
              <p class="limit-note">上限 {{ activeListWords.length }} 题 · 已按当前 List 限制</p>
            </section>
            <section class="quote-panel"><div class="quote-mark">“</div><p>先把今天的一小块，变成明天的底气。</p><span>WORDLAB NOTE / 01</span></section>
          </aside>
        </div>
      </section>

      <section v-else class="page-content mistakes-page">
        <div class="page-intro mistakes-intro"><div><div class="eyebrow"><span class="eyebrow-line"></span> MEMORY ARCHIVE / REVIEW</div><h1>错题不会消失，<br /><em>但会越来越少。</em></h1><p class="intro-copy">每一次答错都留下线索，下一次就知道该从哪里开始。</p></div><div class="archive-actions"><button class="secondary-button" @click="openImport"><Upload :size="16" /> 导入 HTML</button><button class="primary-button compact" @click="exportMistakes"><Download :size="16" /> 导出档案</button><input ref="fileInput" class="visually-hidden" type="file" accept=".html,text/html" @change="importMistakes" /></div></div>
        <div class="archive-summary"><div><span class="summary-label">错题词数</span><strong>{{ wrongEntries.length }}</strong><small>个词仍在记忆中</small></div><div><span class="summary-label">累计错误</span><strong>{{ totalMistakes }}</strong><small>次答题记录</small></div><div><span class="summary-label">最常错 List</span><strong>{{ wrongEntries.length ? `List ${wrongEntries[0].list}` : '—' }}</strong><small>按出现频率排序</small></div><div><span class="summary-label">最近复习</span><strong>{{ wrongEntries.length ? formatDate(wrongEntries[0].lastSeen) : '—' }}</strong><small>保持一点点连续</small></div></div>

        <section class="mistake-table-panel"><div class="table-heading"><div><span class="section-kicker">REVIEW QUEUE</span><h2>需要再见面的词</h2></div><button v-if="wrongEntries.length" class="text-button danger" @click="clearMistakes"><Trash2 :size="15" /> 清空记录</button></div><div v-if="wrongEntries.length" class="mistake-table-wrap"><table><thead><tr><th>单词</th><th>释义</th><th>来源</th><th>错误次数</th><th>最近一次</th><th></th></tr></thead><tbody><tr v-for="item in wrongEntries" :key="`${item.list}-${item.word}`"><td><strong class="table-word">{{ item.word }}</strong></td><td class="meaning-cell">{{ item.meaning }}</td><td><span class="list-badge">List {{ item.list }}</span></td><td><span class="mistake-count">{{ item.count }} <small>次</small></span></td><td class="date-cell">{{ formatDate(item.lastSeen) }}</td><td><button class="row-action" title="练习这个 List" aria-label="练习这个 List" @click="chooseList(item.list)"><ArrowRight :size="16" /></button></td></tr></tbody></table></div><div v-else class="empty-archive"><div class="empty-icon"><CircleCheck :size="28" /></div><h3>这里还很干净。</h3><p>开始一轮练习，答错的单词会自动出现在这里。</p><button class="primary-button" @click="activeView = 'practice'"><Play :size="16" fill="currentColor" /> 去做一组练习</button></div></section>
      </section>
    </main>
    <Transition name="toast"><div v-if="toast" class="toast-message"><CircleCheck :size="17" /> {{ toast }}</div></Transition>
  </div>
</template>
