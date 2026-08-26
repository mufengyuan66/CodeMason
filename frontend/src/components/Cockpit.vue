<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { fetchSessions, switchSession, useCockpit } from '../api'
import Timeline from './Timeline.vue'
import DialogueView from './DialogueView.vue'
import SessionRail from './SessionRail.vue'
import ConfirmDialog from './ConfirmDialog.vue'
import ThemePanel from './ThemePanel.vue'
import YagniBoard from './YagniBoard.vue'
import FileViewer from './FileViewer.vue'
import CostCockpit from './CostCockpit.vue'
import ContextPanel from './ContextPanel.vue'
import HealthSignals from './HealthSignals.vue'
import ContributionPanel from './ContributionPanel.vue'
import ApprovalInboxPanel from './ApprovalInboxPanel.vue'
import VisionPanel from './VisionPanel.vue'
import RootCausePanel from './RootCausePanel.vue'
import EvolutionPanel from './EvolutionPanel.vue'
import FirstRunGuide from './FirstRunGuide.vue'
import ApprovalInline from './ApprovalInline.vue'
import SuccessFeedback from './SuccessFeedback.vue'
import ModelConfigPanel from './ModelConfigPanel.vue'
import type { Event } from '../api'

interface Props {
  onBack: () => void
}

const props = defineProps<Props>()

const HEALTH_POLL_MS = 15000
const VIEW_KEY = 'codemason-center-view'

// 状态管理
const getInitialSession = (): string => {
  try {
    return sessionStorage.getItem('codemason-session') || 'web'
  } catch {
    return 'web'
  }
}

const getInitialView = (): string => {
  try {
    return sessionStorage.getItem(VIEW_KEY) || 'timeline'
  } catch {
    return 'timeline'
  }
}

const activeSession = ref<string>(getInitialSession())
const centerView = ref<string>(getInitialView())

const sessions = ref<any[]>([])
const input = ref('')
const mode = ref<'act' | 'plan'>('act')
const approvals = ref<Event[]>([])
const viewerFile = ref<any>(null)
const drawerView = ref<string | null>(null)
const confirm = ref<{ type: string } | null>(null)
const modeHint = ref(false)
const health = ref<any>(null)
const sessionsError = ref('')
const themeOpen = ref(false)
const showConfig = ref(false) // 模型配置面板
let modeHintTimer: number | null = null

// 权限控制（参考 Codex 三档权限：default / auto-review / full-access）
const permissionLevel = ref<'default' | 'auto-review' | 'full-access'>('default')
const permissionLevels = ['default', 'auto-review', 'full-access'] as const
const permissionLabels: Record<string, string> = {
  'default': '默认',
  'auto-review': '自动审查',
  'full-access': '完全访问'
}
const permissionIcons: Record<string, string> = {
  'default': '🔒',
  'auto-review': '🛡️',
  'full-access': '🔓'
}

const permissionLabel = computed(() => permissionLabels[permissionLevel.value])
const permissionIcon = computed(() => permissionIcons[permissionLevel.value])

const cyclePermission = () => {
  const idx = permissionLevels.indexOf(permissionLevel.value)
  permissionLevel.value = permissionLevels[(idx + 1) % permissionLevels.length]
}

// 模型选择（参考 Codex 右下角模型选择）
const models = ['deepseek-v4-flash', 'deepseek-v4', 'gpt-5.4-mini']
const currentModelIndex = ref(0)
const currentModel = computed(() => models[currentModelIndex.value])

const cycleModel = () => {
  currentModelIndex.value = (currentModelIndex.value + 1) % models.length
}

// P0-1: 首次运行引导
const showFirstRun = ref(false)
const isFirstRun = () => {
  try {
    return !sessionStorage.getItem('codemason-first-run-done')
  } catch {
    return true
  }
}

// P0-3: 成功反馈
const showSuccess = ref(false)
const successData = ref({ linesReduced: 0, testsPassed: 0, duration: 0 })

// WebSocket 连接
const { connected, events, sendTurn, sendApproval, cancelTurn, compact } = useCockpit({
  sessionId: activeSession,
  onEvent: (ev: Event) => {
    if (ev.type === 'ExecApprovalRequest') {
      approvals.value = [...approvals.value.filter((a) => a.approval_id !== ev.approval_id), ev]
    }
  },
})

// 会话列表加载
watch(activeSession, async () => {
  try {
    sessions.value = await fetchSessions()
  } catch {
    sessionsError.value = '会话列表加载失败'
  }
}, { immediate: true })

// 健康信号轮询（被动横幅，不打断主流程）
onMounted(() => {
  // P0-1: 检查是否首次运行
  if (isFirstRun()) {
    showFirstRun.value = true
  }

  let alive = true
  async function poll() {
    try {
      const res = await fetch('/health-signals', { headers: { 'x-agent-token': 'demo-token' } })
      if (res.ok) {
        const data = await res.json()
        if (alive) health.value = data.enabled ? data.report : null
      }
    } catch {
      /* 静默：健康面板未挂载不打扰 */
    }
  }
  poll()
  const t = setInterval(poll, HEALTH_POLL_MS)
  onUnmounted(() => {
    alive = false
    clearInterval(t)
  })
})

// YAGNI 指标
const yagniMetrics = computed(() => {
  return events.value
    .filter((e: Event) => e.type === 'ItemCompleted' && e.metrics)
    .map((e: Event) => e.metrics)
})

const handleSend = () => {
  const text = input.value.trim()
  if (!text) return
  sendTurn(text, { mode: mode.value })
  input.value = ''
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

const handleModeSwitch = (next: 'act' | 'plan') => {
  mode.value = next
  modeHint.value = true
  if (modeHintTimer) clearTimeout(modeHintTimer)
  modeHintTimer = setTimeout(() => {
    modeHint.value = false
  }, 3000) as any
}

const handleSessionSelect = async (sid: string) => {
  if (sid === activeSession.value) return
  try {
    await switchSession(sid)
    activeSession.value = sid
    try {
      sessionStorage.setItem('codemason-session', sid)
    } catch {
      /* ignore */
    }
    approvals.value = []
    drawerView.value = null
  } catch {
    sessionsError.value = '切换会话失败'
  }
}

const handleSessionNew = async (name: string) => {
  try {
    await switchSession(name)
    activeSession.value = name
    try {
      sessionStorage.setItem('codemason-session', name)
    } catch {
      /* ignore */
    }
    approvals.value = []
    drawerView.value = null
  } catch {
    sessionsError.value = '创建会话失败'
  }
}

const healthBad = computed(() => {
  return health.value && (health.value.status === 'degraded' || health.value.status === 'critical')
})

const toggleDrawer = (id: string) => {
  drawerView.value = drawerView.value === id ? null : id
}

const setCenterView = (view: string) => {
  centerView.value = view
  try { sessionStorage.setItem(VIEW_KEY, view) } catch { /* ignore */ }
}

const toggleTheme = () => {
  themeOpen.value = !themeOpen.value
}

const closeConfirm = () => {
  confirm.value = null
}

const confirmCompact = () => {
  compact('session')
  closeConfirm()
}

const confirmCancel = () => {
  cancelTurn('user cancelled from cockpit')
  closeConfirm()
}

const drawerTabs = [
  { id: 'files', label: '文件', icon: '☰' },
  { id: 'yagni', label: 'YAGNI', icon: '▣' },
  { id: 'costs', label: '成本', icon: '⚡' },
  { id: 'context', label: '上下文', icon: '🧠' },
  { id: 'health', label: '健康', icon: '💓' },
  { id: 'contribution', label: '贡献', icon: '📜' },
  { id: 'inbox', label: '收件箱', icon: '📥' },
  { id: 'vision', label: '视觉', icon: '👁' },
  { id: 'rootcause', label: '溯源', icon: '🔍' },
  { id: 'evolution', label: '进化', icon: '🧬' },
]

// P0-1: 首次运行引导处理
const handleFirstRunDismiss = () => {
  showFirstRun.value = false
  try {
    sessionStorage.setItem('codemason-first-run-done', '1')
  } catch { /* ignore */ }
}

const handleFirstRunUseExample = (task: string) => {
  input.value = task
  showFirstRun.value = false
  try {
    sessionStorage.setItem('codemason-first-run-done', '1')
  } catch { /* ignore */ }
  // 自动发送示例任务
  nextTick(() => {
    handleSend()
  })
}

// P0-2: 审批内联处理
const handleApproveInline = (approvalId: string) => {
  sendApproval(approvalId, 'approve')
  approvals.value = approvals.value.filter(a => a.approval_id !== approvalId)
}

const handleRejectInline = (approvalId: string, reason: string) => {
  sendApproval(approvalId, 'reject', reason)
  approvals.value = approvals.value.filter(a => a.approval_id !== approvalId)
}

// P0-3: 成功反馈处理
const handleViewTimeline = () => {
  showSuccess.value = false
  setCenterView('timeline')
}

const handleDismissSuccess = () => {
  showSuccess.value = false
}

// 监听任务完成，显示成功反馈
watch(events, (newEvents) => {
  const completedEvents = newEvents.filter((e: Event) => e.type === 'ItemCompleted')
  if (completedEvents.length > 0) {
    const latest = completedEvents[completedEvents.length - 1]
    if (latest.metrics) {
      successData.value = {
        linesReduced: latest.metrics.lines_reduced || 0,
        testsPassed: latest.metrics.tests_passed || 0,
        duration: latest.metrics.duration_seconds || 0
      }
      showSuccess.value = true
    }
  }
}, { deep: true })
</script>

<template>
  <div class="cockpit" data-testid="cockpit">
    <!-- P0-1: 首次运行引导 -->
    <FirstRunGuide
      v-if="showFirstRun"
      @dismiss="handleFirstRunDismiss"
      @use-example="handleFirstRunUseExample"
    />

    <!-- 顶栏 -->
    <header class="cockpit-topbar">
      <button class="topbar-btn" data-testid="cp-back" aria-label="返回" @click="props.onBack">
        <svg class="topbar-btn-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
        <span class="topbar-btn-text">返回</span>
      </button>
      <div class="cp-brand">
        <span class="cp-logo">CM</span>
        <span class="cp-title">CodeMason 驾驶舱</span>
      </div>
      <div :class="['cp-status', connected ? 'is-online' : 'is-offline']" @click="showConfig = !showConfig" style="cursor: pointer" title="点击配置模型">
        <span class="status-dot" />
        {{ connected ? '内核已连接' : '点击配置模型' }}
      </div>
      <button class="topbar-btn" title="释放空间（压缩历史记录）" aria-label="释放空间（压缩历史记录）" data-testid="cp-compact" @click="confirm = { type: 'compact' }">
        <svg class="topbar-btn-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
        <span class="topbar-btn-text">压缩</span>
      </button>
      <button class="topbar-btn" title="停止当前任务" aria-label="停止当前任务" data-testid="cp-cancel" @click="confirm = { type: 'cancel' }">
        <svg class="topbar-btn-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="10" x2="14" y1="12" y2="12"/></svg>
        <span class="topbar-btn-text">停止</span>
      </button>
      <button class="topbar-btn" title="主题设置" aria-label="主题设置" data-testid="cp-theme" @click="toggleTheme">
        <svg class="topbar-btn-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
        <span class="topbar-btn-text">主题</span>
      </button>
    </header>

    <!-- 健康被动横幅（不打断主流程） -->
    <div v-if="healthBad" class="health-banner" data-testid="health-banner">
      <span class="health-banner-dot" />
      会话健康度 {{ health.status === 'critical' ? '严重下降' : '下降' }}（连续卡住 {{ health.stuck_count ?? 0 }} 次），建议开新会话
      <button class="health-banner-close" aria-label="关闭健康提示" @click="health = null">×</button>
    </div>

    <!-- 三区主体 -->
    <div class="cockpit-main">
      <SessionRail :sessions="sessions" :active-id="activeSession" @select="handleSessionSelect" @new="handleSessionNew" />

      <main class="cp-center">
        <!-- v1.29 双投影切换器：对话视图（折叠投影）/ 时间线（展开投影）——同一事件流两种渲染 -->
        <div class="cp-center-switcher" data-testid="center-view-switcher">
          <button
            :class="['view-btn', { 'is-active': centerView === 'dialogue' }]"
            data-testid="view-dialogue"
            @click="setCenterView('dialogue')"
          >
            对话视图
          </button>
          <button
            :class="['view-btn', { 'is-active': centerView === 'timeline' }]"
            data-testid="view-timeline"
            @click="setCenterView('timeline')"
          >
            时间线
          </button>
        </div>
        
        <DialogueView v-if="centerView === 'dialogue'" :events="events" :send-approval="sendApproval" />
        <Timeline v-else :events="events" :send-approval="sendApproval" />

        <!-- P0-2: 内联审批卡片（在对话/时间线下方显示） -->
        <div v-if="approvals.length > 0" class="approvals-inline-area">
          <ApprovalInline
            v-for="approval in approvals"
            :key="approval.approval_id"
            :approval-id="approval.approval_id"
            :tool-name="approval.tool_name || 'Unknown'"
            :command="approval.command || ''"
            :risk-level="approval.risk_level || 'medium'"
            @approve="handleApproveInline"
            @reject="handleRejectInline"
          />
        </div>
        
        <footer class="cp-inputbar">
          <!-- 权限控制（参考 Codex 三档权限） -->
          <div class="cp-permission" :class="{ 'is-active': permissionLevel !== 'default' }" @click="cyclePermission">
            <span class="cp-permission-icon">{{ permissionIcon }}</span>
            <span class="cp-permission-text">{{ permissionLabel }}</span>
          </div>

          <!-- 模式切换（执行/规划） -->
          <div class="cp-mode-switch">
            <button :class="['mode-btn', { 'is-active': mode === 'act' }]" data-testid="mode-act" @click="handleModeSwitch('act')">
              执行
            </button>
            <button :class="['mode-btn', { 'is-active': mode === 'plan' }]" data-testid="mode-plan" @click="handleModeSwitch('plan')">
              规划
            </button>
          </div>

          <!-- 输入框 -->
          <textarea
            v-model="input"
            class="cp-input"
            placeholder="输入任务描述…（Agent 忙时自动排队）"
            data-testid="cp-input"
            rows="2"
            @keydown="handleKeyDown"
          />

          <!-- 模型选择（参考 Codex 右下角模型选择） -->
          <div class="cp-model-select" @click="cycleModel">
            <span class="cp-model-name">{{ currentModel }}</span>
            <span class="cp-model-arrow">▼</span>
          </div>

          <!-- 发送按钮 -->
          <button class="cp-send" :disabled="!input.trim()" data-testid="cp-send" @click="handleSend">
            <span class="cp-send-icon">↑</span>
            发送
          </button>
        </footer>

        <!-- 模式提示（保留原有） -->
        <div v-if="modeHint" class="mode-hint" data-testid="mode-hint">
          {{ mode === 'plan' ? '规划：只读模式，Agent 不改任何文件，先出方案' : '执行：Agent 可读写文件并运行命令（危险操作需审批）' }}
        </div>
      </main>

      <!-- 右：监控抽屉 -->
      <aside class="cp-drawer">
        <div class="drawer-tabs">
          <button
            v-for="m in drawerTabs"
            :key="m.id"
            :class="['drawer-tab', { 'is-active': drawerView === m.id }]"
            :data-testid="`drawer-${m.id}`"
            :aria-label="m.label"
            @click="toggleDrawer(m.id)"
          >
            <span class="drawer-icon">{{ m.icon }}</span>
            <span class="drawer-label">{{ m.label }}</span>
          </button>
        </div>
        <div v-if="drawerView" class="drawer-panel" data-testid="drawer-panel">
          <FileViewer v-if="drawerView === 'files'" :file="viewerFile" :events="events" @select="viewerFile = $event" />
          <YagniBoard v-if="drawerView === 'yagni'" :metrics="yagniMetrics" />
          <CostCockpit v-if="drawerView === 'costs'" />
          <ContextPanel v-if="drawerView === 'context'" />
          <HealthSignals v-if="drawerView === 'health'" />
          <ContributionPanel v-if="drawerView === 'contribution'" />
          <ApprovalInboxPanel v-if="drawerView === 'inbox'" />
          <VisionPanel v-if="drawerView === 'vision'" :events="events" />
          <RootCausePanel v-if="drawerView === 'rootcause'" :events="events" />
          <EvolutionPanel v-if="drawerView === 'evolution'" />
        </div>
      </aside>
    </div>

    <!-- 确认弹层：压缩 / 取消 -->
    <ConfirmDialog
      v-if="confirm?.type === 'compact'"
      title="释放空间？"
      desc="整理本会话的早期记录，让 Agent 响应更快。历史记录会完整保留，可随时回看。"
      confirm-label="释放空间"
      @confirm="confirmCompact"
      @cancel="closeConfirm"
    />
    <ConfirmDialog
      v-if="confirm?.type === 'cancel'"
      title="停止当前任务？"
      desc="Agent 正在执行的操作将终止。已完成的修改会保留，不会丢失。"
      confirm-label="停止任务"
      @confirm="confirmCancel"
      @cancel="closeConfirm"
    />

    <!-- P0-3: 成功反馈 -->
    <div v-if="showSuccess" class="success-feedback-overlay">
      <SuccessFeedback
        :lines-reduced="successData.linesReduced"
        :tests-passed="successData.testsPassed"
        :duration="successData.duration"
        @view-timeline="handleViewTimeline"
        @dismiss="handleDismissSuccess"
      />
    </div>

    <!-- 主题面板（换壁纸式个性化） -->
    <ThemePanel v-if="themeOpen" @close="themeOpen = false" />

    <!-- 模型配置面板（全屏覆盖层） -->
    <div v-if="showConfig" class="config-overlay">
      <div class="config-overlay-header">
        <button class="config-overlay-close" @click="showConfig = false">← 返回驾驶舱</button>
      </div>
      <ModelConfigPanel />
    </div>
  </div>
</template>