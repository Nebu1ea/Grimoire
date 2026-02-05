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
  <div class="relative flex h-screen text-gray-100 antialiased font-mono overflow-hidden">

    <div class="fixed inset-0 -z-10 bg-[#050505] pointer-events-none">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_#1e293b_0%,#050505_100%)] opacity-70"></div>
      <div class="absolute inset-0 opacity-[0.05]" style="background-image: linear-gradient(to right, #22d3ee 1px, transparent 1px), linear-gradient(to bottom, #22d3ee 1px, transparent 1px); background-size: 50px 50px;"></div>
      <div class="absolute inset-0">
        <div class="scanner-line line-1"></div>
        <div class="scanner-line line-2"></div>

        <div class="v-scanner-line v-line-1"></div>
        <div class="v-scanner-line v-line-2"></div>
      </div>
    </div>

    <SidebarNav class="relative z-20 border-r border-white/5 bg-black/20 backdrop-blur-xl shrink-0" />

    <main class="relative z-10 flex-1 overflow-x-hidden overflow-y-auto custom-scrollbar bg-transparent">
      <div class="px-8 py-6 min-h-full">
        <slot></slot>
      </div>
    </main>

  </div>
</template>

<style scoped>
@keyframes scan {
  0% { transform: translateY(-10vh); opacity: 0; }
  15% { opacity: 0.3; }
  85% { opacity: 0.3; }
  100% { transform: translateY(110vh); opacity: 0; }


  0% { transform: translateY(-10vh); opacity: 0; }
  15% { opacity: 0.8; }
  85% { opacity: 0.8; }
  100% { transform: translateY(110vh); opacity: 0; }
}


@keyframes scan-horizontal-move {
  0% {
    transform: translateX(-10vw);
    opacity: 0;
  }
  20% { opacity: 0.3; }
  80% { opacity: 0.3; }
  100% {
    transform: translateX(110vw);
    opacity: 0;
  }
}


.scanner-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  opacity: 0;
  height: 1px;
  background: linear-gradient(to right, transparent, #06b6d4, #d946ef, transparent);
  box-shadow: 0 0 15px rgba(6, 182, 212, 0.2);
}

.line-1 { animation: scan 12s linear infinite; }
.line-2 { animation: scan 20s linear infinite 5s; }

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(34, 211, 238, 0.2);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(34, 211, 238, 0.5);
}

.v-scanner-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 1px;
  height: 100vh;
  opacity: 0;
  background: linear-gradient(to bottom,
  transparent,
  rgba(6, 182, 212, 0.2),
  rgba(217, 70, 239, 0.2),
  transparent
  );
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.1);
  will-change: transform;
  z-index: 5;
}

.v-line-1 {
  animation: scan-horizontal-move 20s linear infinite;
}

.v-line-2 {
  animation: scan-horizontal-move 25s linear infinite 8s;
}


</style>