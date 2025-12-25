// src/stores/authStore.ts

import { defineStore } from 'pinia';
import apiClient from '@/utils/http';
import router from '@/router';


export const useAuthStore = defineStore('auth', {
    state: () => ({
        // 存储 JWT Token
        authToken: localStorage.getItem('auth_token') as string | null,
        // 用户名
        username: localStorage.getItem('username') as string | null,
        // 登录过程中的加载状态
        isLoading: false,
        // 登录错误信息
        loginError: null as string | null,
    }),

    getters: {
        // 检查用户是否已登录（Token 是否存在）
        isAuthenticated: (state): boolean => !!state.authToken,
    },

    actions: {
        /**
         * @description 处理登录请求，并存储返回的 JWT Token
         */
        async login(username: string, password: string): Promise<void> {
            this.isLoading = true;
            this.loginError = null; // 清除之前的错误

            try {
                const response = await apiClient.post('/auth/login', {
                    username: username,
                    password: password,
                });

                const token = response.data.access_token;

                // 更新 Pinia 状态
                this.authToken = token;
                this.username = username;

                // 持久化存储,浏览器关闭后仍然保持登录
                localStorage.setItem('auth_token', token);
                localStorage.setItem('username', username);

                // 登录成功，跳转到 Lobby 界面
                router.push({ name: 'Lobby' });

            } catch (error: any) {
                console.error('Login failed:', error);

                // 处理 401 或其他网络错误
                if (error.response && error.response.status === 401) {
                    this.loginError = '用户名或密码错误，请重试。';
                } else {
                    this.loginError = '网络连接失败或服务器错误。';
                }
                this.authToken = null; // 清除 Token
                localStorage.removeItem('auth_token');

            } finally {
                this.isLoading = false;
            }
        },

        /**
         * @description 注销用户，清除 Token，并跳转到登录页
         */
        logout(): void {
            this.authToken = null;
            this.username = null;
            localStorage.removeItem('auth_token');
            localStorage.removeItem('username');

            // 跳转到登录页
            router.push({ name: 'Login' });
        }
    }
});