<!--
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-27 11:45:10
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-27 11:45:59
 * @FilePath: \Case_KB_Vue\src\views\EmailClassification.vue
 * @Description: 案例分类组件
-->
<template>
  <base-layout>
    <!-- Toast 容器 -->
    <div class="toast-container"></div>

    <div class="container mt-4">
      <h2>Case分类管理</h2>
      
      <div class="row">
        <!-- 左侧：状态和操作区 -->
        <div class="col-md-3">
          <div class="card mb-4">
            <div class="card-body">
              <h5 class="card-title">当前状态</h5>
              <p class="card-text">
                分类层级文件: {{ hierarchy_exists ? '已存在' : '未创建' }}<br>
                案例文件: {{ cases_exists ? '已存在' : '未创建' }}
              </p>
            </div>
          </div>

          <div class="card mb-4">
            <div class="card-body">
              <h5 class="card-title">{{ hierarchy_exists && cases_exists ? '更新分类' : '创建分类' }}</h5>
              <form @submit.prevent="processEmails">
                <div class="mb-3">
                  <label for="email_folder" class="form-label">邮件文件夹路径</label>
                  <input type="text" 
                         class="form-control" 
                         id="email_folder" 
                         v-model="email_folder" 
                         required>
                </div>
                <div class="d-grid gap-2">
                  <button type="submit" 
                          class="btn btn-primary"
                          :disabled="isProcessing">
                    <span v-if="isProcessing" class="spinner-border spinner-border-sm me-1"></span>
                    {{ isProcessing ? '处理中...' : (hierarchy_exists && cases_exists ? '开始更新' : '开始创建') }}
                  </button>
                  <button v-if="hierarchy_exists && cases_exists"
                          type="button" 
                          class="btn btn-success"
                          @click="importToNeo4j"
                          :disabled="isImporting">
                    <i class="fas fa-database me-1"></i>
                    {{ isImporting ? '导入中...' : '导入Neo4j' }}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>

        <!-- 右侧：文件列表和分类结果 -->
        <div class="col-md-9">
          <!-- 邮件文件列表 -->
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="card-title mb-0">邮件文件列表</h5>
            </div>
            <div class="card-body" style="max-height: 600px; overflow-y: auto;">
              <template v-if="email_files.length">
                <div class="list-group">
                  <div v-for="file in sortedEmailFiles" 
                       :key="file.name"
                       class="list-group-item"
                       :class="{ processed: file.processed }">
                    <div class="d-flex flex-column">
                      <div class="d-flex align-items-center mb-2">
                        <span class="me-3">{{ file.name.replace('.pdf', '') }}</span>
                        <span :class="['badge', file.processed ? 'bg-success' : 'bg-warning']">
                          {{ file.processed ? '已处理' : '未处理' }}
                        </span>
                      </div>
                      <div v-if="file.processed" class="category-editor" :data-file="file.name">
                        <div class="row g-2">
                          <template v-for="(level, index) in ['一', '二', '三']" :key="index">
                            <div class="col-md-4">
                              <div class="input-group input-group-sm mb-2">
                                <span class="input-group-text w-100px">{{ level }}级分类</span>
                                <input type="text" 
                                       class="form-control category-input" 
                                       :data-level="index + 1"
                                       v-model="file.categories[`level${index + 1}`]"
                                       :disabled="file.confidence && file.confidence[`level${index + 1}`] >= 0.8"
                                       :style="getCategoryInputStyle(file.confidence?.[`level${index + 1}`])">
                                <span class="input-group-text confidence-badge"
                                      :class="getConfidenceBadgeClass(file.confidence?.[`level${index + 1}`])"
                                      data-bs-toggle="tooltip"
                                      title="分类置信度">
                                  {{ formatConfidence(file.confidence?.[`level${index + 1}`]) }}
                                </span>
                              </div>
                            </div>
                          </template>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
              <p v-else class="text-muted">暂无邮件文件</p>
            </div>
          </div>

          <!-- 分类结果 -->
          <div class="card">
            <div class="card-header">
              <h5 class="card-title mb-0">分类结果</h5>
            </div>
            <div class="card-body" style="max-height: 600px; overflow-y: auto;">
              <template v-if="hierarchy">
                <pre class="bg-light p-3 rounded"><code>{{ formattedHierarchy }}</code></pre>
              </template>
              <p v-else class="text-muted">暂无分类数据</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 处理进度模态框 -->
    <div class="modal fade" id="progressModal" tabindex="-1" ref="progressModal">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">处理进度</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="progress">
              <div class="progress-bar progress-bar-striped progress-bar-animated"
                   role="progressbar"
                   :style="{ width: progress + '%' }"
                   :aria-valuenow="progress"
                   aria-valuemin="0"
                   aria-valuemax="100">
                {{ progress }}%
              </div>
            </div>
            <div id="progressText" class="mt-2">{{ progressText }}</div>
          </div>
        </div>
      </div>
    </div>
  </base-layout>
</template>

<script>
import BaseLayout from '@/layouts/BaseLayout.vue'
import { Modal, Tooltip } from 'bootstrap'

export default {
  name: 'EmailClassification',
  components: {
    BaseLayout
  },
  data() {
    return {
      email_folder: './emails',
      email_files: [],
      hierarchy: null,
      hierarchy_exists: false,
      cases_exists: false,
      isProcessing: false,
      isImporting: false,
      progress: 0,
      progressText: '',
      progressModal: null,
      tooltips: []
    }
  },
  computed: {
    sortedEmailFiles() {
      return [...this.email_files].sort((a, b) => {
        if (a.processed === b.processed) {
          return a.name.localeCompare(b.name)
        }
        return a.processed ? 1 : -1
      })
    },
    formattedHierarchy() {
      return this.hierarchy ? JSON.stringify(this.hierarchy, null, 2) : ''
    }
  },
  methods: {
    showToast(message, type = 'success') {
      const toastContainer = document.querySelector('.toast-container')
      const toastEl = document.createElement('div')
      toastEl.className = `toast ${type} fade show`
      toastEl.innerHTML = `
        <div class="toast-header">
          <strong class="me-auto">${type === 'success' ? '成功' : type === 'error' ? '错误' : '警告'}</strong>
          <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
      `
      toastContainer.appendChild(toastEl)
      
      setTimeout(() => {
        toastEl.classList.add('fade-out')
        setTimeout(() => toastEl.remove(), 300)
      }, 2700)
    },

    getCategoryInputStyle(confidence) {
      if (!confidence) return {}
      if (confidence >= 0.9) return { backgroundColor: '#d4edda', borderColor: '#28a745' }
      if (confidence >= 0.7) return { backgroundColor: '#cce5ff', borderColor: '#17a2b8' }
      if (confidence >= 0.5) return { backgroundColor: '#fff3cd', borderColor: '#ffc107' }
      if (confidence >= 0.3) return { backgroundColor: '#ffe5d0', borderColor: '#fd7e14' }
      if (confidence >= 0.1) return { backgroundColor: '#f8d7da', borderColor: '#dc3545' }
      return { backgroundColor: '#e9ecef', borderColor: '#343a40' }
    },

    getConfidenceBadgeClass(confidence) {
      if (!confidence) return 'confidence-none'
      if (confidence >= 0.9) return 'confidence-very-high'
      if (confidence >= 0.7) return 'confidence-high'
      if (confidence >= 0.5) return 'confidence-medium'
      if (confidence >= 0.3) return 'confidence-low'
      if (confidence >= 0.1) return 'confidence-very-low'
      return 'confidence-none'
    },

    formatConfidence(confidence) {
      return confidence ? `${Math.round(confidence * 100)}%` : 'N/A'
    },

    async processEmails() {
      if (this.isProcessing) return

      this.isProcessing = true
      this.progress = 0
      this.progressText = '准备处理...'
      
      if (!this.progressModal) {
        this.progressModal = new Modal(this.$refs.progressModal)
      }
      this.progressModal.show()

      try {
        const response = await fetch('/process-emails', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email_folder: this.email_folder
          })
        })

        const data = await response.json()
        if (data.success) {
          this.showToast('处理成功')
          await this.loadData()
        } else {
          throw new Error(data.message || '处理失败')
        }
      } catch (error) {
        this.showToast(error.message, 'error')
      } finally {
        this.isProcessing = false
        this.progressModal.hide()
      }
    },

    async importToNeo4j() {
      if (this.isImporting || !this.hierarchy) return

      this.isImporting = true
      try {
        const response = await fetch('/import-to-neo4j', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.hierarchy)
        })

        const data = await response.json()
        if (data.success) {
          this.showToast('分类数据已成功导入到Neo4j')
        } else {
          if (data.message.includes('已存在')) {
            this.showToast(data.message, 'warning')
          } else {
            throw new Error(data.message)
          }
        }
      } catch (error) {
        this.showToast('导入失败: ' + error.message, 'error')
      } finally {
        this.isImporting = false
      }
    },

    async loadData() {
      try {
        const response = await fetch('/get-classification-data')
        const data = await response.json()
        this.email_files = data.email_files || []
        this.hierarchy = data.hierarchy
        this.hierarchy_exists = data.hierarchy_exists
        this.cases_exists = data.cases_exists
      } catch (error) {
        console.error('加载数据失败:', error)
        this.showToast('加载数据失败', 'error')
      }
    },

    initTooltips() {
      this.tooltips.forEach(tooltip => tooltip.dispose())
      this.tooltips = []
      
      const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
      this.tooltips = tooltipTriggerList.map(tooltipTriggerEl => new Tooltip(tooltipTriggerEl))
    }
  },
  async created() {
    await this.loadData()
  },
  updated() {
    this.$nextTick(() => {
      this.initTooltips()
    })
  },
  beforeUnmount() {
    this.tooltips.forEach(tooltip => tooltip.dispose())
  }
}
</script>

<style scoped>
/* 已有的样式保持不变 */
.hierarchy-tree {
  font-family: 'Microsoft YaHei', sans-serif;
  padding: 15px;
}

.hierarchy-tree ul {
  margin: 0;
  padding-left: 20px;
}

.hierarchy-tree li {
  list-style: none;
  margin: 5px 0;
}

.hierarchy-tree .folder {
  color: #2c3e50;
  font-weight: bold;
}

.hierarchy-tree .file {
  color: #34495e;
}

pre code {
  font-family: 'Microsoft YaHei', Consolas, monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.category-editor {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 0.25rem;
  margin-top: 0.5rem;
}

.input-group-sm > .form-control {
  font-size: 0.875rem;
}

.w-100px {
  min-width: 100px !important;
  justify-content: center;
}

.btn-success {
  transition: all 0.3s ease;
}

.btn-success:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  pointer-events: none;
}

.toast {
  min-width: 300px;
  background-color: white;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
  opacity: 1 !important;
  transition: opacity 0.3s ease-in-out;
  margin-bottom: 10px;
  pointer-events: auto;
}

.toast.success {
  border-left: 4px solid #28a745;
}

.toast.error {
  border-left: 4px solid #dc3545;
}

.toast.warning {
  border-left: 4px solid #ffc107;
}

.toast.fade-out {
  opacity: 0 !important;
}

.confidence-badge {
  min-width: 60px;
  text-align: center;
}

.confidence-badge.confidence-very-high {
  background-color: #198754 !important;
  color: white !important;
}

.confidence-badge.confidence-high {
  background-color: #0dcaf0 !important;
  color: white !important;
}

.confidence-badge.confidence-medium {
  background-color: #ffc107 !important;
  color: #664d03 !important;
}

.confidence-badge.confidence-low {
  background-color: #fd7e14 !important;
  color: white !important;
}

.confidence-badge.confidence-very-low {
  background-color: #dc3545 !important;
  color: white !important;
}

.confidence-badge.confidence-none {
  background-color: #343a40 !important;
  color: white !important;
}

/* 滚动条样式 */
.card-body::-webkit-scrollbar {
  width: 8px;
}

.card-body::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.card-body::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.card-body::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* 未处理案例高亮 */
.list-group-item:not(.processed) {
  background-color: #fff8e1;
  border-left: 4px solid #ffc107;
}

/* 已处理案例样式 */
.list-group-item.processed {
  border-left: 4px solid #28a745;
}
</style> 