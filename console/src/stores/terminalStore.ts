import { defineStore } from 'pinia';
import apiClient from '@/utils/http';

interface LogEntry {
    type: 'input' | 'output' | 'error' | 'system' | 'easter-egg';
    fullCommand: string;
    content: string;
    timestamp: string;
    isHtml: boolean;
}

export const useTerminalStore = defineStore('terminal', {
    state: () => ({
        logsMap: {} as Record<string, LogEntry[]>,
        // isSending: false,
        isSending: {} as Record<string, boolean>,
        supportCommands: ['clear', 'shell', 'history', 'whoami', 'powershell', 'screenshot', 'task_history', 'download', 'help', 'christmas']
    }),

    actions: {
        // 工具函数：延迟
        sleep(ms: number) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        isSendingTrue(beaconId: string) {
          if (!this.isSending[beaconId]) {
              this.isSending[beaconId] = true;
          }
          this.isSending[beaconId] = true;
        },

        clearSending(beaconId: string) {
            if (!this.isSending[beaconId]) {
                this.isSending[beaconId] = false;
            }
            this.isSending[beaconId] = false;
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
                    "  screenshot      Fetch remote desktop screenshot\n" +
                    "  download [path] Download Path File\n"+
                    "---------------------------------------------------------\n" +
                    "  Tip: Use UP/DOWN arrows to navigate command history.\n"+
                    "  Easter Egg Command       ??? Go and find them~~???\n",
                timestamp: new Date().toLocaleTimeString(),
                isHtml: false,
            });
        },

        // 显示本地输入历史 (本地)
        displayLocalHistory(beaconId: string, history: string[]) {
            this.addLog(beaconId, {
                type: 'system',
                fullCommand: 'history',
                content: "--- LOCAL COMMAND HISTORY ---\n" + history.join('\n'),
                timestamp: new Date().toLocaleTimeString(),
                isHtml: false,
            });
        },

        //发送命令并轮询结果
        async sendCommand(beaconId: string, fullCommand: string) {
            this.isSendingTrue(beaconId);

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
                isHtml: false
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
                    isHtml: false
                });

                // 开始轮询结果
                let output = null;
                let attempts = 0;
                const maxAttempts = 30; // 最多轮询 30 次 (约 1 分钟)

                while (!output && attempts < maxAttempts) {
                    attempts++;

                    const outputRes = await apiClient.get(`/operator/task/output/${taskId}`);

                    // 假设后端在没结果时返回空字符串或特定的状态码
                    if (outputRes.data && outputRes.data.output_content) {
                        output = outputRes.data.output_content;
                    } else {
                        // 每 2 秒查一次
                        await this.sleep(2000);
                    }
                }

                // 展示结果
                if (output) {
                    const binStr = window.atob(output);
                    const bytes = new Uint8Array(binStr.length);
                    for (let i = 0; i < binStr.length; i++) {
                        bytes[i] = binStr.charCodeAt(i);
                    }

                    if (command === "download") {
                        const contentBase64 = window.atob(output);

                        // 触发下载
                        const fileName = args.split(/[\\/]/).pop()?.replace(/"/g, '') || 'file';
                        const link = document.createElement('a');
                        link.href = `data:application/octet-stream;base64,${contentBase64.replace(/\s/g, '')}`;
                        link.download = fileName;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);

                        this.addLog(beaconId, {
                            type: 'system',
                            content: `[*] File [${fileName}] downloaded successfully.`,
                            fullCommand: fullCommand,
                            timestamp: new Date().toLocaleTimeString(),
                            isHtml: false
                        });

                        return contentBase64;
                    }


                    if (command === "screenshot") {
                        // 第一层拆包：拿到内部的 Base64 图片内容
                        const imgBase64 = window.atob(output);


                        const imgTag = `<img src="data:image/jpeg;base64,${imgBase64.replace(/\s/g, '')}" 
                             style="max-width: 100%; border: 2px solid #00ff00; margin-top: 10px;" 
                             onload="console.log('Screenshot rendered!')" />`;

                        // 直接在日志里展示
                        this.addLog(beaconId, {
                            type: 'output',
                            content: imgTag,
                            fullCommand: fullCommand,
                            timestamp: new Date().toLocaleTimeString(),
                            isHtml: true
                        });
                        return imgBase64;
                    }

                    let decodedOutput = new TextDecoder('utf-8').decode(bytes);


                    this.addLog(beaconId, {
                        type: 'output',
                        content: decodedOutput,
                        fullCommand: fullCommand,
                        timestamp: new Date().toLocaleTimeString(),
                        isHtml: false
                    });

                    // 这里的 return 依然保留，如果是 download
                    return decodedOutput;
                } else {
                    this.addLog(beaconId, {
                        type: 'error',
                        fullCommand: fullCommand,
                        content: `[!] Task ${taskId} timed out or returned no output.`,
                        timestamp: new Date().toLocaleTimeString(),
                        isHtml: false
                    });
                    return null;
                }

            } catch (error: any) {
                this.addLog(beaconId, {
                    type: 'error',
                    fullCommand: fullCommand,
                    content: `[!] Error: ${error.response?.data?.msg || 'Communication failed'}`,
                    timestamp: new Date().toLocaleTimeString(),
                    isHtml: false
                });
                return null;
            } finally {
                this.isSending[beaconId] = false;
            }
        },


        async fetchHistory(beaconId: string) {
            this.isSendingTrue(beaconId); // 复用加载状态，让终端显示正在查询
            try {
                const response = await apiClient.get(`/operator/task/history/${beaconId}`);
                const data = response.data;

                this.addLog(beaconId, {
                    type: 'system',
                    fullCommand: 'task_history',
                    content: `[*] Syncing historical tasks for ${beaconId}...`,
                    timestamp: new Date().toLocaleTimeString(),
                    isHtml: false
                });

                // 解析返回的 JSON 并渲染到终端
                Object.entries(data).forEach(([tid, task]: [string, any]) => {
                    this.addLog(beaconId, {
                        type: 'output',
                        fullCommand: 'task_history',
                        content: `[TASK ${tid}] ${task.command}: ${task.result || 'No output'}`,
                        timestamp: task.timestamp,
                        isHtml: false
                    });
                });
            } catch (error) {
                this.addLog(beaconId, { type: 'error', fullCommand: 'task_history', content: 'Failed to fetch history.', timestamp: '' , isHtml: false });
            } finally {
                this.clearSending(beaconId);
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
                isHtml: false
            });
        },

    }
});