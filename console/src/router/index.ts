// src/router/index.ts

import { createRouter, createWebHistory } from 'vue-router';
const base = (typeof import.meta.env !== 'undefined' && import.meta.env.BASE_URL) ? import.meta.env.BASE_URL : '/';
// 定义应用路由
const router = createRouter({
    history: createWebHistory(base),
    routes: [
        {
            path: '/login',
            name: 'Login',
            component: () => import('../views/LoginView.vue'),
            meta: { requiresAuth: false }
        },
        {
            path: '/',
            name: 'Lobby',
            component: () => import('../views/LobbyView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/terminal/:id',
            name: 'Terminal',
            component: () => import('../views/TerminalView.vue'),
            meta: { requiresAuth: true }
        },
    ],
});


// 路由导航守卫,每次访问前先获取auth_toke在，存在则继续，不然跳转登录
router.beforeEach((to, from, next) => {
    if (to.meta.requiresAuth) {
        const isAuthenticated = !!localStorage.getItem('auth_token');

        if (isAuthenticated) {
            next();
        } else {
            next({ name: 'Login' });
        }
    } else {
        next();
    }
});

// 导出 router 实例
export default router;