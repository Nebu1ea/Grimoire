<script setup lang="ts">
import { ref } from 'vue';
import { useAuthStore } from '@/stores/authStore';

const authStore = useAuthStore();

// 表单响应式数据
const username = ref('');
const password = ref('');

// 处理表单提交
const handleLogin = async () => {
  // 触发 Store 中的 login action
  await authStore.login(username.value, password.value);
};
</script>

<template>
  <div class="flex items-center justify-center min-h-screen bg-gray-950">
    <div class="w-full max-w-md p-8 space-y-6 bg-gray-800 rounded-xl shadow-2xl border border-cyan-700/50">

      <h2 class="text-3xl font-extrabold text-center text-cyan-400 font-mono">
        GRIMOIRE C2 Console
      </h2>
      <p class="text-center text-gray-400">操作员登录</p>

      <form @submit.prevent="handleLogin" class="space-y-4">

        <div>
          <label for="username" class="block text-sm font-medium text-gray-300">用户名 (Username)</label>
          <input
              id="username"
              name="username"
              type="text"
              required
              v-model="username"
              :disabled="authStore.isLoading"
              class="w-full px-4 py-2 mt-1 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-cyan-500 focus:border-cyan-500"
              placeholder="请输入操作员名称"
          />
        </div>

        <div>
          <label for="password" class="block text-sm font-medium text-gray-300">密码 (Password)</label>
          <input
              id="password"
              name="password"
              type="password"
              required
              v-model="password"
              :disabled="authStore.isLoading"
              class="w-full px-4 py-2 mt-1 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-cyan-500 focus:border-cyan-500"
              placeholder="请输入密码"
          />
        </div>

        <div v-if="authStore.loginError" class="text-sm p-2 bg-red-900/50 border border-red-700 rounded-lg text-red-300">
          {{ authStore.loginError }}
        </div>

        <div>
          <button
              type="submit"
              :disabled="authStore.isLoading"
              class="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white transition-colors duration-200"
              :class="{
                'bg-cyan-600 hover:bg-cyan-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500': !authStore.isLoading,
                'bg-gray-500 cursor-not-allowed': authStore.isLoading
            }"
          >
            <span v-if="authStore.isLoading">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              正在连接...
            </span>
            <span v-else>
              登录控制台 (Login)
            </span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>