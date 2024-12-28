<!--
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-27 10:15:02
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-27 11:09:02
 * @FilePath: \Case_KB_Vue\src\App.vue
 * @Description: Case-KB Vue 项目的根组件
-->
<template>
  <div id="app">
    <!-- 导航栏 -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container-fluid">
        <router-link class="navbar-brand" to="/">Case-KB</router-link>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <router-link class="nav-link" to="/case-manager">案例管理</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/email-generator">邮件生成</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/email-classification">案例分类</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/audit-manager">案例审核</router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- Flash 消息 -->
    <div class="container mt-3">
      <div v-for="(message, index) in messages" 
           :key="index"
           :class="['alert', `alert-${message.category}`, 'alert-dismissible', 'fade', 'show']">
        {{ message.text }}
        <button type="button" class="btn-close" @click="removeMessage(index)"></button>
      </div>
    </div>

    <!-- 主要内容 -->
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      messages: []
    }
  },
  methods: {
    addMessage(text, category = 'info') {
      this.messages.push({ text, category });
      setTimeout(() => this.removeMessage(this.messages.length - 1), 5000);
    },
    removeMessage(index) {
      this.messages.splice(index, 1);
    }
  }
}
</script>

<style>
#app {
  font-family: Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 导航栏样式 */
.navbar {
  margin-bottom: 20px;
}

.navbar-nav .nav-link {
  color: rgba(255, 255, 255, 0.85) !important;
}

.navbar-nav .nav-link.router-link-active {
  color: #fff !important;
  font-weight: bold;
}

/* 消息提示样式 */
.alert {
  margin-bottom: 1rem;
}

/* 通用样式 */
.badge {
  font-size: 0.9em;
  padding: 0.4em 0.8em;
}

pre {
  margin: 0;
}

code {
  white-space: pre-wrap;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .container {
    padding: 0 15px;
  }
}
</style> 