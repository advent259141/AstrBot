<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useCustomizerStore } from "@/stores/customizer";
import axios from "axios";
import Logo from "@/components/shared/Logo.vue";
import { md5 } from "js-md5";
import { useAuthStore } from "@/stores/auth";
import { useCommonStore } from "@/stores/common";
import { MarkdownRender, enableKatex, enableMermaid } from "markstream-vue";
import "markstream-vue/index.css";
import "katex/dist/katex.min.css";
import "highlight.js/styles/github.css";
import { useI18n } from "@/i18n/composables";
import { router } from "@/router";
import { useRoute } from "vue-router";
import { useTheme } from "vuetify";
import StyledMenu from "@/components/shared/StyledMenu.vue";
import { useLanguageSwitcher } from "@/i18n/composables";
import type { Locale } from "@/i18n/types";
import AboutPage from "@/views/AboutPage.vue";
import { getDesktopRuntimeInfo } from "@/utils/desktopRuntime";

enableKatex();
enableMermaid();

const customizer = useCustomizerStore();
const authStore = useAuthStore();
const theme = useTheme();
const { t } = useI18n();
const route = useRoute();
const LAST_BOT_ROUTE_KEY = "astrbot:last_bot_route";
let dialog = ref(false);
let accountWarning = ref(false);
let updateStatusDialog = ref(false);
let aboutDialog = ref(false);
const username = localStorage.getItem("user");
let password = ref("");
let newPassword = ref("");
let confirmPassword = ref("");
let newUsername = ref("");
let status = ref("");
let updateStatus = ref("");
let releaseMessage = ref("");
let hasNewVersion = ref(false);
let botCurrVersion = ref("");
let dashboardHasNewVersion = ref(false);
let dashboardCurrentVersion = ref("");
let version = ref("");
let releases = ref([]);
let updatingDashboardLoading = ref(false);
let installLoading = ref(false);
const isDesktopReleaseMode = ref(
  typeof window !== "undefined" && !!window.astrbotDesktop?.isDesktop,
);
const desktopUpdateDialog = ref(false);
const desktopUpdateChecking = ref(false);
const desktopUpdateInstalling = ref(false);
const desktopUpdateHasNewVersion = ref(false);
const desktopUpdateCurrentVersion = ref("-");
const desktopUpdateLatestVersion = ref("-");
const desktopUpdateStatus = ref("");

const getAppUpdaterBridge = (): AstrBotAppUpdaterBridge | null => {
  if (typeof window === "undefined") {
    return null;
  }
  const bridge = window.astrbotAppUpdater;
  if (
    bridge &&
    typeof bridge.checkForAppUpdate === "function" &&
    typeof bridge.installAppUpdate === "function"
  ) {
    return bridge;
  }
  return null;
};

const getSelectedGitHubProxy = () => {
  if (typeof window === "undefined" || !window.localStorage) return "";
  return localStorage.getItem("githubProxyRadioValue") === "1"
    ? localStorage.getItem("selectedGitHubProxy") || ""
    : "";
};

// Release Notes Modal
let releaseNotesDialog = ref(false);
let selectedReleaseNotes = ref("");
let selectedReleaseTag = ref("");

const releasesHeader = computed(() => [
  { title: t("core.header.updateDialog.table.tag"), key: "tag_name" },
  {
    title: t("core.header.updateDialog.table.publishDate"),
    key: "published_at",
  },
  { title: t("core.header.updateDialog.table.content"), key: "body" },
  { title: t("core.header.updateDialog.table.sourceUrl"), key: "zipball_url" },
  { title: t("core.header.updateDialog.table.actions"), key: "switch" },
]);
// Form validation
const formValid = ref(true);
const passwordRules = computed(() => [
  (v: string) =>
    !!v || t("core.header.accountDialog.validation.passwordRequired"),
  (v: string) =>
    v.length >= 8 ||
    t("core.header.accountDialog.validation.passwordMinLength"),
]);
const confirmPasswordRules = computed(() => [
  (v: string) =>
    !newPassword.value ||
    !!v ||
    t("core.header.accountDialog.validation.passwordRequired"),
  (v: string) =>
    !newPassword.value ||
    v === newPassword.value ||
    t("core.header.accountDialog.validation.passwordMatch"),
]);
const usernameRules = computed(() => [
  (v: string) =>
    !v ||
    v.length >= 3 ||
    t("core.header.accountDialog.validation.usernameMinLength"),
]);

// 显示密码相关
const showPassword = ref(false);
const showNewPassword = ref(false);
const showConfirmPassword = ref(false);

// 账户修改状态
const accountEditStatus = ref({
  loading: false,
  success: false,
  error: false,
  message: "",
});

function cancelDesktopUpdate() {
  if (desktopUpdateInstalling.value) {
    return;
  }
  desktopUpdateDialog.value = false;
}

async function openDesktopUpdateDialog() {
  desktopUpdateDialog.value = true;
  desktopUpdateChecking.value = true;
  desktopUpdateInstalling.value = false;
  desktopUpdateHasNewVersion.value = false;
  // ...
}

const commonStore = useCommonStore();
commonStore.createEventSource(); // log
commonStore.getStartTime();

// 视图模式切换
const viewMode = computed({
  get: () => customizer.viewMode,
  set: (value: "bot" | "chat") => {
    customizer.SET_VIEW_MODE(value);
  },
});

// 保存 bot 模式的最後路由
// 監聽 route 變化，保存最後一次 bot 路由
watch(
  () => route.fullPath,
  (newPath) => {
    if (customizer.viewMode === "bot" && typeof window !== "undefined") {
      try {
        localStorage.setItem(LAST_BOT_ROUTE_KEY, newPath);
      } catch (e) {
        console.error("Failed to save last bot route to localStorage:", e);
      }
    }
  },
);

// 監聽 viewMode 切換
watch(
  () => customizer.viewMode,
  (newMode, oldMode) => {
    if (
      newMode === "bot" &&
      oldMode === "chat" &&
      typeof window !== "undefined"
    ) {
      // 從 chat 切換回 bot，跳轉到最後一次的 bot 路由
      let lastBotRoute = "/";
      try {
        lastBotRoute = localStorage.getItem(LAST_BOT_ROUTE_KEY) || "/";
      } catch (e) {
        console.error("Failed to read last bot route from localStorage:", e);
      }
      router.push(lastBotRoute);
    }
  },
);
</script>

<template>
  <v-app-bar elevation="0" :priority="0" height="70" class="px-0">
    <v-container class="fill-height d-flex align-center">
      <!-- 桌面端标题栏拖拽区域 -->
      <div
        v-if="isDesktopReleaseMode"
        style="
          -webkit-app-region: drag;
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 30px;
          z-index: 9999;
        "
      ></div>

      <div class="d-flex align-center">
        <Logo />
      </div>

      <v-spacer />

      <!-- Bot/Chat 模式切换按钮 - 手机端隐藏，移入 ... 菜单 -->
      <div class="hidden-sm-and-down mr-4">
        <v-btn-toggle
          v-model="viewMode"
          color="primary"
          rounded="xl"
          group
          density="compact"
        >
          <v-btn value="chat" prepend-icon="mdi-chat-processing-outline">
            Chat
          </v-btn>
          <v-btn value="bot" prepend-icon="mdi-robot-outline"> Bot </v-btn>
        </v-btn-toggle>
      </div>

      <div class="mr-3">
        <v-chip
          v-if="hasNewVersion"
          color="error"
          variant="flat"
          size="small"
          class="cursor-pointer"
          @click="updateStatusDialog = true"
        >
          {{ t("core.header.updateAvailable") }}
        </v-chip>
      </div>

      <StyledMenu :menu="customizer.navbarMenu" />
    </v-container>
  </v-app-bar>
</template>
