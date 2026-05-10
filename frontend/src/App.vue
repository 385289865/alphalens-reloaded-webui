<template>
  <n-config-provider :theme="theme" :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-notification-provider>
      <n-message-provider>
        <n-dialog-provider>
          <n-loading-bar-provider>
            <router-view />
          </n-loading-bar-provider>
        </n-dialog-provider>
      </n-message-provider>
    </n-notification-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { darkTheme, zhCN, dateZhCN } from 'naive-ui';
import { useThemeStore } from '@/stores/themeStore';

const themeStore = useThemeStore();
const theme = computed(() => (themeStore.darkMode ? darkTheme : undefined));
const themeOverrides = computed(() => ({
  common: {
    fontFamily: 'Fira Sans, sans-serif',
    fontFamilyMono: 'Fira Code, monospace',
    ...(themeStore.darkMode
      ? {
          primaryColor: '#22C55E',
          primaryColorHover: '#4ADE80',
          primaryColorPressed: '#16A34A',
          bodyColor: '#020617',
          cardColor: '#0F172A',
          modalColor: '#0F172A',
          popoverColor: '#1E293B',
          tableColor: '#0F172A',
          inputColor: '#1E293B',
          textColorBase: '#F8FAFC',
          textColor1: '#F8FAFC',
          textColor2: '#CBD5E1',
          textColor3: '#94A3B8',
          borderColor: '#1E293B',
          dividerColor: '#1E293B',
          actionColor: '#0F172A',
          hoverColor: '#1E293B',
          closeColor: '#94A3B8',
          closeColorHover: '#F8FAFC',
          clearColor: '#94A3B8',
          clearColorHover: '#F8FAFC',
          successColor: '#22C55E',
          warningColor: '#F59E0B',
          errorColor: '#EF4444',
          infoColor: '#3B82F6',
          progressRailColor: '#1E293B',
        }
      : {
          primaryColor: '#22C55E',
          primaryColorHover: '#16A34A',
          primaryColorPressed: '#15803D',
          bodyColor: '#F8FAFC',
          cardColor: '#FFFFFF',
          modalColor: '#FFFFFF',
          popoverColor: '#FFFFFF',
          tableColor: '#FFFFFF',
          inputColor: '#FFFFFF',
          textColorBase: '#0F172A',
          textColor1: '#0F172A',
          textColor2: '#334155',
          textColor3: '#64748B',
          borderColor: '#E2E8F0',
          dividerColor: '#E2E8F0',
          actionColor: '#FFFFFF',
          hoverColor: '#F1F5F9',
        }),
  },
}));
</script>
