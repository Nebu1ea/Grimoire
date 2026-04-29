// src/main.ts

import { createApp } from 'vue';
import { createPinia } from 'pinia';
// 导入新创建的 router 实例
import router from './router';

import App from './App.vue';
import './assets/main.css';

const app = createApp(App);
const pinia = createPinia();


app.use(pinia);
app.use(router);

app.mount('#app');