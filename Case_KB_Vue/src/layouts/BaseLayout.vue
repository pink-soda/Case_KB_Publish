<!--
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-27 11:17:10
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-27 11:23:21
 * @FilePath: \Case_KB_Vue\src\layouts\BaseLayout.vue
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
<template>
  <div>
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
              <router-link class="nav-link" to="/show">主页面</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/email-classification">案例分类</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/case-manager">案例管理</router-link>
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
           :class="['alert', `alert-${message.type}`, 'alert-dismissible', 'fade', 'show']">
        {{ message.text }}
        <button type="button" class="btn-close" @click="removeMessage(index)"></button>
      </div>
    </div>

    <!-- 主要内容 -->
    <slot></slot>
  </div>
</template>

<script>
export default {
  name: 'BaseLayout',
  data() {
    return {
      messages: []
    }
  },
  methods: {
    addMessage(text, type = 'info') {
      this.messages.push({ text, type });
      setTimeout(() => {
        this.removeMessage(this.messages.length - 1);
      }, 5000);
    },
    removeMessage(index) {
      this.messages.splice(index, 1);
    }
  }
}
</script>

<style>
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
</style> 