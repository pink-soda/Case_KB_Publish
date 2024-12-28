<template>
  <div class="container">
    <div class="section">
      <!-- 案例信息收集部分 -->
      <h2>案例信息收集</h2>
      <input 
        type="text" 
        v-model="caseId" 
        class="input-field" 
        placeholder="请输入案例编号"
        @keyup.enter="collectInfo"
      >
      <button @click="collectInfo" class="button">收集信息</button>
      <div class="result-area">
        <div v-if="caseInfo" class="info-container">
          <div class="info-row">
            <span class="info-label">客户名称：</span>
            <span>{{ caseInfo.customer_name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">联系人：</span>
            <span>{{ caseInfo.contact_person }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">联系电话：</span>
            <span>{{ caseInfo.contact_phone }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">案例标题：</span>
            <span>{{ caseInfo.project_subject }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">系统版本：</span>
            <span>{{ caseInfo.system_version }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">case owner：</span>
            <span>{{ caseInfo.project_owner }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">案例进度：</span>
            <span>{{ caseInfo.project_scale }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 邮件生成部分 -->
    <div class="section">
      <h2>邮件生成</h2>
      <div class="reference-case">
        <label>请参照案例</label>
        <select v-model="selectedCase" class="select-field">
          <option value="">请选择参考案例</option>
          <option v-for="item in referenceCases" 
                  :key="item.id" 
                  :value="item.id">
            {{ item.id }}
          </option>
        </select>
      </div>
      <textarea 
        v-model="progressDescription" 
        class="progress-input" 
        placeholder="请输入当前进度描述..."
      ></textarea>
      <div class="d-flex align-items-center">
        <button class="button" @click="generateEmail">
          <i class="fas fa-envelope"></i> 生成邮件
        </button>
        <span v-show="tipVisible" 
              :class="['ms-2', tipError ? 'text-danger' : 'text-muted']">
          <i class="fas fa-info-circle"></i>
          <span class="tip-text">{{ tipMessage }}</span>
        </span>
      </div>
      <div class="generated-email-container">
        <div ref="emailContent" 
             class="generated-email" 
             contenteditable="true"
             v-html="emailContent">
        </div>
        <button v-if="emailContent"
                class="copy-button" 
                @click="copyEmailContent" 
                title="复制内容">
          <i class="fas fa-copy"></i>
        </button>
      </div>
    </div>

    <!-- 案例分类部分 -->
    <div class="section">
      <h2>案例分类</h2>
      <button @click="queryCaseCategory" class="button">
        <i class="fas fa-chevron-down"></i> 查询类别
      </button>
      <div class="tag-container">
        <div v-for="(tag, index) in tags" 
             :key="index" 
             class="tag">
          {{ tag }}
          <span class="tag-close" @click="removeTag(index)">×</span>
        </div>
      </div>
      <div class="section-subtitle">标签描述识别</div>
      <div class="chat-area" ref="chatArea">
        <div v-for="(message, index) in chatMessages"
             :key="index"
             :class="['chat-message', message.type]">
          {{ message.text }}
        </div>
      </div>
      <div class="input-group">
        <input type="text" 
               v-model="tagDescription" 
               class="input-field" 
               placeholder="输入消息..."
               @keyup.enter="sendDescription">
        <div class="input-group-append">
          <button class="btn btn-primary" @click="sendDescription">
            <i class="fas fa-paper-plane"></i>
          </button>
          <button class="btn btn-secondary" @click="addNewTag">
            <i class="fas fa-plus"></i>
          </button>
        </div>
      </div>
      <button @click="confirmClassification" class="button green">确认分类</button>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'

export default {
  name: 'Show',
  
  data() {
    return {
      caseId: '',
      selectedCase: '',
      progressDescription: '',
      tagDescription: '',
      tipVisible: false,
      tipError: false,
      tipMessage: '',
      tags: [],
      chatMessages: [],
      referenceCases: []  // 这个应该从后端获取
    }
  },

  computed: {
    ...mapState(['caseInfo', 'emailContent'])
  },

  methods: {
    ...mapActions(['fetchCaseInfo', 'generateEmail', 'queryCaseCategory']),

    showTip(message, isError = false) {
      this.tipMessage = message;
      this.tipError = isError;
      this.tipVisible = true;
      setTimeout(() => {
        this.tipVisible = false;
      }, 3000);
    },

    async collectInfo() {
      if (!this.caseId) {
        this.showTip('请输入案例编号', true);
        return;
      }
      try {
        await this.fetchCaseInfo(this.caseId);
        this.showTip('信息收集成功');
      } catch (error) {
        this.showTip(error.message || '信息收集失败', true);
      }
    },

    async handleGenerateEmail() {
      if (!this.selectedCase || !this.progressDescription) {
        this.showTip('请选择参考案例并填写进度描述', true);
        return;
      }
      try {
        await this.generateEmail({
          reference_case_id: this.selectedCase,
          progress_description: this.progressDescription,
          case_info: this.caseInfo
        });
        this.showTip('邮件生成成功');
      } catch (error) {
        this.showTip(error.message || '邮件生成失败', true);
      }
    },

    copyEmailContent() {
      const content = this.$refs.emailContent.innerText;
      navigator.clipboard.writeText(content)
        .then(() => this.showTip('复制成功'))
        .catch(() => this.showTip('复制失败', true));
    },

    async sendDescription() {
      if (!this.tagDescription.trim()) return;
      
      this.chatMessages.push({
        type: 'user',
        text: this.tagDescription
      });

      try {
        const response = await this.queryCaseCategory({
          description: this.tagDescription
        });
        
        this.chatMessages.push({
          type: 'system',
          text: response.message
        });

        if (response.tags) {
          this.tags.push(...response.tags);
        }
      } catch (error) {
        this.chatMessages.push({
          type: 'system',
          text: '处理失败，请重试'
        });
      }

      this.tagDescription = '';
      this.$nextTick(() => {
        const chatArea = this.$refs.chatArea;
        chatArea.scrollTop = chatArea.scrollHeight;
      });
    },

    removeTag(index) {
      this.tags.splice(index, 1);
    },

    addNewTag() {
      // 弹出输入框让用户输入新标签
      const newTag = prompt('请输入新标签');
      if (newTag && newTag.trim()) {
        // 检查是否已存在相同标签
        if (!this.tags.includes(newTag.trim())) {
          this.tags.push(newTag.trim());
        } else {
          this.showTip('标签已存在', true);
        }
      }
    },

    async confirmClassification() {
      if (this.tags.length === 0) {
        this.showTip('请至少添加一个分类标签', true);
        return;
      }

      try {
        // 调用 Vuex action 保存分类结果
        await this.$store.dispatch('saveClassification', {
          caseId: this.caseId,
          tags: this.tags
        });
        
        this.showTip('分类保存成功');
        // 清空标签列表
        this.tags = [];
        // 清空聊天记录
        this.chatMessages = [];
      } catch (error) {
        this.showTip(error.message || '保存分类失败', true);
      }
    }
  }
}
</script>

<style scoped>
/* 保持原有的样式，但使用 scoped 确保样式只应用于当前组件 */
.container {
  display: flex;
  gap: 20px;
  margin: 0 auto;
  min-width: 1600px;
  position: relative;
}

.section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  height: calc(100vh - 60px);
  overflow-y: auto;
  position: relative;
  min-width: 200px;
  max-width: none;
  flex: 0 0 auto;
}

.section:nth-child(1) {
  width: 400px;
  flex: none;
}

.section:nth-child(2) {
  width: 350px;
  flex: none;
}

.section:nth-child(3) {
  width: 370px;
  flex: none;
}

/* 其他样式保持不变... */

.generated-email-container {
  position: relative;
  margin-top: 20px;
}

.generated-email {
  min-height: 200px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.copy-button {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 5px 10px;
  background: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.copy-button:hover {
  background: #e9ecef;
}

.chat-area {
  height: 300px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 10px;
}

.chat-message {
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 4px;
}

.chat-message.user {
  background: #e3f2fd;
  margin-left: 20px;
}

.chat-message.system {
  background: #f5f5f5;
  margin-right: 20px;
}

.tag-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0;
}

.tag {
  background: #e3f2fd;
  padding: 4px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.tag-close {
  cursor: pointer;
  opacity: 0.6;
}

.tag-close:hover {
  opacity: 1;
}
</style>