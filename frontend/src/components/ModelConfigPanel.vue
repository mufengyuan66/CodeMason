<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchModelConfig, saveModelConfig, testModel, type ModelConfig, type ModelTestResult } from '../api'

const models = ref<Record<string, ModelConfig>>({})
const loading = ref(true)
const saving = ref(false)
const testing = ref<string | null>(null) // 正在测试的 role
const testResults = ref<Record<string, ModelTestResult>>({})
const error = ref('')
const success = ref('')

// 编辑中的值
const editValues = ref<Record<string, { base_url: string; model: string; api_key: string }>>({})

async function loadConfig() {
  try {
    loading.value = true
    const res = await fetchModelConfig()
    models.value = res.models
    // 初始化编辑值
    for (const [role, cfg] of Object.entries(res.models)) {
      editValues.value[role] = {
        base_url: cfg.base_url,
        model: cfg.model,
        api_key: '', // 不回填 key，让用户手动输入
      }
    }
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  try {
    saving.value = true
    error.value = ''
    // 构建保存数据
    const toSave: Record<string, any> = {}
    for (const [role, cfg] of Object.entries(models.value)) {
      const edit = editValues.value[role] || {}
      toSave[role] = {
        provider: cfg.provider,
        base_url: edit.base_url || cfg.base_url,
        model: edit.model || cfg.model,
        api_key_ref: cfg.api_key_ref,
      }
      // 如果用户输入了新 key，更新 credentials.yaml
      if (edit.api_key) {
        toSave[role].api_key = edit.api_key
      }
    }
    await saveModelConfig(toSave)
    success.value = '配置已保存'
    setTimeout(() => success.value = '', 3000)
  } catch (e: any) {
    error.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function handleTest(role: string) {
  const edit = editValues.value[role]
  const cfg = models.value[role]
  if (!edit || !cfg) return

  testing.value = role
  testResults.value[role] = undefined as any
  error.value = ''

  try {
    // 如果用户没输入新 key，用 placeholder 提示
    const apiKey = edit.api_key || ''
    if (!apiKey) {
      error.value = `请先输入 ${role} 的 API Key`
      testing.value = null
      return
    }

    const result = await testModel(edit.base_url || cfg.base_url, edit.model || cfg.model, apiKey)
    testResults.value[role] = result
  } catch (e: any) {
    testResults.value[role] = {
      ok: false,
      latency_ms: 0,
      model: edit.model || cfg.model,
      error: e.message || '测试失败',
      response_preview: null,
    }
  } finally {
    testing.value = null
  }
}

onMounted(loadConfig)
</script>

<template>
  <div class="config-panel">
    <div class="config-header">
      <h2>模型配置</h2>
      <p class="config-subtitle">配置大语言模型连接参数，测试通过后即可使用</p>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="config-loading">
      <div class="spinner" />
      <span>加载配置...</span>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="config-alert is-error">
      <span class="alert-icon">⚠️</span>
      {{ error }}
      <button class="alert-close" @click="error = ''">×</button>
    </div>

    <!-- 成功提示 -->
    <div v-if="success" class="config-alert is-success">
      <span class="alert-icon">✅</span>
      {{ success }}
    </div>

    <!-- 模型列表 -->
    <div v-if="!loading" class="config-models">
      <div v-for="(cfg, role) in models" :key="role" class="model-card">
        <div class="model-header">
          <span class="model-role">{{ role === 'main' ? '🧠 主链路' : role === 'vision' ? '👁️ 视觉' : `🔧 ${role}` }}</span>
          <span class="model-status" :class="cfg.api_key_configured ? 'is-configured' : 'is-missing'">
            {{ cfg.api_key_configured ? 'Key 已配置' : 'Key 未配置' }}
          </span>
        </div>

        <div class="model-fields">
          <div class="field">
            <label>Base URL</label>
            <input v-model="editValues[role].base_url" type="text" class="field-input" placeholder="https://api.example.com/v1" />
          </div>
          <div class="field">
            <label>Model</label>
            <input v-model="editValues[role].model" type="text" class="field-input" placeholder="model-name" />
          </div>
          <div class="field">
            <label>API Key</label>
            <input v-model="editValues[role].api_key" type="password" class="field-input" placeholder="sk-..." autocomplete="off" />
          </div>
        </div>

        <!-- 测试结果 -->
        <div v-if="testResults[role]" class="test-result" :class="testResults[role].ok ? 'is-success' : 'is-error'">
          <div class="test-header">
            <span v-if="testResults[role].ok" class="test-icon">✅</span>
            <span v-else class="test-icon">❌</span>
            <span class="test-latency">{{ testResults[role].latency_ms }}ms</span>
            <span class="test-model">{{ testResults[role].model }}</span>
          </div>
          <div v-if="testResults[role].error" class="test-error">{{ testResults[role].error }}</div>
          <div v-if="testResults[role].response_preview" class="test-preview">
            <span class="preview-label">响应：</span>
            <span class="preview-text">{{ testResults[role].response_preview }}</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="model-actions">
          <button
            class="btn-test"
            :disabled="testing === role"
            @click="handleTest(role)"
          >
            <span v-if="testing === role" class="spinner-sm" />
            <span v-else>🧪</span>
            {{ testing === role ? '测试中...' : '测试连通性' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 底部操作 -->
    <div v-if="!loading" class="config-footer">
      <button class="btn-refresh" @click="loadConfig">🔄 重新加载</button>
      <button class="btn-save" :disabled="saving" @click="handleSave">
        {{ saving ? '保存中...' : '💾 保存配置' }}
      </button>
    </div>

    <!-- 提示 -->
    <div class="config-hint">
      <p>💡 配置文件位置：<code>~/.codemason/config.yaml</code></p>
      <p>🔑 凭据文件位置：<code>~/.codemason/credentials.yaml</code></p>
    </div>
  </div>
</template>

<style scoped>
.config-panel {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px 24px;
  font-family: var(--font-mono);
}

.config-header h2 {
  font-family: var(--font-display);
  font-size: var(--fs-lg);
  color: var(--c-text);
  margin: 0 0 4px;
}

.config-subtitle {
  font-size: var(--fs-xs);
  color: var(--c-text-dim);
  margin: 0 0 24px;
}

.config-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 32px 0;
  color: var(--c-text-dim);
  font-size: var(--fs-sm);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--c-border);
  border-top-color: var(--c-primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid var(--c-border);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.config-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs);
  margin-bottom: 16px;
}

.config-alert.is-error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.config-alert.is-success {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #6ee7b7;
}

.alert-close {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: var(--fs-md);
  padding: 0 4px;
}

.config-models {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.model-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  padding: 16px;
}

.model-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.model-role {
  font-weight: 600;
  font-size: var(--fs-sm);
  color: var(--c-text);
}

.model-status {
  font-size: var(--fs-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.model-status.is-configured {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
}

.model-status.is-missing {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

.model-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field label {
  display: block;
  font-size: var(--fs-xs);
  color: var(--c-text-dim);
  margin-bottom: 4px;
}

.field-input {
  width: 100%;
  padding: 8px 10px;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  color: var(--c-text);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: var(--c-primary);
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.15);
}

.field-input::placeholder {
  color: var(--c-text-dim);
  opacity: 0.5;
}

.test-result {
  margin-top: 10px;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs);
}

.test-result.is-success {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.test-result.is-error {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.test-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.test-latency {
  color: var(--c-primary-soft);
  font-family: var(--font-mono);
}

.test-model {
  color: var(--c-text-dim);
}

.test-error {
  margin-top: 6px;
  color: #fca5a5;
  word-break: break-all;
}

.test-preview {
  margin-top: 6px;
  color: var(--c-text-dim);
  font-style: italic;
}

.preview-label {
  color: var(--c-text-dim);
  opacity: 0.7;
}

.model-actions {
  margin-top: 12px;
}

.btn-test {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--c-surface-2);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  color: var(--c-text-dim);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-test:hover:not(:disabled) {
  border-color: var(--c-primary);
  color: var(--c-text);
}

.btn-test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.config-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--c-border);
}

.btn-refresh,
.btn-save {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-refresh {
  background: none;
  border: 1px solid var(--c-border);
  color: var(--c-text-dim);
}

.btn-refresh:hover {
  border-color: var(--c-text-dim);
  color: var(--c-text);
}

.btn-save {
  background: linear-gradient(135deg, var(--c-primary), var(--c-accent));
  border: none;
  color: #fff;
  font-weight: 600;
}

.btn-save:hover:not(:disabled) {
  transform: scale(1.02);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.config-hint {
  margin-top: 20px;
  padding: 12px;
  background: rgba(16, 31, 24, 0.4);
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs);
  color: var(--c-text-dim);
  line-height: 1.8;
}

.config-hint code {
  background: var(--c-surface-2);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
}
</style>
