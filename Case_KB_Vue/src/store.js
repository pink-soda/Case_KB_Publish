import { createStore } from 'vuex'
import api from './api'

export default createStore({
  state: {
    caseInfo: null,
    emailContent: '',
    hierarchy: null,
    cases: [],
    emailFiles: [],
    referenceCases: []
  },
  
  mutations: {
    setCaseInfo(state, info) {
      state.caseInfo = info;
    },
    setEmailContent(state, content) {
      state.emailContent = content;
    },
    setHierarchy(state, hierarchy) {
      state.hierarchy = hierarchy;
    },
    setCases(state, cases) {
      state.cases = cases;
    },
    setEmailFiles(state, files) {
      state.emailFiles = files;
    },
    setReferenceCases(state, cases) {
      state.referenceCases = cases;
    }
  },
  
  actions: {
    async fetchCaseInfo({ commit }, caseId) {
      try {
        const response = await api.collectInfo(caseId);
        if (response.status === 'success') {
          commit('setCaseInfo', response.data);
        } else {
          throw new Error(response.message);
        }
      } catch (error) {
        throw new Error('获取案例信息失败');
      }
    },
    
    async generateEmail({ commit }, data) {
      try {
        const response = await api.generateEmail(data);
        if (response.success) {
          commit('setEmailContent', response.email);
        } else {
          throw new Error(response.message);
        }
      } catch (error) {
        throw new Error('生成邮件失败');
      }
    },
    
    async saveClassification({ commit }, { caseId, tags }) {
      try {
        const response = await api.saveClassification(caseId, tags);
        if (!response.success) {
          throw new Error(response.message);
        }
      } catch (error) {
        throw new Error('保存分类失败');
      }
    },

    async queryCaseCategory({ commit }, { description }) {
      try {
        const response = await api.queryCaseCategory(description);
        return response;
      } catch (error) {
        throw new Error('查询分类失败');
      }
    },

    async fetchReferenceCases({ commit }) {
      try {
        const response = await api.getReferenceCases();
        if (response.success) {
          commit('setReferenceCases', response.cases);
        }
      } catch (error) {
        throw new Error('获取参考案例失败');
      }
    }
  }
}) 