<template>
  <div class="spaceship-page">
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <div class="d-flex align-center gap-2 mb-1">
          <h2 class="text-h5 font-weight-bold">{{ tm('page.title') }}</h2>
          <v-chip size="x-small" color="primary" variant="tonal" label class="font-weight-bold">
            {{ tm('page.builtin') }}
          </v-chip>
        </div>
        <div class="text-body-2 text-medium-emphasis">
          {{ tm('page.subtitle') }}
        </div>
      </div>

      <div class="d-flex align-center gap-2">
        <v-btn variant="text" color="primary" prepend-icon="mdi-refresh" :loading="loading" @click="reload">
          {{ tm('actions.refresh') }}
        </v-btn>
        <v-btn variant="flat" color="primary" prepend-icon="mdi-content-save" :loading="saving" @click="save">
          {{ tm('actions.save') }}
        </v-btn>
      </div>
    </div>

    <v-row class="mb-6" dense>
      <v-col cols="12" md="6">
        <v-card class="rounded-lg h-100 border-thin" variant="flat" border>
          <v-card-text>
            <div class="text-subtitle-1 font-weight-bold mb-3">{{ tm('section.gateway') }}</div>

            <v-switch v-model="cfg.enable" color="primary" inset hide-details class="mb-4">
              <template #label>
                <div class="d-flex flex-column">
                  <span class="text-body-2 font-weight-medium">{{ tm('form.enable') }}</span>
                  <span class="text-caption text-medium-emphasis">{{ tm('form.enableHint') }}</span>
                </div>
              </template>
            </v-switch>

            <v-switch v-model="cfg.allow_auto_register" color="primary" inset hide-details class="mb-4">
              <template #label>
                <div class="d-flex flex-column">
                  <span class="text-body-2 font-weight-medium">{{ tm('form.autoRegister') }}</span>
                  <span class="text-caption text-medium-emphasis">{{ tm('form.autoRegisterHint') }}</span>
                </div>
              </template>
            </v-switch>

            <v-text-field
              v-model="cfg.websocket_path"
              :label="tm('form.websocketPath')"
              prepend-inner-icon="mdi-connection"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
              class="mb-4"
            />

            <v-text-field
              v-model="cfg.bootstrap_token"
              :label="tm('form.bootstrapToken')"
              prepend-inner-icon="mdi-key-variant"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
              class="mb-4"
            />

            <v-text-field
              v-model.number="cfg.heartbeat_timeout_sec"
              :label="tm('form.heartbeatTimeout')"
              prepend-inner-icon="mdi-timer-outline"
              type="number"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
            />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card class="rounded-lg h-100 border-thin" variant="flat" border>
          <v-card-text>
            <div class="text-subtitle-1 font-weight-bold mb-3">{{ tm('section.summary') }}</div>
            <div class="d-flex flex-column gap-3">
              <div class="summary-row">
                <span class="text-medium-emphasis">{{ tm('summary.totalNodes') }}</span>
                <span class="font-weight-bold">{{ nodes.length }}</span>
              </div>
              <div class="summary-row">
                <span class="text-medium-emphasis">{{ tm('summary.activeNodes') }}</span>
                <span class="font-weight-bold">{{ activeNodes }}</span>
              </div>
              <div class="summary-row">
                <span class="text-medium-emphasis">{{ tm('summary.gatewayStatus') }}</span>
                <v-chip :color="cfg.enable ? 'success' : 'grey'" size="small" variant="tonal">
                  {{ cfg.enable ? tm('status.enabled') : tm('status.disabled') }}
                </v-chip>
              </div>
              <div class="summary-row align-start">
                <span class="text-medium-emphasis pt-1">{{ tm('summary.defaultScopes') }}</span>
                <div class="d-flex flex-wrap gap-2 justify-end">
                  <v-chip
                    v-for="scope in cfg.default_granted_scopes"
                    :key="scope"
                    size="small"
                    color="primary"
                    variant="tonal"
                  >
                    {{ scope }}
                  </v-chip>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card class="rounded-lg border-thin" variant="flat" border>
      <v-card-text>
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <div class="text-subtitle-1 font-weight-bold">{{ tm('section.nodes') }}</div>
            <div class="text-caption text-medium-emphasis">{{ tm('section.nodesHint') }}</div>
          </div>
          <v-chip size="small" variant="tonal" color="primary">{{ nodes.length }}</v-chip>
        </div>

        <v-table density="comfortable">
          <thead>
            <tr>
              <th>{{ tm('table.alias') }}</th>
              <th>{{ tm('table.hostname') }}</th>
              <th>{{ tm('table.platform') }}</th>
              <th>{{ tm('table.status') }}</th>
              <th>{{ tm('table.scopes') }}</th>
              <th>{{ tm('table.lastSeen') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="node in nodes" :key="node.node_id">
              <td>
                <div class="font-weight-medium">{{ node.alias || node.node_id }}</div>
                <div class="text-caption text-medium-emphasis">{{ node.node_id }}</div>
              </td>
              <td>{{ node.hostname || '-' }}</td>
              <td>{{ node.platform }}/{{ node.arch }}</td>
              <td>
                <v-chip :color="node.status === 'active' ? 'success' : 'grey'" size="small" variant="tonal">
                  {{ node.status }}
                </v-chip>
              </td>
              <td>
                <div class="d-flex flex-wrap gap-1">
                  <v-chip v-for="scope in node.granted_scopes" :key="scope" size="x-small" variant="outlined">
                    {{ scope }}
                  </v-chip>
                </div>
              </td>
              <td>{{ formatDate(node.last_seen_at) }}</td>
            </tr>
            <tr v-if="nodes.length === 0">
              <td colspan="6" class="text-center text-medium-emphasis py-8">
                {{ tm('empty.nodes') }}
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000" location="top">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">{{ tm('actions.close') }}</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { useModuleI18n } from '@/i18n/composables'

type SpaceshipConfig = {
  enable: boolean
  websocket_path: string
  heartbeat_timeout_sec: number
  allow_auto_register: boolean
  bootstrap_token: string
  default_granted_scopes: string[]
}

type SpaceshipNode = {
  node_id: string
  alias: string
  hostname: string
  platform: string
  arch: string
  status: string
  granted_scopes: string[]
  last_seen_at: string | null
}

const { tm } = useModuleI18n('features/spaceship')

const loading = ref(false)
const saving = ref(false)
const nodes = ref<SpaceshipNode[]>([])
const cfg = ref<SpaceshipConfig>({
  enable: false,
  websocket_path: '/api/spaceship/ws',
  heartbeat_timeout_sec: 60,
  allow_auto_register: false,
  bootstrap_token: '',
  default_granted_scopes: ['exec', 'list_dir', 'read_file']
})

const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

const activeNodes = computed(() => nodes.value.filter((node) => node.status === 'active').length)

function toast(message: string, color: 'success' | 'error' | 'warning' = 'success') {
  snackbar.value = { show: true, message, color }
}

function normalizeConfig(raw: any): SpaceshipConfig {
  return {
    enable: !!raw?.enable,
    websocket_path: (raw?.websocket_path ?? '/api/spaceship/ws').toString(),
    heartbeat_timeout_sec: Number(raw?.heartbeat_timeout_sec ?? 60),
    allow_auto_register: !!raw?.allow_auto_register,
    bootstrap_token: (raw?.bootstrap_token ?? '').toString(),
    default_granted_scopes: Array.isArray(raw?.default_granted_scopes)
      ? raw.default_granted_scopes.map((item: any) => item.toString())
      : ['exec', 'list_dir', 'read_file']
  }
}

async function loadConfig() {
  const res = await axios.get('/api/spaceship/config')
  if (res.data.status !== 'ok') {
    throw new Error(res.data.message || tm('messages.loadConfigFailed'))
  }
  cfg.value = normalizeConfig(res.data.data)
}

async function loadNodes() {
  const res = await axios.get('/api/spaceship/nodes')
  if (res.data.status !== 'ok') {
    throw new Error(res.data.message || tm('messages.loadNodesFailed'))
  }
  nodes.value = Array.isArray(res.data.data) ? res.data.data : []
}

async function reload() {
  loading.value = true
  try {
    await Promise.all([loadConfig(), loadNodes()])
  } catch (e: any) {
    toast(e?.response?.data?.message || e?.message || tm('messages.loadConfigFailed'), 'error')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const res = await axios.post('/api/spaceship/config', cfg.value)
    if (res.data.status === 'ok') {
      toast(res.data.message || tm('messages.saveSuccess'))
    } else {
      toast(res.data.message || tm('messages.saveFailed'), 'error')
    }
  } catch (e: any) {
    toast(e?.response?.data?.message || tm('messages.saveFailed'), 'error')
  } finally {
    saving.value = false
  }
}

function formatDate(value: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

onMounted(() => {
  reload()
})
</script>

<style scoped>
.spaceship-page {
  padding: 24px;
  max-width: 1280px;
  margin: 0 auto;
}

.gap-2 {
  gap: 8px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.align-start {
  align-items: flex-start;
}
</style>
