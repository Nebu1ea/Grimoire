// src/stores/beaconStore.ts

import { defineStore } from 'pinia';
import apiClient from '@/utils/http';

// 定义 Beacon 数据的 TypeScript 接口
export interface Beacon {
    id: string; // Beacon 的唯一标识符
    user: string; // 用户
    os: string;   //主机系统
    ip_address: string; // 外部 IP 或主机地址
    last_checkin: number; // 最后心跳时间戳（Unix 时间，秒）
    status: 'active' | 'dead' | 'stale'; // 状态
}

export const useBeaconStore = defineStore('beacon', {
    state: () => ({
        // 存储所有 Beacon 对象的数组
        beacons: [] as Beacon[],
        // 当前操作员选中的 Beacon ID
        selectedBeaconId: null as string | null,
        // 加载状态
        isLoading: false,
        // 轮询句柄，用于停止或重启
        pollingInterval: null as number | null,
    }),

    getters: {
        // 获取当前选中的 Beacon 对象
        selectedBeacon: (state): Beacon | null => {
            return state.beacons.find(b => b.id === state.selectedBeaconId) || null;
        },
        // 获取活跃 Beacon 的数量
        activeCount: (state): number => {
            return state.beacons.filter(b => b.status === 'active').length;
        },
        // 将时间戳转换为可读的日期字符串 (用于 Lobby 列表)
        formattedBeacons: (state) => {
            return state.beacons.map(beacon => ({
                ...beacon,
                display_checkin: new Date(beacon.last_checkin * 1000).toLocaleString(),
            }));
        },
    },

    actions: {
        // 从后端获取 Beacon 列表
        async fetchBeacons() {
            if (this.isLoading) return;
            this.isLoading = true;
            try {
                // 使用配置好的 apiClient 发起请求
                const response = await apiClient.get('/operator/beacons');

                // 更新状态
                this.beacons = response.data.map((b: any) => ({
                    ...b,
                    status: b.status.toLowerCase(),
                }));
            } catch (error) {
                console.error('Failed to fetch beacons:', error);
            } finally {
                this.isLoading = false;
            }
        },

        // 设置轮询，每 5 秒更新一次状态
        startPolling() {
            if (this.pollingInterval !== null) {
                clearInterval(this.pollingInterval);
            }
            this.fetchBeacons(); // 立即执行一次
            this.pollingInterval = setInterval(() => {
                this.fetchBeacons();
            }, 5000); // 每 5000 毫秒（5 秒）轮询一次
        },

        stopPolling() {
            if (this.pollingInterval !== null) {
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
            }
        },

        // 选择一个 Beacon 进行交互
        selectBeacon(id: string) {
            this.selectedBeaconId = id;
        }
    }
});