class TagManager {
    constructor() {
        this.selectedTags = new Set();
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // 监听查询类别按钮点击
        document.querySelector('#queryCategory').addEventListener('click', () => {
            this.handleCategoryQuery();
        });

        // 监听新标签输入
        const tagInput = document.querySelector('#tagInput');
        tagInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleNewTagInput(e.target.value);
                e.target.value = '';
            }
        });

        // 监听添加标签按钮
        document.querySelector('#addTagBtn').addEventListener('click', () => {
            this.addSelectedTagsToSpan();
        });
    }

    async handleCategoryQuery() {
        const resultSpan = document.querySelector('#categoryResult');
        resultSpan.innerHTML = '正在查询...';
        
        try {
            const response = await fetch('/query-category', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    case_id: getCurrentCaseId() // 需要实现这个函数来获取当前案例ID
                })
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                resultSpan.innerHTML = `
                    <div>一级分类: ${data.category.level1}</div>
                    <div>二级分类: ${data.category.level2}</div>
                    <div>三级分类: ${data.category.level3}</div>
                    <div>置信度: ${data.confidence}</div>
                    <div>推理过程: ${data.reasoning}</div>
                `;
            } else {
                resultSpan.innerHTML = '查询失败: ' + data.message;
            }
        } catch (error) {
            resultSpan.innerHTML = '查询出错: ' + error.message;
        }
    }

    async handleNewTagInput(text) {
        try {
            const response = await fetch('/generate-tag', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text })
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                this.displayGeneratedTags(data.tags);
            }
        } catch (error) {
            console.error('生成标签失败:', error);
        }
    }

    displayGeneratedTags(tags) {
        const dialog = document.querySelector('#tagDialog');
        const tagList = dialog.querySelector('.tag-list');
        tagList.innerHTML = tags.map(tag => `
            <div class="tag">
                <input type="checkbox" value="${tag}">
                <label>${tag}</label>
            </div>
        `).join('');
        dialog.style.display = 'block';
    }

    addSelectedTagsToSpan() {
        const checkboxes = document.querySelectorAll('#tagDialog input[type="checkbox"]:checked');
        const selectedTagSpan = document.querySelector('#selectedTags');
        
        checkboxes.forEach(checkbox => {
            if (!this.selectedTags.has(checkbox.value)) {
                this.selectedTags.add(checkbox.value);
                const tagElement = document.createElement('span');
                tagElement.className = 'tag';
                tagElement.textContent = checkbox.value;
                selectedTagSpan.appendChild(tagElement);
            }
        });
        
        document.querySelector('#tagDialog').style.display = 'none';
    }
}

// 初始化标签管理器
document.addEventListener('DOMContentLoaded', () => {
    window.tagManager = new TagManager();
}); 