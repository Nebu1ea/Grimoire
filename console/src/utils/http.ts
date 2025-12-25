// src/utils/http.ts
import axios, {type AxiosInstance } from 'axios';

// 从 Vite 环境变量中读取 API 基础 URL，如果未设置则默认为 /api
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 5000, // 5秒超时
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器：在发送请求前添加认证 Token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
            // 在 Header 中设置 Bearer Token
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 响应拦截器：集中处理全局错误
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // 统一处理 401 (未认证) 错误
        if (error.response && error.response.status === 401) {
            console.error('认证失败，Token 无效或过期。');
            // 清除 token 并跳转到登录页
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default apiClient;