<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { useBeaconStore } from '@/stores/beaconStore';
import { useRoute } from 'vue-router';

const beaconStore = useBeaconStore();
const route = useRoute();
// 实时计算活跃 Beacon 数量
const activeCount = computed(() => beaconStore.activeCount);
// 实时计算总 Beacon 数量
const totalCount = computed(() => beaconStore.beacons.length);

// 获取当前路由名称，用于高亮导航链接
// const currentRouteName = computed(() => beaconStore.selectedBeaconId ? 'Terminal' : 'Lobby');
const currentRouteName = computed(() => route.name);
</script>

<template>
  <div class="w-64 flex flex-col bg-gray-800 border-r border-gray-700 p-4">

    <div class="text-xl font-mono text-cyan-400 mb-6 border-b border-cyan-600/50 pb-2">
      Grimoire C2
    </div>

    <div class="space-y-4 mb-8">
      <div class="text-xs text-gray-400 uppercase tracking-wider">
        System Status
      </div>
      <div class="flex justify-between items-center text-sm">
        <span class="text-gray-300">Active Beacons:</span>
        <span class="font-bold text-green-400">{{ activeCount }}</span>
      </div>
      <div class="flex justify-between items-center text-sm">
        <span class="text-gray-300">Total Hosts:</span>
        <span class="font-bold text-yellow-400">{{ totalCount }}</span>
      </div>
    </div>


    <nav class="flex flex-col space-y-2">
      <RouterLink
          :to="{ name: 'Lobby' }"
          :class="['p-2 rounded-lg transition-colors duration-150', {
          'bg-cyan-700/50 text-white font-semibold': currentRouteName === 'Lobby',
          'hover:bg-gray-700': currentRouteName !== 'Lobby'
        }]"
      >
         Host Lobby
      </RouterLink>

      <RouterLink
          v-if="beaconStore.selectedBeaconId"
          :to="{ name: 'Terminal', params: { id: beaconStore.selectedBeaconId } }"
          :class="['p-2 rounded-lg transition-colors duration-150', {
          'bg-cyan-700/50 text-white font-semibold': currentRouteName === 'Terminal',
          'hover:bg-gray-700': currentRouteName !== 'Terminal'
        }]"
      >
        Terminal: {{ beaconStore.selectedBeaconId.substring(0, 8) }}...
      </RouterLink>


      <RouterLink
          v-if="beaconStore.selectedBeaconId"
          :to="{ name: 'FileBrowser', params: { id: beaconStore.selectedBeaconId } }"
          :class="['p-2 rounded-lg transition-colors duration-150', {
          'bg-cyan-700/50 text-white font-semibold': currentRouteName === 'FileBrowser',
          'hover:bg-gray-700 text-gray-300': currentRouteName !== 'FileBrowser'
      }]"
      >
        File Browser
      </RouterLink>

      <div
          v-else
          class="p-2 rounded-lg text-gray-600 cursor-not-allowed flex items-center select-none"
      >
        File Browser (No beacon selected)
      </div>

      <RouterLink
          :to="{ name: 'PayloadGenerator', params: { id: beaconStore.selectedBeaconId } }"
          :class="['p-2 rounded-lg transition-colors duration-150', {
          'bg-cyan-700/50 text-white font-semibold': currentRouteName === 'PayloadGenerator',
          'hover:bg-gray-700 text-gray-300': currentRouteName !== 'PayloadGenerator'
      }]"
      >
        PayloadGenerator
      </RouterLink>

    </nav>
  </div>
</template>