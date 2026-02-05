<script setup lang="ts">
import { onMounted } from 'vue';
import { useBeaconStore } from '@/stores/beaconStore';
import { useRouter } from 'vue-router';

const beaconStore = useBeaconStore();
const router = useRouter();

// 页面加载时拉取数据
onMounted(() => {
  beaconStore.fetchBeacons();
});

// 点击行进入终端详情页
const goToTerminal = (beacon: { id: string | null; }) => {
  beaconStore.selectedBeaconId = beacon.id;
  router.push({ name: 'Terminal', params: { id: beacon.id } });
};
</script>


<template>
  <div class="space-y-8 w-full max-w-6xl mx-auto p-4">

    <div class="flex items-end justify-between border-b border-cyan-500/20 pb-4">
      <div>
        <h1 class="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-cyan-100 font-mono tracking-tighter drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
          HOST_LOBBY
        </h1>
        <p class="text-cyan-600/70 text-xs font-mono tracking-[0.2em] mt-1 uppercase">
          Active Beacon Monitoring System // Ver 0.2
        </p>
      </div>

      <div class="flex items-center space-x-6">
        <div class="group relative px-5 py-2 overflow-hidden rounded border border-cyan-500/20 bg-cyan-950/10 backdrop-blur-sm">
          <div class="absolute inset-0 bg-cyan-500/5 group-hover:bg-cyan-500/10 transition-colors"></div>
          <div class="relative flex flex-col items-end">
            <span class="text-[10px] text-cyan-500/70 uppercase tracking-widest font-bold">Live Units</span>
            <span class="text-2xl font-mono text-cyan-100 font-bold drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]">
              {{ String(beaconStore.activeCount).padStart(2, '0') }}
            </span>
          </div>
        </div>

        <button
            @click="beaconStore.fetchBeacons()"
            class="relative p-3 group border border-cyan-500/20 rounded bg-black/20 hover:bg-cyan-500/10 hover:border-cyan-500/50 transition-all active:scale-95"
            title="SYNC DATA"
        >
          <svg class="w-5 h-5 text-cyan-500 group-hover:animate-spin-slow transition-colors group-hover:text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
        </button>
      </div>
    </div>

    <div class="relative rounded-xl overflow-hidden border border-white/5 bg-black/10 backdrop-blur-md shadow-2xl">
      <div class="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent"></div>

      <table class="w-full text-left border-collapse">
        <thead>
        <tr class="border-b border-white/5 text-xs uppercase tracking-[0.15em] text-cyan-700/80 font-mono">
          <th class="px-6 py-5 font-bold">Status</th>
          <th class="px-6 py-5 font-bold">Beacon_ID</th>
          <th class="px-6 py-5 font-bold">User <span class="text-fuchsia-800">@</span> Host</th>
          <th class="px-6 py-5 font-bold">IP_Addr</th>
          <th class="px-6 py-5 font-bold">Last_Heartbeat</th>
        </tr>
        </thead>


      <tbody class="divide-y divide-white/5 text-sm font-mono">
      <tr
          v-for="beacon in beaconStore.formattedBeacons"
          :key="beacon.id"
          @click="goToTerminal(beacon)"
          class="group relative hover:bg-cyan-500/5 transition-all duration-300 cursor-pointer"
      >
        <td class="px-6 py-5">
          <div class="flex items-center gap-3">
            <div class="relative flex h-2.5 w-2.5">
                  <span
                      class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                      :class="{
                      'bg-green-400': beacon.status === 'active',
                      'bg-red-500': beacon.status === 'dead',
                      'bg-yellow-500': beacon.status === 'stale'
                    }"
                  ></span>
              <span
                  class="relative inline-flex rounded-full h-2.5 w-2.5 shadow-[0_0_8px_currentColor]"
                  :class="{
                      'bg-green-500 text-green-500': beacon.status === 'active',
                      'bg-red-500 text-red-500': beacon.status === 'dead',
                      'bg-yellow-500 text-yellow-500': beacon.status === 'stale'
                    }"
              ></span>
            </div>
            <span class="text-[10px] font-bold tracking-widest uppercase"
                  :class="beacon.status === 'active' ? 'text-green-400' : 'text-gray-500'">
                {{ beacon.status }}
            </span>
          </div>
        </td>

        <td class="px-6 py-5">
      <span class="px-2 py-1 rounded bg-cyan-500/10 text-cyan-400 text-xs border border-cyan-500/20 group-hover:border-cyan-500/50 transition-colors">
        {{ beacon.id.substring(0, 8).toUpperCase() }}
      </span>
        </td>

        <td class="px-6 py-5">
          <div class="flex items-center text-gray-300 group-hover:text-white transition-colors">
            <span class="font-bold">{{ beacon.user }}</span>
            <span class="text-fuchsia-500 mx-1.5 opacity-50">@</span>
            <span class="text-gray-400 group-hover:text-cyan-200">{{ beacon.os }}</span>
          </div>
        </td>

        <td class="px-6 py-5 text-gray-500 group-hover:text-cyan-500/70">
          {{ beacon.ip_address }}
        </td>

        <td class="px-6 py-5 text-gray-600 text-xs">
          {{ beacon.last_checkin }}
        </td>

        <td class="px-6 py-5 text-right">
        </td>
      </tr>
      </tbody>
      </table>

      <div class="h-1 w-full bg-gradient-to-r from-cyan-900/0 via-cyan-900/30 to-cyan-900/0"></div>
    </div>
  </div>
</template>

<style scoped>
/* 定义一个慢速旋转，给雷达和刷新按钮用 */
@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin-slow {
  animation: spin-slow 3s linear infinite;
}
</style>