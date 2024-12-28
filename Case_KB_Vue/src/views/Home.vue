<!--
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-27 11:55:10
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-27 11:25:41
 * @FilePath: \Case_KB_Vue\src\views\Home.vue
 * @Description: 首页组件
-->
<template>
  <base-layout>
    <div class="container mt-4">
      <!-- 用户界面部分 -->
      <div class="section mb-5">
        <h2 class="border-bottom pb-2">用户界面</h2>
        <div class="row mt-4">
          <div class="col-md-6 offset-md-3">
            <div class="card">
              <div class="card-body">
                <h5 class="card-title">主界面</h5>
                <p class="card-text">进入系统主界面，查看和处理案例信息。</p>
                <router-link to="/show" class="btn btn-primary w-100">进入主界面</router-link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 管理员界面部分 -->
      <div class="section">
        <h2 class="border-bottom pb-2">管理员界面</h2>
        <div class="row mt-4">
          <div class="col-md-4" v-for="(item, index) in adminMenus" :key="index">
            <div class="card h-100">
              <div class="card-body d-flex flex-column">
                <h5 class="card-title">{{ item.title }}</h5>
                <p class="card-text flex-grow-1">{{ item.description }}</p>
                <router-link :to="item.route" class="btn btn-primary">{{ item.buttonText }}</router-link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </base-layout>
</template>

<script>
import BaseLayout from '@/layouts/BaseLayout.vue'

export default {
  name: 'Home',
  components: {
    BaseLayout
  },
  data() {
    return {
      adminMenus: [
        {
          title: '第一步:案例分类',
          description: '按案例进行结构分类和管理。',
          route: '/email-classification',
          buttonText: 'Case分类管理'
        },
        {
          title: '第二步:案例管理',
          description: '案例库的构建与更新。',
          route: '/case-manager',
          buttonText: '进入案例管理'
        },
        {
          title: '第三步:案例审核',
          description: '审核和修正案例的结构分类结果。',
          route: '/audit-manager',
          buttonText: '进入审核'
        }
      ]
    }
  }
}
</script>

<style scoped>
.section {
  background-color: #f8f9fa;
  padding: 2rem;
  border-radius: 0.5rem;
  margin-bottom: 2rem;
}

.card {
  transition: transform 0.2s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 1rem;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.card-body {
  padding: 1.5rem;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.btn-primary {
  margin-top: auto;
}

h2 {
  color: #2c3e50;
  margin-bottom: 1rem;
}

.card-title {
  color: #34495e;
  font-weight: 600;
}

.card-text {
  color: #7f8c8d;
  margin-bottom: 1rem;
}

.row {
  margin: 0 -0.5rem;
}

.col-md-4 {
  padding: 0 0.5rem;
}
</style> 