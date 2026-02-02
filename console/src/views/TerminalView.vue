<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useTerminalStore } from '@/stores/terminalStore';
import { useBeaconStore } from '@/stores/beaconStore';

const route = useRoute();
const terminalStore = useTerminalStore();
const beaconStore = useBeaconStore();
const historyIndex = ref(-1);
const beaconId = route.params.id as string;
const commandInput = ref('');
const scrollContainer = ref<HTMLElement | null>(null);
const localHistory = ref<string[]>([]);
const currentBeacon = computed(() =>
    beaconStore.beacons.find(b => b.id === beaconId)
);

const logs = computed(() => terminalStore.getLogs(beaconId));

const scrollToBottom = async () => {
  await nextTick();
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
  }
};

const handleSend = async () => {
  const fullCommand = commandInput.value.trim();


  if (!fullCommand || terminalStore.isSending[beaconId]) return;

  // 存入本地键盘历史
  localHistory.value.push(fullCommand);
  historyIndex.value = -1;
  commandInput.value = '';

  // 解析指令
  const parts = fullCommand.split(/\s+/);
  const cmd = parts[0].toLowerCase();
  // const args = parts.slice(1).join(' ');

  if(currentBeacon.value?.status != 'active'){
    terminalStore.addLog(beaconId,{
      type: 'error',
      fullCommand: fullCommand,
      content:`Beacon is fucking dead or staling, don't waste time.`,
      timestamp: new Date().toLocaleTimeString()
    })
    return;
  }


  if(!terminalStore.supportCommands.includes(cmd)) {
    terminalStore.addLog(beaconId,{
      type: 'error',
      fullCommand: fullCommand,
      content:`CRITICAL: Execution failed. Instruction '${cmd}' is undefined in Grimoire Protocol.Please input 'help' to get help.`,
      timestamp: new Date().toLocaleTimeString()
    })
    return;
  }

  // 进入分发逻辑
  switch (cmd) {
    case 'help':
      terminalStore.displayHelp(beaconId);
      break;

    case 'clear':
      // 本地逻辑：清空当前屏幕日志
      terminalStore.clearLogs(beaconId);
      break;

    case 'task_history':
      // 即时查询逻辑：不走任务创建，直接查后端历史路由
      await terminalStore.fetchHistory(beaconId);
      break;

    case 'history':
      // 本地逻辑：显示本次会话的输入历史
      terminalStore.displayLocalHistory(beaconId, localHistory.value);
      break;

    case 'whoami':
      terminalStore.addLog(beaconId, {
        type: 'system',
        fullCommand: 'whoami',
        content: currentBeacon.value.user,
        timestamp: new Date().toLocaleTimeString()
        });
      break;

    case 'christmas':
      terminalStore.merryChristmas(beaconId);
      break;

    default:
      // 远程任务逻辑：走 /task/create 流程
      await terminalStore.sendCommand(beaconId, fullCommand);
      break;
  }

  scrollToBottom();
};

const handleKeyDown = (e: KeyboardEvent) => {
  // 如果历史记录是空的，直接返回
  if (localHistory.value.length === 0) return;

  if (e.key === 'ArrowUp') {
    // 阻止光标乱跳
    e.preventDefault();

    if (historyIndex.value === -1) {
      // 第一次按上，跳到最后一条
      historyIndex.value = localHistory.value.length - 1;
    } else if (historyIndex.value > 0) {
      // 继续往上翻
      historyIndex.value--;
    }
    commandInput.value = localHistory.value[historyIndex.value];
  }

  else if (e.key === 'ArrowDown') {
    e.preventDefault();

    if (historyIndex.value !== -1) {
      if (historyIndex.value < localHistory.value.length - 1) {
        // 往下翻
        historyIndex.value++;
        commandInput.value = localHistory.value[historyIndex.value];
      } else {
        // 翻到头了，清空输入框
        historyIndex.value = -1;
        commandInput.value = '';
      }
    }
  }
};





onMounted(() => {
  // 模拟终端开启时的系统提示
  if (logs.value.length === 0) {
    terminalStore.addLog(beaconId, {
      type: 'system',
      fullCommand: 'beginTerminal',
      content: `
   ______  ____   _____   __  ___  ____   _____  ____    _____
  / ____/ / __ \\ /_  _/  /  |/  / / __ \\ /_  _/ / __ \\  /____/
 / / __  / /_/ /  / /   / /|_/ / / / / /  / /  / /_/ / / /__/
/ /_/ / / _, _/ _/ /_  / /  / / / /_/ / _/ /_ / _, _/ / /___
\\____/ /_/ |_/ /____/ /_/  /_/  \\____/ /____//_/ |_/  \\_____/

> SYSTEM: GRIMOIRE C2 KERNEL 2.4.0-STABLE
> CONNECTION: ESTABLISHED VIA AES-256-GCM
> TARGET_ID: ${beaconId}
> STATUS: SESSION_ACTIVE
      `,
      timestamp: new Date().toLocaleTimeString()
    });
  }
  scrollToBottom();
});
</script>

<template>
  <div class="terminal-container flex flex-col h-[calc(100vh-100px)] bg-black overflow-hidden rounded-lg border border-cyan-900/50 relative">

    <div class="crt-overlay pointer-events-none absolute inset-0 z-10"></div>
    <div class="scanline pointer-events-none absolute inset-0 z-10"></div>

    <div class="z-20 flex items-center justify-between bg-cyan-950/30 px-4 py-2 border-b border-cyan-900/50 backdrop-blur-sm">
      <div class="flex items-center space-x-3 text-xs font-mono">
        <span class="text-cyan-500 animate-pulse">●</span>
        <span class="text-cyan-400 font-bold tracking-widest uppercase">Console_Session: {{ beaconId.slice(0, 8) }}</span>
        <span class="text-cyan-800">|</span>
        <span class="text-cyan-600">Arch: x64</span>
        <span class="text-cyan-600">OS: Windows_NT</span>
      </div>
      <div class="flex space-x-2">
        <div class="w-3 h-3 rounded-full bg-red-900/50 border border-red-700"></div>
        <div class="w-3 h-3 rounded-full bg-yellow-900/50 border border-yellow-700"></div>
        <div class="w-3 h-3 rounded-full bg-green-900/50 border border-green-700"></div>
      </div>
    </div>

    <div
        ref="scrollContainer"
        class="z-0 flex-1 p-6 font-mono text-sm overflow-y-auto scrollbar-custom relative"
    >
      <div v-for="(log, index) in logs" :key="index" class="mb-3 leading-relaxed">
        <span class="text-cyan-500">[{{ log.timestamp }}]:{{log.fullCommand}}</span>
        <div v-if="log.type === 'system'" class="text-cyan-700 whitespace-pre font-bold leading-none mb-4 opacity-80">
          {{ log.content }}
        </div>

        <div v-else class="flex flex-col">
          <div class="flex items-center space-x-2 opacity-50 text-[10px]">
            <span v-if="log.type === 'input'" class="text-white">OPERATOR_REQ</span>
            <span v-else-if="log.type === 'output'" class="text-green-500">BEACON_RESP</span>
          </div>

          <div
              :class="{
              'text-cyan-400 glow-text': log.type === 'input',
              'text-green-400/90 whitespace-pre-wrap mt-1': log.type === 'output',
              'text-red-500 font-bold mt-1 bg-red-950/20 p-2 border-l-2 border-red-500': log.type === 'error',
              'text-green-400 whitespace-pre glow-text-green mt-1 p-4 bg-green-950/10 border-l-2 border-yellow-500 italic shadow-[0_0_15px_rgba(34,197,94,0.2)]': log.type === 'easter-egg'
            }"
          >
            {{ log.content }}
          </div>
        </div>
      </div>

      <div v-if="terminalStore.isSending[beaconId]" class="flex items-center space-x-2 text-cyan-600 italic">
        <span class="inline-block w-2 h-4 bg-cyan-600 animate-blink"></span>
        <span>Awaiting encrypted response...</span>
      </div>
    </div>

    <div class="bg-gray-900 border-t border-cyan-900/50 p-4">
      <div class="flex items-center group">

      /* 这里第一次isSending其实是null，不过是null也不影响使用，因为当第一次输入指令的时候，就有了 */
      <span :class="terminalStore.isSending[beaconId] ? 'text-gray-600' : 'text-cyan-500'" class="font-bold mr-3">
        {{ currentBeacon?.user || 'operator' }}@grimoire:~$
      </span>

        <input
            v-model="commandInput"
            @keyup.enter="handleSend"
            @keydown="handleKeyDown"
            type="text"
            spellcheck="false"

        :disabled="terminalStore.isSending[beaconId]"

        :placeholder="terminalStore.isSending[beaconId] ? 'Awaiting beacon response... Please wait.' : 'Execute system command...'"

        class="flex-1 bg-transparent border-none text-cyan-300 focus:ring-0 placeholder-cyan-900 font-mono disabled:cursor-not-allowed disabled:text-gray-600"
        autofocus
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* CRT 扫描线动画 */
.crt-overlay {
  background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%),
  linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
  background-size: 100% 3px, 3px 100%;
}

.scanline {
  width: 100%;
  height: 2px;
  background: rgba(0, 255, 255, 0.04);
  opacity: 0.75;
  animation: scanline 6s linear infinite;
}

@keyframes scanline {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(1000%); }
}

/* 文本发光效果 */
.glow-text {
  text-shadow: 0 0 5px rgba(34, 211, 238, 0.5);
}

/* 光标闪烁 */
.animate-blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* 自定义滚动条 - 这种深蓝窄条最帅 */
.scrollbar-custom::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-custom::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.3);
}
.scrollbar-custom::-webkit-scrollbar-thumb {
  background: rgba(6, 182, 212, 0.2);
  border-radius: 10px;
}
.scrollbar-custom::-webkit-scrollbar-thumb:hover {
  background: rgba(6, 182, 212, 0.5);
}
</style>