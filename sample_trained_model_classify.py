import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.base import BaseEstimator, TransformerMixin

# 示例数据
# 假设你已经有一个标注好的多级分类数据集，格式如下：
data = {
    "log": [
        "系统提示激活失败，错误代码0x1234",
        "补丁更新失败，安全补丁无法安装",
        "系统升级后出现蓝屏，提示内存错误",
        "黑屏问题，可能与显卡驱动有关",
        "安装补丁后，功能更新失败",
        "激活过程中出现密钥无效错误",
    ],
    "parent_category": ["激活", "补丁更新", "蓝屏", "黑屏", "补丁更新", "激活"],
    "child_category": [
        "激活失败",
        "安全补丁",
        "内存错误",
        "显卡问题",
        "功能更新失败",
        "密钥无效",
    ],
}

# 转换为DataFrame
df = pd.DataFrame(data)

# 分割数据：父类模型的数据
X = df["log"]
y_parent = df["parent_category"]

# 训练集与测试集划分
X_train, X_test, y_train, y_test = train_test_split(X, y_parent, test_size=0.2, random_state=42)

# 构建父类分类模型
parent_model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", RandomForestClassifier(random_state=42)),
])

# 训练父类分类模型
parent_model.fit(X_train, y_train)

# 评估父类分类模型
parent_predictions = parent_model.predict(X_test)
print("父类分类报告:\n")
print(classification_report(y_test, parent_predictions))

# 为子类分类做准备
# 按父类分组，训练每个父类对应的子类分类器
child_models = {}
for parent in df["parent_category"].unique():
    # 筛选属于当前父类的数据
    parent_data = df[df["parent_category"] == parent]
    
    X_child = parent_data["log"]
    y_child = parent_data["child_category"]
    
    # 分割训练集和测试集
    X_train_child, X_test_child, y_train_child, y_test_child = train_test_split(
        X_child, y_child, test_size=0.2, random_state=42
    )

    # 构建子类分类模型
    child_model = Pipeline([
        ("tfidf", TfidfVectorizer()),
        ("classifier", RandomForestClassifier(random_state=42)),
    ])

    # 训练子类模型
    child_model.fit(X_train_child, y_train_child)

    # 保存模型
    child_models[parent] = child_model

    # 评估子类分类器
    child_predictions = child_model.predict(X_test_child)
    print(f"子类分类报告（父类: {parent}）:\n")
    print(classification_report(y_test_child, child_predictions))

# 整合多级分类预测逻辑
def predict_multilevel(log):
    # 预测父类
    parent_prediction = parent_model.predict([log])[0]
    
    # 根据父类选择对应的子类模型
    if parent_prediction in child_models:
        child_prediction = child_models[parent_prediction].predict([log])[0]
    else:
        child_prediction = "未知子类"

    return {
        "父类": parent_prediction,
        "子类": child_prediction
    }

# 测试多级分类
log_example = "系统更新后蓝屏，提示驱动冲突"
result = predict_multilevel(log_example)
print("分类结果:\n", result)




