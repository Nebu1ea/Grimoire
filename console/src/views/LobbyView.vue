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
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white font-mono tracking-tight">
          HOST LOBBY <span class="text-cyan-500">_</span>
        </h1>
        <p class="text-gray-400 text-sm">监控并管理所有已连接的 Beacon 实例</p>
      </div>

      <div class="flex space-x-4">
        <div class="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg">
          <span class="text-gray-400 text-xs block uppercase">活跃总数</span>
          <span class="text-cyan-400 text-xl font-bold">{{ beaconStore.activeCount }}</span>
        </div>
        <button
            @click="beaconStore.fetchBeacons()"
            class="p-2 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg transition-colors"
            title="手动刷新"
        >
          <svg class="w-5 h-5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
        </button>
      </div>
    </div>

    <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
      <table class="w-full text-left border-collapse">
        <thead>
        <tr class="bg-gray-800/50 text-gray-400 text-xs uppercase tracking-wider">
          <th class="px-6 py-4 font-semibold">状态</th>
          <th class="px-6 py-4 font-semibold">标识 ID</th>
          <th class="px-6 py-4 font-semibold">用户 @ 主机</th>
          <th class="px-6 py-4 font-semibold">地址</th>
          <th class="px-6 py-4 font-semibold">最后心跳</th>
          <th class="px-6 py-4 font-semibold text-right">操作</th>
        </tr>
        </thead>
        <tbody class="divide-y divide-gray-800 text-sm">
        <tr
            v-for="beacon in beaconStore.formattedBeacons"
            :key="beacon.id"
            @click="goToTerminal(beacon)"
            class="hover:bg-cyan-900/10 cursor-pointer transition-colors group"
        >
          <td class="px-6 py-4">
              <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border"
                  :class="{
                  'bg-green-900/30 text-green-400 border-green-800': beacon.status === 'active',
                  'bg-red-900/30 text-red-400 border-red-800': beacon.status === 'dead',
                  'bg-yellow-900/30 text-yellow-400 border-yellow-800': beacon.status === 'sleep'
                }"
              >
                <span class="w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse" :class="beacon.status === 'active' ? 'bg-green-400' : 'bg-gray-400'"></span>
                {{ beacon.status.toUpperCase() }}
              </span>
          </td>

          <td class="px-6 py-4 font-mono text-cyan-500">{{ beacon.id.substring(0, 8) }}</td>
          <td class="px-6 py-4 font-medium text-gray-200">{{ beacon.user }} <span class="text-gray-500">@</span> {{ beacon.os }}</td>
          <td class="px-6 py-4 text-gray-400">{{ beacon.ip_address}}</td>
          <td class="px-6 py-4 text-gray-400">{{ beacon.last_checkin}}</td>

          <td class="px-6 py-4 text-right">
            <button class="text-gray-500 group-hover:text-cyan-400 transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M13 5l7 7-7 7M5 5l7 7-7 7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
            </button>
          </td>
        </tr>

        <tr v-if="beaconStore.beacons.length === 0">
          <td colspan="7" class="px-6 py-12 text-center text-gray-500">
            <div class="flex flex-col items-center">
              <svg class="w-12 h-12 mb-3 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9.172 9.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
              <p>暂无连接的 Beacon 实例，请等待上线...</p>
            </div>
          </td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>