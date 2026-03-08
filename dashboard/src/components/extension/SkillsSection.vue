<template>
  <div class="skills-page">
    <!-- Top tab navigation -->
    <v-tabs v-model="activeTab" color="primary" class="mb-1">
      <v-tab value="installed">
        <v-icon size="small" class="me-2">mdi-package-variant</v-icon>
        {{ tm('skills.tabs.installed') }}
      </v-tab>
      <v-tab value="market">
        <v-icon size="small" class="me-2">mdi-store</v-icon>
        {{ tm('skills.tabs.market') }}
      </v-tab>
    </v-tabs>

    <v-divider class="mb-4" />

    <v-window v-model="activeTab">
      <!-- Installed skills tab -->
      <v-window-item value="installed">
        <v-container fluid class="pa-0">
          <v-row class="d-flex justify-space-between align-center px-4 py-3 pb-4">
            <div>
              <v-btn color="success" prepend-icon="mdi-upload" class="me-2" variant="tonal" @click="uploadDialog = true">
                {{ tm('skills.upload') }}
              </v-btn>
              <v-btn color="primary" prepend-icon="mdi-refresh" variant="tonal" @click="fetchSkills">
                {{ tm('skills.refresh') }}
              </v-btn>
            </div>
          </v-row>

          <div class="px-4 pb-2">
            <small style="color: grey;">{{ tm('skills.runtimeHint') }}</small>
          </div>

          <v-progress-linear v-if="loading" indeterminate color="primary" class="mt-2" />

          <div v-else-if="skills.length === 0" class="text-center pa-8">
            <v-icon size="64" color="grey-lighten-1">mdi-folder-open</v-icon>
            <p class="text-grey mt-4">{{ tm('skills.empty') }}</p>
            <small class="text-grey">{{ tm('skills.emptyHint') }}</small>
          </div>

          <v-row v-else class="px-2 mt-2">
            <v-col v-for="skill in skills" :key="skill.name" cols="12" md="6" lg="4" xl="3">
              <item-card :item="skill" title-field="name" enabled-field="active" :loading="itemLoading[skill.name] || false"
                :show-edit-button="false" @toggle-enabled="toggleSkill" @delete="confirmDelete">
                <template v-slot:item-details="{ item }">
                  <div class="text-caption text-medium-emphasis mb-2 skill-description">
                    <v-icon size="small" class="me-1">mdi-text</v-icon>
                    {{ item.description || tm('skills.noDescription') }}
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    <v-icon size="small" class="me-1">mdi-file-document</v-icon>
                    {{ tm('skills.path') }}: {{ item.path }}
                  </div>
                </template>
              </item-card>
            </v-col>
          </v-row>
        </v-container>
      </v-window-item>

      <!-- Skill market tab -->
      <v-window-item value="market">
        <v-container fluid class="pa-0">
          <!-- Market header with source management -->
          <div class="d-flex align-center flex-wrap px-4 pt-2 pb-4" style="gap: 12px;">
            <v-tooltip location="top" :text="tm('skills.market.sourceManagement')">
              <template v-slot:activator="{ props }">
                <v-btn v-bind="props" variant="tonal" rounded="md" color="primary" class="text-none px-3"
                  @click="openSourceManagerDialog">
                  <v-icon size="18" class="mr-1">mdi-source-branch</v-icon>
                  <span class="text-truncate" style="max-width: 200px;">{{ currentSourceName }}</span>
                </v-btn>
              </template>
            </v-tooltip>

            <v-btn color="primary" prepend-icon="mdi-refresh" variant="tonal" :loading="marketLoading"
              @click="fetchMarketSkills">
              {{ tm('skills.market.refresh') }}
            </v-btn>
          </div>

          <v-progress-linear v-if="marketLoading" indeterminate color="primary" />

          <div v-else-if="marketError" class="px-4 pb-4">
            <v-alert type="warning" variant="tonal" density="comfortable">
              {{ marketError }}
            </v-alert>
          </div>

          <div v-else-if="marketSkills.length === 0" class="text-center pa-8">
            <v-icon size="52" color="grey-lighten-1">mdi-store-search</v-icon>
            <p class="text-grey mt-3">{{ tm('skills.market.empty') }}</p>
          </div>

          <v-row v-else class="px-2">
            <v-col v-for="mSkill in marketSkills" :key="mSkill.id || mSkill.github_url || mSkill.name"
              cols="12" md="6" lg="4" xl="3">
              <v-card variant="outlined" class="h-100 d-flex flex-column skill-market-card" elevation="0">
                <v-card-text class="pb-2">
                  <div class="d-flex align-center justify-space-between mb-2">
                    <div class="text-subtitle-1 font-weight-bold market-title">
                      {{ mSkill.display_name || mSkill.name }}
                    </div>
                    <v-chip size="x-small" label color="primary" variant="outlined">
                      {{ mSkill.category || '-' }}
                    </v-chip>
                  </div>

                  <div class="text-caption text-medium-emphasis mb-2 market-name">{{ mSkill.name }}</div>

                  <div class="market-description mb-3">
                    {{ mSkill.description || tm('skills.noDescription') }}
                  </div>

                  <div class="d-flex align-center flex-wrap" style="gap: 6px;">
                    <v-chip size="x-small" color="warning" label>⭐ {{ mSkill.star_count || 0 }}</v-chip>
                    <v-chip size="x-small" color="success" label>⬇ {{ mSkill.download_count || 0 }}</v-chip>
                    <v-chip v-if="mSkill.updated_at" size="x-small" variant="outlined" label>
                      {{ formatDate(mSkill.updated_at) }}
                    </v-chip>
                  </div>
                </v-card-text>

                <v-card-actions class="pt-0 px-4 pb-3 d-flex flex-wrap" style="gap: 6px;">
                  <v-btn color="success" variant="tonal" size="small"
                    :disabled="isMarketSkillInstalled(mSkill)"
                    :loading="marketInstallLoading[getMarketSkillKey(mSkill)] || false"
                    @click="installMarketSkill(mSkill)">
                    {{ isMarketSkillInstalled(mSkill) ? tm('skills.market.installed') : tm('skills.market.install') }}
                  </v-btn>
                  <v-btn v-if="mSkill.id" variant="text" size="small" @click="openMarketDetail(mSkill)">
                    {{ tm('skills.market.viewDetail') }}
                  </v-btn>
                  <v-btn v-if="mSkill.github_url" variant="text" size="small"
                    @click="openGithub(mSkill.github_url)">
                    {{ tm('skills.market.viewRepo') }}
                  </v-btn>
                </v-card-actions>
              </v-card>
            </v-col>
          </v-row>
        </v-container>
      </v-window-item>
    </v-window>

    <!-- Source manager dialog -->
    <v-dialog v-model="showSourceManagerDialog" width="560">
      <v-card>
        <v-card-title class="text-h3 pa-4 pl-6">{{ tm('skills.market.sourceManagement') }}</v-card-title>
        <v-card-text>
          <v-select :model-value="selectedSource || '__default__'"
            @update:model-value="selectSkillSource($event === '__default__' ? null : $event)"
            :items="sourceSelectItems" :label="tm('skills.market.currentSource')" variant="outlined"
            prepend-inner-icon="mdi-source-branch" hide-details class="mb-4" />

          <div class="d-flex align-center justify-space-between mb-2">
            <div class="text-subtitle-2">{{ tm('skills.market.availableSources') }}</div>
            <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-plus"
              @click="openAddSourceDialog">
              {{ tm('skills.market.addSource') }}
            </v-btn>
          </div>

          <v-list density="compact" nav class="pa-0">
            <v-list-item rounded="md" color="primary" :active="selectedSource === null"
              @click="selectSkillSource(null)">
              <template v-slot:prepend>
                <v-icon icon="mdi-shield-check" size="small" class="mr-2" />
              </template>
              <v-list-item-title>{{ tm('skills.market.defaultSource') }}</v-list-item-title>
            </v-list-item>

            <v-list-item v-for="source in customSources" :key="source.url" rounded="md" color="primary"
              :active="selectedSource === source.url" @click="selectSkillSource(source.url)">
              <template v-slot:prepend>
                <v-icon icon="mdi-link-variant" size="small" class="mr-2" />
              </template>
              <v-list-item-title>{{ source.name }}</v-list-item-title>
              <v-list-item-subtitle class="text-caption">{{ source.url }}</v-list-item-subtitle>
              <template v-slot:append>
                <v-btn icon="mdi-pencil-outline" size="small" variant="text" color="medium-emphasis"
                  @click.stop="openEditSourceDialog(source)" />
                <v-btn icon="mdi-trash-can-outline" size="small" variant="text" color="error"
                  @click.stop="promptRemoveSource(source)" />
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="text" @click="showSourceManagerDialog = false">
            {{ tm('skills.market.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add / edit source dialog -->
    <v-dialog v-model="showSourceDialog" width="480">
      <v-card>
        <v-card-title class="text-h5">
          {{ editingSource ? tm('skills.market.editSource') : tm('skills.market.addSource') }}
        </v-card-title>
        <v-card-text>
          <div class="pa-2">
            <v-text-field v-model="sourceName" :label="tm('skills.market.sourceName')" variant="outlined"
              prepend-inner-icon="mdi-rename-box" hide-details class="mb-4"
              :placeholder="tm('skills.market.sourceNamePlaceholder')" />
            <v-text-field v-model="sourceUrl" :label="tm('skills.market.sourceUrl')" variant="outlined"
              prepend-inner-icon="mdi-link" hide-details
              placeholder="https://skill.astrbot.app" />
            <div class="text-caption text-medium-emphasis mt-2">
              {{ tm('skills.market.sourceUrlHint') }}
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="showSourceDialog = false">
            {{ tm('skills.cancel') }}
          </v-btn>
          <v-btn color="primary" variant="text" @click="saveSource">
            {{ tm('skills.market.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Remove source confirm dialog -->
    <v-dialog v-model="showRemoveSourceDialog" width="400">
      <v-card>
        <v-card-title class="text-h5 d-flex align-center">
          <v-icon color="warning" class="mr-2">mdi-alert-circle</v-icon>
          {{ tm('skills.market.removeSource') }}
        </v-card-title>
        <v-card-text>
          <div>{{ tm('skills.market.confirmRemoveSource') }}</div>
          <div v-if="sourceToRemove" class="mt-2">
            <strong>{{ sourceToRemove.name }}</strong>
            <div class="text-caption">{{ sourceToRemove.url }}</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="showRemoveSourceDialog = false">
            {{ tm('skills.cancel') }}
          </v-btn>
          <v-btn color="error" variant="text" @click="confirmRemoveSource">
            {{ tm('skills.market.deleteSource') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Upload dialog -->
    <v-dialog v-model="uploadDialog" max-width="520px">
      <v-card>
        <v-card-title class="text-h3 pa-4 pb-0 pl-6">{{ tm('skills.uploadDialogTitle') }}</v-card-title>
        <v-card-text>
          <small class="text-grey">{{ tm('skills.uploadHint') }}</small>
          <v-file-input v-model="uploadFile" accept=".zip" :label="tm('skills.selectFile')"
            prepend-icon="mdi-folder-zip-outline" variant="outlined" class="mt-4" :multiple="false" />
        </v-card-text>
        <v-card-actions class="d-flex justify-end">
          <v-btn variant="text" @click="uploadDialog = false">{{ tm('skills.cancel') }}</v-btn>
          <v-btn color="primary" :loading="uploading" :disabled="!uploadFile" @click="uploadSkill">
            {{ tm('skills.confirmUpload') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title>{{ tm('skills.deleteTitle') }}</v-card-title>
        <v-card-text>{{ tm('skills.deleteMessage') }}</v-card-text>
        <v-card-actions class="d-flex justify-end">
          <v-btn variant="text" @click="deleteDialog = false">{{ tm('skills.cancel') }}</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteSkill">
            {{ t('core.common.itemCard.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :timeout="3000" :color="snackbar.color" elevation="24">
      {{ snackbar.message }}
    </v-snackbar>
  </div>
</template>

<script>
import axios from "axios";
import { ref, reactive, computed, onMounted } from "vue";
import ItemCard from "@/components/shared/ItemCard.vue";
import { useI18n, useModuleI18n } from "@/i18n/composables";

const DEFAULT_SKILL_MARKET_URL = "https://skill.astrbot.app";

export default {
  name: "SkillsSection",
  components: { ItemCard },
  setup() {
    const { t } = useI18n();
    const { tm } = useModuleI18n("features/extension");

    // ── tab ──────────────────────────────────────────────────────────────
    const activeTab = ref("installed");

    // ── installed skills ─────────────────────────────────────────────────
    const skills = ref([]);
    const loading = ref(false);
    const uploading = ref(false);
    const uploadDialog = ref(false);
    const uploadFile = ref(null);
    const itemLoading = reactive({});
    const deleteDialog = ref(false);
    const deleting = ref(false);
    const skillToDelete = ref(null);

    // ── market ────────────────────────────────────────────────────────────
    const marketSkills = ref([]);
    const marketLoading = ref(false);
    const marketError = ref("");
    const marketInstallLoading = reactive({});
    const installedGithubSet = ref(new Set());

    // ── source management ─────────────────────────────────────────────────
    const customSources = ref([]);
    const selectedSource = ref(null);
    const showSourceManagerDialog = ref(false);
    const showSourceDialog = ref(false);
    const showRemoveSourceDialog = ref(false);
    const editingSource = ref(false);
    const originalSourceUrl = ref("");
    const sourceName = ref("");
    const sourceUrl = ref("");
    const sourceToRemove = ref(null);

    // ── snackbar ──────────────────────────────────────────────────────────
    const snackbar = reactive({ show: false, message: "", color: "success" });

    const showMessage = (message, color = "success") => {
      snackbar.message = message;
      snackbar.color = color;
      snackbar.show = true;
    };

    // ── computed ───────────────────────────────────────────────────────────
    const currentSourceName = computed(() => {
      if (!selectedSource.value) return tm("skills.market.defaultSource");
      const matched = customSources.value.find((s) => s.url === selectedSource.value);
      return matched?.name || tm("skills.market.defaultSource");
    });

    const sourceSelectItems = computed(() => [
      { title: tm("skills.market.defaultSource"), value: "__default__" },
      ...customSources.value.map((s) => ({ title: s.name, value: s.url })),
    ]);

    const effectiveMarketUrl = computed(
      () => selectedSource.value || DEFAULT_SKILL_MARKET_URL,
    );

    // ── source management methods ──────────────────────────────────────────
    const loadCustomSources = async () => {
      try {
        const res = await axios.get("/api/skills/source/get");
        if (res.data.status === "ok") {
          customSources.value = res.data.data;
        }
      } catch (e) {
        console.warn("Failed to load skill custom sources:", e);
        customSources.value = [];
      }
      const saved = localStorage.getItem("selectedSkillSource");
      if (saved) selectedSource.value = saved;
    };

    const saveCustomSourcesToServer = async () => {
      try {
        await axios.post("/api/skills/source/save", { sources: customSources.value });
      } catch (e) {
        console.warn("Failed to save skill custom sources:", e);
      }
    };

    const selectSkillSource = (url) => {
      selectedSource.value = url;
      if (url) {
        localStorage.setItem("selectedSkillSource", url);
      } else {
        localStorage.removeItem("selectedSkillSource");
      }
      fetchMarketSkills();
    };

    const openSourceManagerDialog = async () => {
      await loadCustomSources();
      showSourceManagerDialog.value = true;
    };

    const openAddSourceDialog = () => {
      showSourceManagerDialog.value = false;
      editingSource.value = false;
      originalSourceUrl.value = "";
      sourceName.value = "";
      sourceUrl.value = "";
      showSourceDialog.value = true;
    };

    const openEditSourceDialog = (source) => {
      showSourceManagerDialog.value = false;
      editingSource.value = true;
      originalSourceUrl.value = source.url;
      sourceName.value = source.name;
      sourceUrl.value = source.url;
      showSourceDialog.value = true;
    };

    const saveSource = () => {
      const normalizedUrl = sourceUrl.value.trim();
      if (!sourceName.value.trim() || !normalizedUrl) {
        showMessage(tm("skills.market.fillSourceFields"), "error");
        return;
      }
      try {
        new URL(normalizedUrl);
      } catch {
        showMessage(tm("skills.market.invalidUrl"), "error");
        return;
      }

      if (editingSource.value) {
        const idx = customSources.value.findIndex(
          (s) => s.url === originalSourceUrl.value,
        );
        if (idx !== -1) {
          customSources.value[idx] = { name: sourceName.value.trim(), url: normalizedUrl };
          if (selectedSource.value === originalSourceUrl.value) {
            selectedSource.value = normalizedUrl;
            localStorage.setItem("selectedSkillSource", normalizedUrl);
          }
        }
      } else {
        if (customSources.value.some((s) => s.url === normalizedUrl)) {
          showMessage(tm("skills.market.sourceExists"), "error");
          return;
        }
        customSources.value.push({ name: sourceName.value.trim(), url: normalizedUrl });
      }

      saveCustomSourcesToServer();
      showMessage(tm("skills.market.sourceSaved"), "success");
      showSourceDialog.value = false;
      showSourceManagerDialog.value = true;
    };

    const promptRemoveSource = (source) => {
      showSourceManagerDialog.value = false;
      sourceToRemove.value = source;
      showRemoveSourceDialog.value = true;
    };

    const confirmRemoveSource = () => {
      if (!sourceToRemove.value) return;
      customSources.value = customSources.value.filter(
        (s) => s.url !== sourceToRemove.value.url,
      );
      saveCustomSourcesToServer();
      if (selectedSource.value === sourceToRemove.value.url) {
        selectedSource.value = null;
        localStorage.removeItem("selectedSkillSource");
        fetchMarketSkills();
      }
      showMessage(tm("skills.market.sourceRemoved"), "success");
      showRemoveSourceDialog.value = false;
      sourceToRemove.value = null;
    };

    // ── installed skills methods ───────────────────────────────────────────
    const normalizeGithubUrl = (url) =>
      (url || "").trim().replace(/\.git$/i, "").replace(/\/+$/, "").toLowerCase();

    const guessRepoUrlFromName = (name) =>
      name ? `https://github.com/${name}/${name}`.toLowerCase() : "";

    const refreshInstalledGithubSet = () => {
      const next = new Set();
      for (const s of skills.value || []) {
        if (s?.github_url) next.add(normalizeGithubUrl(s.github_url));
        if (s?.name) next.add(guessRepoUrlFromName(s.name));
      }
      installedGithubSet.value = next;
    };

    const fetchSkills = async () => {
      loading.value = true;
      try {
        const res = await axios.get("/api/skills");
        const payload = res.data?.data || [];
        skills.value = Array.isArray(payload) ? payload : payload.skills || [];
        refreshInstalledGithubSet();
      } catch {
        showMessage(tm("skills.loadFailed"), "error");
      } finally {
        loading.value = false;
      }
    };

    const handleApiResponse = (res, successMsg, failureMsg, onSuccess) => {
      if (res?.data?.status === "ok") {
        showMessage(successMsg, "success");
        onSuccess?.();
      } else {
        showMessage(res?.data?.message || failureMsg, "error");
      }
    };

    const uploadSkill = async () => {
      if (!uploadFile.value) return;
      uploading.value = true;
      try {
        const formData = new FormData();
        const file = Array.isArray(uploadFile.value)
          ? uploadFile.value[0]
          : uploadFile.value;
        if (!file) return;
        formData.append("file", file);
        const res = await axios.post("/api/skills/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        handleApiResponse(res, tm("skills.uploadSuccess"), tm("skills.uploadFailed"), async () => {
          uploadDialog.value = false;
          uploadFile.value = null;
          await fetchSkills();
        });
      } catch {
        showMessage(tm("skills.uploadFailed"), "error");
      } finally {
        uploading.value = false;
      }
    };

    const toggleSkill = async (skill) => {
      const nextActive = !skill.active;
      itemLoading[skill.name] = true;
      try {
        const res = await axios.post("/api/skills/update", {
          name: skill.name,
          active: nextActive,
        });
        handleApiResponse(res, tm("skills.updateSuccess"), tm("skills.updateFailed"), () => {
          skill.active = nextActive;
        });
      } catch {
        showMessage(tm("skills.updateFailed"), "error");
      } finally {
        itemLoading[skill.name] = false;
      }
    };

    const confirmDelete = (skill) => {
      skillToDelete.value = skill;
      deleteDialog.value = true;
    };

    const deleteSkill = async () => {
      if (!skillToDelete.value) return;
      deleting.value = true;
      try {
        const res = await axios.post("/api/skills/delete", {
          name: skillToDelete.value.name,
        });
        handleApiResponse(res, tm("skills.deleteSuccess"), tm("skills.deleteFailed"), async () => {
          deleteDialog.value = false;
          await fetchSkills();
        });
      } catch {
        showMessage(tm("skills.deleteFailed"), "error");
      } finally {
        deleting.value = false;
      }
    };

    // ── market methods ────────────────────────────────────────────────────
    const getMarketSkillKey = (skill) =>
      normalizeGithubUrl(skill?.github_url) || skill?.id || skill?.name || "unknown";

    const isMarketSkillInstalled = (skill) => {
      const github = normalizeGithubUrl(skill?.github_url);
      if (github && installedGithubSet.value.has(github)) return true;
      const localName = (skill?.name || "").toLowerCase();
      return !!skills.value.find((s) => (s?.name || "").toLowerCase() === localName);
    };

    const fetchMarketSkills = async () => {
      marketError.value = "";
      marketSkills.value = [];
      marketLoading.value = true;
      try {
        const params = { page: 1, size: 20, sort: "downloads" };
        if (selectedSource.value) {
          params.source_url = selectedSource.value;
        }
        const res = await axios.get("/api/skills/market", { params });
        const payload = res.data?.data || {};
        marketSkills.value = payload.skills || [];
      } catch {
        marketError.value = tm("skills.market.unavailable");
      } finally {
        marketLoading.value = false;
      }
    };

    const buildGithubZipUrl = (githubUrl) => {
      const normalized = (githubUrl || "").replace(/\.git$/i, "").replace(/\/+$/, "");
      return `${normalized}/archive/refs/heads/main.zip`;
    };

    const installMarketSkill = async (skill) => {
      const githubUrl = (skill?.github_url || "").trim();
      if (!githubUrl) {
        showMessage(tm("skills.market.invalidGithubUrl"), "error");
        return;
      }
      const key = getMarketSkillKey(skill);
      marketInstallLoading[key] = true;
      try {
        const res = await axios.post("/api/skills/install_from_url", {
          url: buildGithubZipUrl(githubUrl),
          github_url: githubUrl,
          market_url: effectiveMarketUrl.value,
        });
        if (res?.data?.status === "ok") {
          showMessage(tm("skills.market.installSuccess"), "success");
          await fetchSkills();
        } else {
          showMessage(res?.data?.message || tm("skills.market.installFailed"), "error");
        }
      } catch (err) {
        showMessage(err?.response?.data?.message || tm("skills.market.installFailed"), "error");
      } finally {
        marketInstallLoading[key] = false;
      }
    };

    const openGithub = (url) => {
      if (url) window.open(url, "_blank", "noopener,noreferrer");
    };

    const openMarketDetail = (skill) => {
      const base = (effectiveMarketUrl.value || "").replace(/\/+$/, "");
      if (base && skill?.id) {
        window.open(`${base}/skills/${skill.id}`, "_blank", "noopener,noreferrer");
      }
    };

    const formatDate = (value) => {
      if (!value) return "";
      const dt = new Date(value);
      return Number.isNaN(dt.getTime()) ? "" : dt.toLocaleDateString();
    };

    // ── lifecycle ─────────────────────────────────────────────────────────
    onMounted(async () => {
      await loadCustomSources();
      await fetchSkills();
      await fetchMarketSkills();
    });

    return {
      t,
      tm,
      activeTab,
      skills,
      loading,
      uploadDialog,
      uploadFile,
      uploading,
      itemLoading,
      marketInstallLoading,
      deleteDialog,
      deleting,
      snackbar,
      marketSkills,
      marketLoading,
      marketError,
      customSources,
      selectedSource,
      showSourceManagerDialog,
      showSourceDialog,
      showRemoveSourceDialog,
      editingSource,
      sourceName,
      sourceUrl,
      sourceToRemove,
      currentSourceName,
      sourceSelectItems,
      fetchSkills,
      fetchMarketSkills,
      uploadSkill,
      toggleSkill,
      confirmDelete,
      deleteSkill,
      getMarketSkillKey,
      isMarketSkillInstalled,
      installMarketSkill,
      openGithub,
      openMarketDetail,
      formatDate,
      openSourceManagerDialog,
      openAddSourceDialog,
      openEditSourceDialog,
      saveSource,
      selectSkillSource,
      promptRemoveSource,
      confirmRemoveSource,
    };
  },
};
</script>

<style scoped>
.skill-market-card {
  border-radius: 12px;
  transition: all .18s ease;
}

.skill-market-card:hover {
  transform: translateY(-2px);
  border-color: rgba(var(--v-theme-primary), .45);
  box-shadow: 0 8px 20px rgba(0, 0, 0, .14);
}

.market-title,
.market-name,
.skill-description {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.market-description {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
