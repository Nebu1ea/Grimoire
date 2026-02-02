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
</script>

<template>
  <div class="p-8 bg-gray-900 min-h-screen text-cyan-400">
    <div class="max-w-2xl mx-auto bg-gray-800 border border-cyan-900/50 rounded-xl p-8 shadow-2xl">
      <h2 class="text-2xl font-mono mb-6 border-b border-cyan-600/30 pb-4">
        Payload Factory
      </h2>

      <div class="space-y-6">
        <div>
          <label class="block text-xs uppercase tracking-widest text-gray-500 mb-2">C2 Callback Host</label>
          <input v-model="config.host" type="text"
                 class="w-full bg-black/40 border border-gray-700 rounded p-3 focus:border-cyan-500 outline-none transition-all">
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs uppercase tracking-widest text-gray-500 mb-2">Callback Port</label>
            <input v-model="config.port" type="text"
                   class="w-full bg-black/40 border border-gray-700 rounded p-3 focus:border-cyan-500 outline-none transition-all">
          </div>
          <div>
            <label class="block text-xs uppercase tracking-widest text-gray-500 mb-2">Protocol</label>
            <select v-model="config.protocol"
                    class="w-full bg-black/40 border border-gray-700 rounded p-3 focus:border-cyan-500 outline-none transition-all appearance-none">
              <option value="http://">HTTP</option>
<!--              <option value="https://">HTTPS</option>-->
            </select>
          </div>
        </div>

        <div>
          <label class="block text-xs uppercase tracking-widest text-gray-500 mb-2">Target Platform</label>
          <div class="flex space-x-4">
            <button @click="config.platform = 'windows'"
                    :class="['flex-1 p-4 rounded border transition-all', config.platform === 'windows' ? 'border-cyan-500 bg-cyan-900/20' : 'border-gray-700 bg-black/20 text-gray-500']">
              Windows
            </button>
            <button @click="config.platform = 'linux'"
                    :class="['flex-1 p-4 rounded border transition-all', config.platform === 'linux' ? 'border-cyan-500 bg-cyan-900/20' : 'border-gray-700 bg-black/20 text-gray-500']">
              Linux
            </button>
          </div>
        </div>

        <div class="mt-8 pt-6 border-t border-gray-700/50">
          <p v-if="statusMsg" :class="['text-sm mb-4 font-mono', isGenerating ? 'text-yellow-400' : 'text-green-400']">
            {{ statusMsg }}
          </p>

          <button
              @click="generatePayload"
              :disabled="isGenerating"
              class="w-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 text-white font-bold py-4 rounded-lg shadow-lg shadow-cyan-900/20 transition-all active:scale-95">
            <span v-if="!isGenerating">SUMMON BEACON</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin h-5 w-5 mr-3 text-white" viewBox="0 0 24 24">
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
</template>