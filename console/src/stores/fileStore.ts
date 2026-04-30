import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useTerminalStore } from './terminalStore';

export const useFileStore = defineStore('file', () => {
    const terminalStore = useTerminalStore();

    // 每个 Beacon 都有自己的“上下文”（当前路径和文件列表）
    const beaconContexts = ref<Record<string, { path: string, files: any[] }>>({});

    // 获取或初始化某个 Beacon 的上下文
    const getContext = (beaconId: string) => {
        if (!beaconContexts.value[beaconId]) {
            beaconContexts.value[beaconId] = { path: 'C:\\', files: [] };
        }
        return beaconContexts.value[beaconId];
    };

    // 刷新目录
    const refreshDirectory = async (beaconId: string, targetPath?: string) => {
        const ctx = getContext(beaconId);
        // 如果传了新路径就更新，没传就用旧的（刷新当前）
        if (targetPath) ctx.path = targetPath;

        //  PowerShell JSON 指令
        // const psCommand = `powershell Get-ChildItem -Path "${ctx.path}" | Select-Object Name, Length, LastWriteTime, @{n='Extension';e={$_.Extension}} | ConvertTo-Json`;

        const psCommand = `powershell $ProgressPreference = 'SilentlyContinue'; $items = Get-ChildItem -Path '${ctx.path}' | Select-Object Name, Length, @{n='LastWriteTime';e={$_.LastWriteTime.ToString('yyyy/MM/dd HH:mm:ss')}}, @{n='IsFolder';e={$_.PSIsContainer}}; if ($items) { $items | ConvertTo-Json } else { '[]' }`;
        // 调用 sendCommand
        const result = await terminalStore.sendCommand(beaconId, psCommand);

        if (result) {
            try {
                const parsed = JSON.parse(result);
                // 自动处理 PowerShell 的单对象/数组坑
                ctx.files = Array.isArray(parsed) ? parsed : [parsed];
                return true;
            } catch (e) {
                console.error("解析文件列表失败:", e);
                return false;
            }
        }
        return false;
    };

    return { beaconContexts, getContext, refreshDirectory };


});