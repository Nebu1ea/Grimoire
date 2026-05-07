<script setup lang="ts">
import { ref, computed, nextTick, onUnmounted } from 'vue';
import { useTerminalStore } from '@/stores/terminalStore.ts';
import apiClient from '@/utils/http';
import 'highlight.js/styles/github-dark.css';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/tokyo-night-dark.css';

const md = new MarkdownIt({
  html: true, // 允许 HTML，这样 inner-os 标签才有效
  linkify: true,
  typographer: true,
  breaks: true,
  highlight: function (str, lang) {
    // 自动高亮代码块
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
            hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
            '</code></pre>';
      } catch (__) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
  }
});


const renderGrimoireResponse = (content: string) => {
  if (!content) return '';
  return md.render(content);
};



// --- 状态定义 ---
const isOpen = ref(false);
const input = ref('');
const terminalStore = useTerminalStore();
const sessionBeaconMap = ref<Record<string, string>>({});
const messages = ref<Message[]>([]);

interface Message {
  role: 'user' | 'ai' | 'system';
  content: string;
  tasks?: string;
  results?: string;
  showType?: 'none' | 'tasks' | 'results';
}

// --- 拖拽功能 ---
function useDraggable(initialX: number, initialY: number) {
  const x = ref(initialX);
  const y = ref(initialY);
  const isDragging = ref(false);

  let startX = 0;
  let startY = 0;

  const onMouseMove = (e: MouseEvent) => {
    if (!isDragging.value) return;
    x.value = e.clientX - startX;
    y.value = e.clientY - startY;
  };

  const onMouseUp = () => {
    isDragging.value = false;
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  };

  const onMouseDown = (e: MouseEvent) => {
    e.preventDefault();
    isDragging.value = true;
    startX = e.clientX - x.value;
    startY = e.clientY - y.value;
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  return { x, y, onMouseDown, isDragging };
}

// --- 初始化拖拽实例 ---
// 这里返回的是 Ref，在 template 里会自动解包，不用写 .value
const btnDraggable = useDraggable(window.innerWidth - 80, window.innerHeight - 80);
const winDraggable = useDraggable(window.innerWidth / 2 - 200, 100);

// --- 核心逻辑 ---
const toggleChat = () => {
  // 这里判断的是按钮的拖拽状态
  if (btnDraggable.isDragging.value) return;
  isOpen.value = !isOpen.value;
};

const toggleDetail = (index: number, type: 'tasks' | 'results') => {
  const msg = messages.value[index];
  if (!msg) return;
  msg.showType = (msg.showType === type) ? 'none' : type;
};

const extractTagMappings = (text: string) => {
  const regex = /<(B\d+)>([\s\S]*?)<\/\1>/g;
  const mappings: Record<string, string> = {};
  let match;
  while ((match = regex.exec(text)) !== null) {
    mappings[match[1]] = match[2].trim();
  }
  return mappings;
};

const cleanInputText = (text: string) => {
  return text.replace(/<([^>]+)>([\s\S]*?)<\/\1>/g, ' $1 ');
};

const formatContent = (content: string) => {
  if (!content) return '';
  return md.render(content);
};


// --- API 交互 ---
const sendMessage = async () => {
  if (!input.value.trim()) return;

  const rawInput = input.value;
  // 提取映射并更新
  const newMappings = extractTagMappings(rawInput);
  sessionBeaconMap.value = { ...sessionBeaconMap.value, ...newMappings };

  const cleanedQuery = cleanInputText(rawInput);
  messages.value.push({ role: 'user', content: rawInput });
  input.value = '';

  const aiMsgIndex = messages.value.push({ role: 'ai', content: '', showType: 'none' }) - 1;

  try {
    // --- 获取 Router 的指令 ---
    const adapter1Res = await callAIAdapter1(cleanedQuery);
    console.log(adapter1Res);
    let finalPrompt = cleanedQuery;

    // --- 判断是否为 JSON 任务列表 ---
    let taskList = null;
    try {
      // 只有当它是数组格式的 JSON 时，我们才认为它是任务
      const parsed = JSON.parse(adapter1Res);
      console.log(parsed);
      if (Array.isArray(parsed)) {
        taskList = parsed;
      }
    } catch (e) {
      // 解析失败说明是 [NORMAL_CHAT]
    }

    if (taskList) {
      const results = [];
      for (const task of taskList) {
        // 执行工具函数
        const res = await executeLocalFunction(task, sessionBeaconMap.value);
        results.push({
          action: task.action,
          beacon_id: task.beacon_id,
          output: res
        });
      }

      // 更新消息状态
      messages.value[aiMsgIndex].tasks = JSON.stringify(taskList, null, 2);
      messages.value[aiMsgIndex].results = JSON.stringify(results, null, 2);

      // 构造给大模型的最终 Prompt
      const toolResultsString = results.map(r => `[TOOL]\n${JSON.stringify(r)}`).join('\n\n');
      finalPrompt = `[ROUTER]\n${adapter1Res}\n\n${toolResultsString}`;
    }

    // --- 带着上下文去请求流式回复 ---
    const history = messages.value.slice(0, -2).map(m => ({
      role: m.role === 'ai' ? 'assistant' : 'user',
      content: m.content
    }));

    await streamAIResponse([...history, { role: 'user', content: finalPrompt }], aiMsgIndex);

  } catch (err) {
    messages.value[aiMsgIndex].content = '发生错误';
    console.error(err);
  }
};


const callAIAdapter1 = async (query: string) => {
  try {

    const response = await apiClient.post('/ai/route', { query });

    return response.data.result;
  } catch (err) {
    console.error(">> [Router Error]:", err);
    return "[NORMAL_CHAT]"; // 万一挂了，保命起见走普通聊天模式
  }
};


const chatContainer = ref<HTMLElement | null>(null);

// --- 带节流的自动滚动 ---
let isScrolling = false;
const scrollToBottom = () => {
  if (isScrolling) return;
  isScrolling = true;

  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTo({
        top: chatContainer.value.scrollHeight,
        behavior: 'smooth'
      });
    }
    // 100ms 触发一次滚动
    setTimeout(() => { isScrolling = false; }, 100);
  });
};

// --- 支持标准 SSE 解析的流式优化 ---
const streamAIResponse = async (messagesArray: any[], msgIndex: number) => {
  try {
    const token = localStorage.getItem('auth_token');
    const response = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' ,'Authorization': `Bearer ${token}`},
      body: JSON.stringify({
        model: "Grimoire",
        messages: messagesArray,
        stream: true
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`后端拒绝了请求: ${response.status}`, errorText);
      messages.value[msgIndex].content = `错误 ${response.status}: ${errorText}`;
      return;
    }
    if (!response.body) throw new Error('ReadableStream not supported');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = ''; // 缓存未处理完的数据块

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // 按 SSE 标准的双换行符拆分消息块
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const rawData = line.substring(6);
          if (rawData === '[DONE]') break;

          try {
            const json = JSON.parse(rawData);
            const content = json.content;
            messages.value[msgIndex].content += content;
          } catch (e) {
            // 降级处理纯文本
            messages.value[msgIndex].content += rawData;
          }
          scrollToBottom();
        }
      }
    }
  } catch (err) {
    console.error("Streaming Error:", err);
    messages.value[msgIndex].content += '\n\n [传输中断] 网络罢工了';
  }
};


const executeLocalFunction = async (toolCall: any, beaconMap: Record<string, string>) => {

  const funcName = toolCall.action;

  const beacon_id_short = toolCall.beacon_id;


  const real_beacon_id = beaconMap[beacon_id_short] ?? beacon_id_short ?? "";

  switch (funcName) {
    case 'gettime':
      return getFormattedTime();

    case 'download': {
      const path = toolCall.path;
      return await terminalStore.sendCommand(real_beacon_id, `download ${path}`);
    }

    case 'execute': {
      const command = 'powershell ' + toolCall.command; // 记得这里加个空格，笨蛋！
      return await terminalStore.sendCommand(real_beacon_id, command);
    }

    case 'screenshot': {
      const command = 'screenshot';
      return await terminalStore.sendCommand(real_beacon_id, command);
    }
    default:
      return `未知的指令: ${funcName}`;
  }
};


/**
 * 获取当前时间并格式化
 * 格式示例: 2026-05-03 13:07:05
 */
const getFormattedTime = () => {
  const now = new Date();

  // 使用 Intl 接口，不仅格式严谨，而且执行效率极高
  // 这种 yyyy-MM-dd HH:mm:ss 的结构，对你的模型分析逻辑最友好
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false // 必须是24小时制，模型可分不清上下午
  }).format(now).replace(/\//g, '-'); // 把斜杠换成横杠，看起来更专业
};

</script>

<template>
  <div class="fixed inset-0 pointer-events-none z-50">

    <div
        class="pointer-events-auto cursor-pointer absolute transition-transform active:scale-90"
        :style="{ left: btnDraggable.x.value + 'px', top: btnDraggable.y.value + 'px' }"
        @mousedown="btnDraggable.onMouseDown"
        @click="toggleChat"
    >
      <div class="w-14 h-14 bg-cyan-600 rounded-full shadow-lg shadow-cyan-500/50 flex items-center justify-center border-2 border-cyan-400 group overflow-hidden">
        <img src="" alt="AI" class="w-10 h-10 group-hover:rotate-12 transition-transform">
      </div>
    </div>

    <div
        v-if="isOpen"
        class="pointer-events-auto fixed w-[400px] h-[550px] flex flex-col bg-gray-950 border border-cyan-500/30 rounded-lg shadow-[0_0_20px_rgba(6,182,212,0.2)] overflow-hidden"
        :style="{ left: winDraggable.x.value + 'px', top: winDraggable.y.value + 'px' }"
    >
      <div @mousedown="winDraggable.onMouseDown" class="bg-cyan-950/20 px-4 py-2 flex justify-between items-center border-b border-cyan-500/20 cursor-move select-none">
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 bg-cyan-500 animate-pulse rounded-full"></div>
          <span class="text-[10px] text-cyan-400 font-black uppercase tracking-tighter">Neural Link: Grimoire-v2</span>
        </div>
        <button @click="isOpen = false" class="text-cyan-800 hover:text-cyan-400 transition-colors">✕</button>
      </div>

      <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-4">
        <template v-for="(m, i) in messages" :key="i">
          <div v-if="m.role !== 'system'" :class="m.role === 'ai' ? 'ai-bubble' : 'user-bubble'">

            <div class="flex items-center gap-2 mb-1 opacity-40 text-[10px]" :class="m.role === 'ai' ? 'justify-start' : 'justify-end'">
              <span>>> {{ m.role === 'ai' ? 'GRIMOIRE' : 'GUEST' }}</span>
            </div>

            <div
                class="prose prose-invert prose-cyan max-w-none text-[15px] leading-7 text-gray-100 font-sans"
                style="white-space: pre-wrap; word-break: break-word;"
                v-html="renderGrimoireResponse(m.content)"
            ></div>

            <div v-if="m.tasks" class="mt-3 space-y-2 text-left">
              <div class="flex gap-2" :class="m.role === 'ai' ? 'justify-start' : 'justify-end'">
                <button
                    @click="toggleDetail(i, 'tasks')"
                    class="text-[10px] px-2 py-1 border border-cyan-500/30 rounded hover:bg-cyan-500/20 transition-colors"
                    :class="m.showType === 'tasks' ? 'bg-cyan-500/30 text-white' : 'text-cyan-600'"
                >
                  [ VIEW_TASKS.JSON ]
                </button>
                <button
                    @click="toggleDetail(i, 'results')"
                    class="text-[10px] px-2 py-1 border border-green-500/30 rounded hover:bg-green-500/20 transition-colors"
                    :class="m.showType === 'results' ? 'bg-green-500/30 text-white' : 'text-green-600'"
                >
                  [ EXEC_RESULTS.LOG ]
                </button>
              </div>

              <div v-if="m.showType && m.showType !== 'none'" class="bg-black/60 rounded p-2 border border-white/10 overflow-x-auto">
                <pre class="text-[11px] font-mono text-gray-400"><code>{{ m.showType === 'tasks' ? m.tasks : m.results }}</code></pre>
              </div>
            </div>

          </div>
        </template>
      </div>

      <div class="p-4 bg-black/40 border-t border-cyan-500/10">
        <div class="flex items-center gap-2 bg-gray-900/50 rounded-lg px-3 py-1 border border-cyan-500/20 focus-within:border-cyan-500/50 transition-all">
          <span class="text-cyan-700">$</span>
          <input
              v-model="input"
              @keyup.enter="sendMessage"
              placeholder="Awaiting instructions..."
              class="flex-1 bg-transparent border-none outline-none text-cyan-400 py-2 text-sm"
          >
        </div>
      </div>

    </div>
  </div>
</template>
<style scoped>
.ai-bubble div {
  /* 强制保留换行和空格，且允许自动换行防止溢出 */
  white-space: pre-wrap !important;
  word-wrap: break-word !important;
}
.ai-bubble :deep(code) {
  white-space: pre !important;        /* 内部 code 保持原样 */
  font-family: 'Fira Code', 'Courier New', monospace;
}
.user-bubble {
  @apply border-r-2 border-gray-700/50 pr-3 py-1 text-right;
}
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  @apply bg-cyan-900/50 rounded;
}
/* 深度选择器处理 v-html 里的样式 */
:deep(.inner-os) {
  font-family: 'Inter', sans-serif;
  letter-spacing: 0.02em;
}
</style>