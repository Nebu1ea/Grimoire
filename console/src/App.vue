<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import AppLayout from './components/AppLayout.vue';
import { computed } from 'vue';

const route = useRoute();

// 判断当前路由是否需要应用 AppLayout (即是否为控制台界面)
const isConsoleLayout = computed(() => route.meta.requiresAuth);
</script>

<template>
  <AppLayout v-if="isConsoleLayout">
    <RouterView />
  </AppLayout>

  <RouterView v-else />
</template>