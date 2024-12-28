<!--
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-27 11:34:10
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-27 11:34:59
 * @FilePath: \Case_KB_Vue\src\views\CaseManager.vue
 * @Description: 案例管理组件
-->
<template>
  <base-layout>
    <div class="container">
      <h1 class="text-center">案例库管理</h1>
      
      <div class="cases-display">
        <template v-if="cases.length">
          <div v-for="case_item in cases" 
               :key="case_item.case_id" 
               class="case-item">
            <h3>案例编号: {{ case_item.case_id }}</h3>
            <p>案例标题: {{ case_item.title }}</p>
            <p>所属类别: {{ case_item.category }}</p>
            <p>案例总结: {{ case_item.case_evaluation }}</p>
          </div>
        </template>
        <p v-else class="text-center">当前案例库为空</p>
      </div>
      
      <div id="message" v-if="message" :class="['alert', messageClass]">
        {{ message }}
      </div>
      
      <div class="button-container">
        <button v-if="cases.length === 0"
                class="action-button build-button"
                @click="buildLibrary"
                :disabled="isProcessing">
          <span v-if="isProcessing" class="spinner-border spinner-border-sm me-2"></span>
          {{ isProcessing ? '构建中...' : '构建案例库' }}
        </button>
        <button v-else
                class="action-button update-button"
                @click="updateLibrary"
                :disabled="isProcessing">
          <span v-if="isProcessing" class="spinner-border spinner-border-sm me-2"></span>
          {{ isProcessing ? '更新中...' : '更新案例库' }}
        </button>
      </div>
      
      <!-- 进度条 -->
      <div class="progress-container" v-show="showProgress">
        <div class="progress">
          <div class="progress-bar progress-bar-striped progress-bar-animated"
               role="progressbar"
               :style="{ width: progress + '%' }"
               :aria-valuenow="progress"
               aria-valuemin="0"
               aria-valuemax="100">
          </div>
        </div>
        <div class="progress-text text-center mt-2">{{ progressText }}</div>
      </div>
    </div>
  </base-layout>
</template>

<script>
import BaseLayout from '@/layouts/BaseLayout.vue'

export default {
  name: 'CaseManager',
  components: {
    BaseLayout
  },
  data() {
    return {
      cases: [],
      message: '',
      messageType: '',
      isProcessing: false,
      showProgress: false,
      progress: 0,
      progressText: '',
      progressInterval: null
    }
  },
  computed: {
    messageClass() {
      return {
        'alert-success': this.messageType === 'success',
        'alert-danger': this.messageType === 'error'
      }
    }
  },
  methods: {
    showMessage(message, type = 'success') {
      this.message = message
      this.messageType = type
      setTimeout(() => {
        this.message = ''
        this.messageType = ''
      }, 5000)
    },

    startProgress() {
      this.showProgress = true
      this.progress = 0
      this.progressInterval = setInterval(() => {
        if (this.progress < 90) {
          this.progress += 5
          this.progressText = `正在${this.cases.length === 0 ? '构建' : '更新'}案例库... ${this.progress}%`
        }
      }, 500)
    },

    completeProgress(success = true) {
      clearInterval(this.progressInterval)
      this.progress = 100
      this.progressText = success ? '操作完成' : '操作失败'
      setTimeout(() => {
        this.showProgress = false
        this.progress = 0
        this.progressText = ''
      }, 2000)
    },

    async buildLibrary() {
      if (this.isProcessing) return
      
      this.isProcessing = true
      this.startProgress()

      try {
        const response = await fetch('/case_manager/build_library', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        const data = await response.json()

        this.completeProgress(data.success)
        this.showMessage(data.message, data.success ? 'success' : 'error')
        
        if (data.success) {
          // 重新加载页面以显示新数据
          setTimeout(() => {
            this.loadCases()
          }, 2000)
        }
      } catch (error) {
        this.completeProgress(false)
        this.showMessage('操作失败: ' + error.message, 'error')
      } finally {
        this.isProcessing = false
      }
    },

    async updateLibrary() {
      if (this.isProcessing) return
      
      this.isProcessing = true
      this.startProgress()

      try {
        const response = await fetch('/case_manager/update_library', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        const data = await response.json()

        this.completeProgress(data.success)
        this.showMessage(data.message, data.success ? 'success' : 'error')
        
        if (data.success) {
          // 重新加载页面以显示更新后的数据
          setTimeout(() => {
            this.loadCases()
          }, 2000)
        }
      } catch (error) {
        this.completeProgress(false)
        this.showMessage('操作失败: ' + error.message, 'error')
      } finally {
        this.isProcessing = false
      }
    },

    async loadCases() {
      try {
        const response = await fetch('/case_manager/get_cases')
        const data = await response.json()
        this.cases = data.cases || []
      } catch (error) {
        console.error('加载案例失败:', error)
        this.showMessage('加载案例失败: ' + error.message, 'error')
      }
    }
  },
  async created() {
    await this.loadCases()
  },
  beforeUnmount() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval)
    }
  }
}
</script>

<style scoped>
body {
  font-family: Arial, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f5f5f5;
}

.container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.cases-display {
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
  border: 1px solid #ddd;
  padding: 15px;
  margin: 20px 0;
  border-radius: 4px;
}

.case-item {
  padding: 10px;
  border-bottom: 1px solid #eee;
}

.case-item:last-child {
  border-bottom: none;
}

.button-container {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
}

.action-button {
  padding: 12px 24px;
  font-size: 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: bold;
  color: white;
}

.action-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.build-button {
  background-color: #4CAF50;
}

.build-button:hover:not(:disabled) {
  background-color: #45a049;
}

.update-button {
  background-color: #2196F3;
}

.update-button:hover:not(:disabled) {
  background-color: #1976D2;
}

.progress-container {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 300px;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  z-index: 1000;
}

.progress {
  height: 20px;
}

.progress-text {
  font-size: 14px;
  color: #666;
}

.spinner-border-sm {
  width: 1rem;
  height: 1rem;
}

.alert {
  padding: 15px;
  margin: 20px 0;
  border-radius: 6px;
}

.alert-success {
  background-color: #dff0d8;
  color: #3c763d;
  border: 1px solid #d6e9c6;
}

.alert-danger {
  background-color: #f2dede;
  color: #a94442;
  border: 1px solid #ebccd1;
}
</style> 