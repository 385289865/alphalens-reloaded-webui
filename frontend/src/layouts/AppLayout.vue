<template>
  <n-layout position="absolute">
    <n-layout-header bordered>
      <div class="header-inner">
        <router-link to="/sessions" class="logo">
          <n-gradient-text type="success" :size="20">Alphalens WebUI</n-gradient-text>
        </router-link>
        <div class="header-right">
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle @click="themeStore.toggle">
                <template #icon>
                  <n-icon :component="themeStore.darkMode ? SunnyOutline : MoonOutline" :size="20" />
                </template>
              </n-button>
            </template>
            {{ themeStore.darkMode ? 'Light Mode' : 'Dark Mode' }}
          </n-tooltip>
        </div>
      </div>
    </n-layout-header>
    <n-layout-content content-style="padding: 24px;">
      <router-view />
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { SunnyOutline, MoonOutline } from '@vicons/ionicons5';
import { useThemeStore } from '@/stores/themeStore';

const themeStore = useThemeStore();
</script>

<style scoped>
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  max-width: 1400px;
  margin: 0 auto;
}
.logo {
  text-decoration: none;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
