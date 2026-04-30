<script setup lang="ts">
import {computed, nextTick, ref} from 'vue';
import { useRoute } from 'vue-router';
import { useFileStore } from '@/stores/fileStore';
import { useTerminalStore } from '@/stores/terminalStore';

const route = useRoute();
const fileStore = useFileStore();
const terminalStore = useTerminalStore();

// 当前正在操作的 Beacon ID
const beaconId = computed(() => route.params.id as string);

// 从 Store 中响应式获取数据
const ctx = computed(() => fileStore.getContext(beaconId.value));
const currentPath = computed(() => ctx.value.path);
const files = computed(() => ctx.value.files);

// 加载状态直接用 terminalStore 的状态（或者在 fileStore 里加一个也行）
const isLoading = computed(() => terminalStore.isSending[beaconId.value]);

// ---------------------------------------------------------
// 行为逻辑
// ---------------------------------------------------------
const refresh = () => fileStore.refreshDirectory(beaconId.value);

const jumpToPath = (path: string) => fileStore.refreshDirectory(beaconId.value, path);

const handleItemClick = async (file: any) => {
  // 如果是文件夹，执行“跳转”逻辑
  if (file.IsFolder) {
    const separator = currentPath.value.endsWith('\\') ? '' : '\\';
    const newPath = `${currentPath.value}${separator}${file.Name}`;
    await fileStore.refreshDirectory(beaconId.value, newPath);
  }
  // 如果是文件，执行“下载”逻辑
  else {
    await downloadFile(file);
  }
};


const downloadFile = async (file: any) => {
  const fullPath = `${currentPath.value}${currentPath.value.endsWith('\\') ? '' : '\\'}${file.Name}`;
  await terminalStore.sendCommand(beaconId.value, `download ${fullPath}`);
};


// 面包屑逻辑（保持原样，因为它只依赖于 currentPath）
const breadcrumbs = computed(() => {
  const parts = currentPath.value.split(/[\\/]/).filter(p => p !== '');
  let acc = '';
  return parts.map((part, i) => {
    if (i === 0 && part.includes(':')) acc = part + '\\';
    else acc += (acc.endsWith('\\') ? '' : '\\') + part;
    return { name: part, path: acc };
  });
});


const formatSize = (bytes: number) => {
  if (!bytes && bytes !== 0) return '--';
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  if (bytes === 0) return '0 Byte';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i)) + ' ' + sizes[i];
};



const isEditingPath = ref(false);
const tempPath = ref('');
const pathInput = ref<HTMLInputElement | null>(null);

// 把当前的 currentPath 同步给输入框
const startEditPath = () => {
  tempPath.value = currentPath.value;
  isEditingPath.value = true;
  // 下一帧自动聚焦
  nextTick(() => pathInput.value?.focus());
};

// 调用写好的 jumpToPath
const confirmEditPath = () => {
  if (tempPath.value.trim() && tempPath.value !== currentPath.value) {
    jumpToPath(tempPath.value.trim());
  }
  isEditingPath.value = false;
};

const cancelEditPath = () => {
  isEditingPath.value = false;
};

</script>

<template>
  <div class="flex flex-col h-full bg-gray-900 text-gray-100 font-mono">
    <div class="p-4 border-b border-gray-800 bg-gray-800/50 flex items-center justify-between">
      <div class="flex items-center space-x-2 overflow-x-auto">
        <span class="text-cyan-500 font-bold">PATH:</span>


        <div v-if="!isEditingPath"
             @click="startEditPath"
             class="flex items-center space-x-1 overflow-x-auto cursor-text py-1 px-2 rounded hover:bg-gray-700/50 transition-all flex-1">

        <div v-for="(crumb, index) in breadcrumbs" :key="crumb.path" class="flex items-center flex-shrink-0">
          <button @click="jumpToPath(crumb.path)" class="hover:text-cyan-400 hover:underline transition-all">
            {{ crumb.name }}
          </button>
          <span v-if="index < breadcrumbs.length - 1" class="mx-2 text-gray-600">/</span>
        </div>
        </div>


        <input v-else
               ref="pathInput"
               v-model="tempPath"
               @blur="cancelEditPath"
               @keyup.enter="confirmEditPath"
               class="flex-1 bg-gray-800 border border-cyan-500/50 rounded px-2 py-1 text-gray-100 focus:outline-none focus:border-cyan-400"
        />

      </div>






      <button @click="refresh" :disabled="isLoading" class="p-2 hover:bg-gray-700 rounded-full transition-colors">
        <span :class="{'animate-spin inline-block': isLoading}">🔄</span>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 relative">
      <div v-if="isLoading" class="absolute inset-0 bg-gray-900/60 flex items-center justify-center z-10">
        <div class="text-cyan-500 animate-pulse">Waiting for Beacon response...</div>
      </div>

      <table class="w-full text-left">
        <thead>
        <tr class="text-gray-500 border-b border-gray-800 text-xs uppercase tracking-wider">
          <th class="pb-3 pl-2">Name</th>
          <th class="pb-3">Size</th>
          <th class="pb-3">Last Modified</th>
        </tr>
        </thead>
        <tbody class="text-sm">
        <tr v-for="file in files" :key="file.Name"
            @dblclick="handleItemClick(file)"
            class="group hover:bg-gray-800/50 cursor-pointer border-b border-gray-800/30 transition-colors">
          <td class="py-3 pl-2 flex items-center space-x-3">
            <span v-if="file.IsFolder" class="text-yellow-500">📁</span>
            <span v-else class="text-blue-400">📄</span>
            <span class="group-hover:text-cyan-400">{{ file.Name }}</span>
          </td>
          <td class="py-3 text-gray-400">
            {{ file.Extension === '' || file.Extension === null ? '--' : formatSize(file.Length) }}
          </td>
          <td class="py-3 text-gray-500 text-xs">
            {{ file.LastWriteTime }}
          </td>
        </tr>
        </tbody>
      </table>

      <div v-if="files.length === 0 && !isLoading" class="text-center py-20 text-gray-600">
        This directory is empty or inaccessible.
      </div>
    </div>
  </div>
</template>

<style scoped>
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #2d3748;
  border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
  background: #4a5568;
}
</style>