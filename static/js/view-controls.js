// 视图控制器类
class ViewControls {
    constructor() {
        // 添加延迟初始化
        setTimeout(() => this.initialize(), 0);
    }

    initialize() {
        console.log('Initializing view controls...');
        // 获取元素
        this.findElements();

        if (this.elementsFound) {
            this.setupEventListeners();
            this.setInitialState();
            console.log('View controls initialized successfully');
        } else {
            console.log('Waiting for elements...');
            // 如果元素未找到，等待一段时间后重试
            setTimeout(() => this.initialize(), 100);
        }
    }

    findElements() {
        this.treeViewBtn = document.getElementById('treeViewBtn');
        this.jsonViewBtn = document.getElementById('jsonViewBtn');
        this.treeView = document.getElementById('treeView');
        this.jsonView = document.getElementById('jsonView');
        this.hierarchyCode = document.getElementById('hierarchyCode');

        this.elementsFound = !!(this.treeViewBtn && this.jsonViewBtn && 
                              this.treeView && this.jsonView && this.hierarchyCode);

        if (!this.elementsFound) {
            console.log('Elements not found:', {
                treeViewBtn: !!this.treeViewBtn,
                jsonViewBtn: !!this.jsonViewBtn,
                treeView: !!this.treeView,
                jsonView: !!this.jsonView,
                hierarchyCode: !!this.hierarchyCode
            });
        }
    }

    setupEventListeners() {
        // 移除现有的事件监听器
        const newTreeViewBtn = this.treeViewBtn.cloneNode(true);
        const newJsonViewBtn = this.jsonViewBtn.cloneNode(true);
        
        this.treeViewBtn.parentNode.replaceChild(newTreeViewBtn, this.treeViewBtn);
        this.jsonViewBtn.parentNode.replaceChild(newJsonViewBtn, this.jsonViewBtn);
        
        // 更新引用
        this.treeViewBtn = newTreeViewBtn;
        this.jsonViewBtn = newJsonViewBtn;

        // 添加新的事件监听器
        this.treeViewBtn.addEventListener('click', () => {
            console.log('Tree view clicked');
            this.showTreeView();
        });

        this.jsonViewBtn.addEventListener('click', () => {
            console.log('JSON view clicked');
            this.showJsonView();
        });
    }

    showTreeView() {
        if (!this.elementsFound) return;
        this.treeView.style.display = 'block';
        this.jsonView.style.display = 'none';
        this.treeViewBtn.classList.add('active');
        this.jsonViewBtn.classList.remove('active');
    }

    showJsonView() {
        if (!this.elementsFound) return;
        this.treeView.style.display = 'none';
        this.jsonView.style.display = 'block';
        this.jsonViewBtn.classList.add('active');
        this.treeViewBtn.classList.remove('active');

        this.updateJsonView();
    }

    updateJsonView() {
        if (!this.elementsFound) return;
        fetch('/get-classification-result')
            .then(response => response.json())
            .then(data => {
                console.log('Received classification data:', data);
                if (data.success && data.hierarchy) {
                    const formattedJson = JSON.stringify(data.hierarchy, null, 2);
                    this.hierarchyCode.textContent = formattedJson;
                }
            })
            .catch(error => console.error('Error updating JSON view:', error));
    }

    setInitialState() {
        if (!this.elementsFound) return;
        this.showTreeView();
    }
}

// 全局初始化函数
window.initializeViewControls = function() {
    console.log('Creating new ViewControls instance');
    if (window.viewControls) {
        delete window.viewControls;
    }
    window.viewControls = new ViewControls();
};

// 页面加载时初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM Content Loaded - initializing view controls');
        window.initializeViewControls();
    });
} else {
    console.log('Document already loaded - initializing view controls');
    window.initializeViewControls();
} 