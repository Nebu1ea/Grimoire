<script setup lang="ts">
import SidebarNav from './SidebarNav.vue';
import { onMounted } from 'vue';
import { useBeaconStore } from '@/stores/beaconStore';

// 引入 Store
const beaconStore = useBeaconStore();

onMounted(() => {
  // 页面加载时开始轮询 Beacon 数据
  beaconStore.startPolling();
});

// 在组件卸载前停止轮询
import { onUnmounted } from 'vue';
onUnmounted(() => {
  beaconStore.stopPolling();
});
</script>

<template>
  <div class="flex h-screen bg-gray-950 text-gray-100 antialiased">
    <SidebarNav />

    <main class="flex-1 overflow-x-hidden overflow-y-auto">
      <div class="px-6 py-4">
        <slot></slot>
      </div>
    </main>
  </div>
</template>