import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export const useThemeStore = defineStore('theme', () => {
  const darkMode = ref(true);

  const stored = localStorage.getItem('alphalens-theme');
  darkMode.value = stored !== null ? stored === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;

  function toggle() {
    darkMode.value = !darkMode.value;
    localStorage.setItem('alphalens-theme', darkMode.value ? 'dark' : 'light');
  }

  watch(darkMode, (val) => {
    document.documentElement.classList.toggle('dark', val);
  });

  return { darkMode, toggle };
});
