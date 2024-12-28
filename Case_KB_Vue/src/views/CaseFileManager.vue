<!--
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-26 16:34:15
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-26 16:34:21
 * @FilePath: \Case_KB\templates\Show.vue
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
<template>
  <div>
    <h1>案例管理系统</h1>
    <div class="container">
      <!-- 这里是你原有的 show.html 内容 -->
      <div class="row">
        <div class="col-md-3">
          <!-- 左侧内容 -->
          <div class="card mb-4">
            <div class="card-body">
              <h5 class="card-title">当前状态</h5>
              <p class="card-text">
                分类层级文件: {{ hierarchyExists ? '已存在' : '未创建' }}<br>
                案例文件: {{ casesExists ? '已存在' : '未创建' }}
              </p>
            </div>
          </div>
          <!-- 其他内容 -->
        </div>
        <div class="col-md-9">
          <!-- 右侧内容 -->
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="card-title mb-0">邮件文件列表</h5>
            </div>
            <div class="card-body" style="max-height: 600px; overflow-y: auto;">
              <div v-if="emailFiles.length">
                <div class="list-group">
                  <div v-for="file in sortedEmailFiles" :key="file.name" class="list-group-item" :class="{ processed: file.processed }">
                    <div class="d-flex flex-column">
                      <div class="d-flex align-items-center mb-2">
                        <span class="me-3">{{ file.name.replace('.pdf', '') }}</span>
                        <span class="badge" :class="file.processed ? 'bg-success' : 'bg-warning'">
                          {{ file.processed ? '已处理' : '未处理' }}
                        </span>
                      </div>
                      <div v-if="file.processed" class="category-editor" :data-file="file.name">
                        <div class="row g-2">
                          <div class="col-md-4">
                            <div class="input-group input-group-sm mb-2">
                              <span class="input-group-text w-100px">一级分类</span>
                              <input type="text" class="form-control category-input" v-model="file.categories.level1" :disabled="isDisabled(file, 'level1')">
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="text-muted text-center my-5">暂无邮件文件</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      emailFiles: [], // 需要从后端获取邮件文件列表
      hierarchyExists: false, // 需要根据实际情况设置
      casesExists: false // 需要根据实际情况设置
    };
  },
  computed: {
    sortedEmailFiles() {
      return this.emailFiles.sort((a, b) => a.processed - b.processed);
    }
  },
  methods: {
    isDisabled(file, level) {
      return file.confidence && file.confidence[level] >= 0.8;
    }
  }
};
</script>

<style scoped>
/* 添加样式 */
</style> 