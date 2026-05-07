<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import AppLayout from './components/AppLayout.vue';
import AiAssistant from '@/components/AiAssistant.vue';
import { computed } from 'vue';

const route = useRoute();

// 判断当前路由是否需要应用 AppLayout (即是否为控制台界面)
const isConsoleLayout = computed(() => route.meta.requiresAuth);
</script>

<template>
  <template v-if="isConsoleLayout">
    <AppLayout>
      <RouterView />
    </AppLayout>
    <AiAssistant />
  </template>

  <RouterView v-else />
</template>