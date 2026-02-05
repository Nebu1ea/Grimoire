<script setup lang="ts">
import { ref } from 'vue';
import apiClient from '@/utils/http';

const config = ref({
  host: window.location.hostname, // 默认当前服务器 IP
  port: '8080',
  protocol: 'http://',
  platform: 'windows'
});

const isGenerating = ref(false);
const statusMsg = ref('');

const generatePayload = async () => {
  isGenerating.value = true;
  statusMsg.value = '正在编译...';

  try {
    const response = await apiClient.post('/operator/payload/generate', config.value, {
      responseType: 'blob',
      // 增加超时，毕竟编译挺慢的，别中途断了
      timeout: 60000
    });

    const blobData = response.data || response;

    // 如果 Blob 太小，说明可能接的是报错 JSON
    if (blobData.size < 500) {
      // 尝试把 Blob 转回文本看看是不是报错
      const text = await blobData.text();
      statusMsg.value = '后端报错了！';
      return;
    }

    const url = window.URL.createObjectURL(new Blob([blobData]));
    const link = document.createElement('a');
    link.href = url;

    // 自动适配后缀
    const ext = config.value.platform === 'windows' ? '.exe' : '.elf';
    link.setAttribute('download', `Grimoire_${Date.now()}${ext}`);

    document.body.appendChild(link);
    link.click();

    link.remove();
    window.URL.revokeObjectURL(url);
    statusMsg.value = '快去虚拟机里投毒吧（划掉）！';

  } catch (error: any) {
    console.error("中短:", error);
    statusMsg.value = '失败，检查网络。';
  } finally {
    isGenerating.value = false;
  }
};

const showDropdown = ref(false)
const toggleDropdown = () => {
  showDropdown.value = !showDropdown.value
}

const selectProtocol = (proto: any) => {
  config.value.protocol = proto
  showDropdown.value = false
}
</script>

<template>
  <div class="min-h-screen w-full flex items-center justify-center p-8 bg-transparent">

    <div class="relative w-full max-w-xl group">

      <div class="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-fuchsia-600 rounded-2xl opacity-10 group-hover:opacity-30 transition duration-1000 blur-xl"></div>

      <div class="relative overflow-hidden rounded-2xl border border-cyan-500/10 bg-black/10 backdrop-blur-3xl p-8 md:p-10 shadow-2xl">

        <div class="absolute top-0 left-0 h-[2px] w-full bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent"></div>

        <h2 class="mb-8 flex items-center text-2xl font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-cyan-100">
          <span class="mr-3 text-fuchsia-500 animate-pulse">></span>
          PAYLOAD_FACTORY
        </h2>

        <div class="space-y-6">
          <div class="group/input relative">
            <label class="mb-2 block text-[10px] font-bold uppercase tracking-[0.3em] text-cyan-900 transition-colors group-focus-within/input:text-cyan-400">
              C2 Callback Host
            </label>
            <div class="relative">
              <input
                  v-model="config.host"
                  type="text"
                  placeholder="127.0.0.1"
                  class="w-full rounded-lg bg-cyan-950/10 p-3 text-cyan-100 placeholder-cyan-900/30 outline-none ring-1 ring-cyan-500/10 transition-all focus:ring-2 focus:ring-cyan-500/40"
              >
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="group/input">
              <label class="mb-2 block text-[10px] font-bold uppercase tracking-[0.3em] text-cyan-900">Port</label>
              <input
                  v-model="config.port"
                  type="text"
                  class="w-full rounded-lg bg-cyan-950/10 p-3 text-cyan-100 outline-none ring-1 ring-cyan-500/10 focus:ring-2 focus:ring-cyan-500/40"
              >
            </div>
            <div class="group/input relative">
              <label class="mb-2 block text-[10px] font-bold uppercase tracking-[0.3em] text-fuchsia-900">
                Protocol
              </label>

              <div class="relative">
                <div
                    @click="showDropdown = !showDropdown"
                    class="w-full cursor-pointer rounded-lg bg-fuchsia-950/10 p-3 text-fuchsia-100 ring-1 ring-fuchsia-500/10 flex items-center justify-between focus:ring-2 focus:ring-fuchsia-500/40"
                >
                  <span>{{ config.protocol }}</span>
                  <span :class="{'rotate-180': showDropdown}" class="text-fuchsia-500/50 text-[8px] transition-transform duration-300">▼</span>
                </div>

                <transition name="fade-slide">
                  <div v-if="showDropdown" class="absolute left-0 right-0 mt-2 z-50 rounded-lg border border-fuchsia-500/20 bg-black/60 backdrop-blur-xl overflow-hidden shadow-2xl">
                    <div
                        v-for="opt in ['http://', 'https://']"
                        :key="opt"
                        @click="config.protocol = opt; showDropdown = false"
                        class="px-4 py-3 hover:bg-fuchsia-500/20 cursor-pointer text-xs tracking-widest text-fuchsia-100/70 hover:text-fuchsia-300 transition-colors border-b border-fuchsia-500/5 last:border-0"
                    >
                      {{ opt }}
                    </div>
                  </div>
                </transition>
              </div>
            </div>
          </div>

          <div>
            <label class="mb-3 block text-[10px] font-bold uppercase tracking-[0.3em] text-slate-600">Target System</label>
            <div class="flex gap-3">
              <button
                  @click="config.platform = 'windows'"
                  :class="['relative flex-1 overflow-hidden rounded-lg border py-3 text-xs transition-all duration-300',
                  config.platform === 'windows'
                    ? 'border-cyan-400 bg-cyan-500/10 text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.1)]'
                    : 'border-white/5 bg-white/5 text-slate-500 hover:border-white/10']"
              >
                <span class="relative z-10 flex items-center justify-center gap-2">WINDOWS</span>
              </button>

              <button
                  @click="config.platform = 'linux'"
                  :class="['relative flex-1 overflow-hidden rounded-lg border py-3 text-xs transition-all duration-300',
                  config.platform === 'linux'
                    ? 'border-cyan-400 bg-cyan-500/10 text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.1)]'
                    : 'border-white/5 bg-white/5 text-slate-500 hover:border-white/10']"
              >
                <span class="relative z-10 flex items-center justify-center gap-2">LINUX</span>
              </button>
            </div>
          </div>

          <div class="mt-8 border-t border-white/5 pt-6">
            <div class="mb-4 min-h-[20px]">
              <p v-if="statusMsg" :class="['font-mono text-[10px] tracking-widest', isGenerating ? 'text-yellow-500' : 'text-green-500']">
                {{ statusMsg }}
              </p>
            </div>

            <button
                @click="generatePayload"
                :disabled="isGenerating"
                class="group relative w-full overflow-hidden rounded-lg bg-cyan-500/10 border border-cyan-500/30 py-3 font-bold text-cyan-400 transition-all hover:bg-cyan-500/20 active:scale-[0.98] disabled:opacity-20">
              <span v-if="!isGenerating" class="tracking-[0.3em] text-sm">SUMMON_BEACON</span>
              <span v-else class="flex items-center justify-center text-sm tracking-widest">
                <svg class="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                FORGING...
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>