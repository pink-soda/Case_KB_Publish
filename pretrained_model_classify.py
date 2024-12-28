from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# 父类和子类标签
parent_categories = ["激活", "补丁更新", "系统升级", "蓝屏", "黑屏", "其他"]
child_categories = {
    "激活": ["激活失败", "密钥无效"],
    "补丁更新": ["安全补丁", "功能更新失败"],
    "系统升级": ["驱动冲突", "系统错误"],
    "蓝屏": ["内存错误", "硬盘故障"],
    "黑屏": ["显卡问题", "未知硬件问题"],
    "其他": ["其他问题"]
}

# 加载预训练模型
parent_model_name = "bert-base-chinese"
child_model_name = "bert-base-chinese"

# 父类分类器
parent_tokenizer = AutoTokenizer.from_pretrained(parent_model_name)
parent_model = AutoModelForSequenceClassification.from_pretrained(parent_model_name, num_labels=len(parent_categories))
parent_classifier = pipeline("text-classification", model=parent_model, tokenizer=parent_tokenizer, return_all_scores=True)

# 子类分类器（这里示例用一个模型代替实际多个子类模型）
child_tokenizer = AutoTokenizer.from_pretrained(child_model_name)
child_model = AutoModelForSequenceClassification.from_pretrained(child_model_name, num_labels=10)
child_classifier = pipeline("text-classification", model=child_model, tokenizer=child_tokenizer, return_all_scores=True)

# 多级分类逻辑
def predict_multilevel(log):
    # 父类分类
    parent_scores = parent_classifier(log)
    parent_pred_index = max(enumerate(parent_scores[0]), key=lambda x: x[1]["score"])[0]
    parent_pred = parent_categories[parent_pred_index]

    # 子类分类
    if parent_pred in child_categories:
        child_labels = child_categories[parent_pred]
        child_scores = child_classifier(log)
        child_pred_index = max(enumerate(child_scores[0]), key=lambda x: x[1]["score"])[0]
        child_pred = child_labels[child_pred_index % len(child_labels)]  # 防止索引溢出
    else:
        child_pred = "未知子类"

    return {"父类": parent_pred, "子类": child_pred}

# 测试多级分类
log_example = '''接到工行接口人许翔来电，反馈V2022-L版本系统安装8B补丁报错问题，涉及1台设备，具体补丁号及报错信息接口人未提供，接口人表示日志已上传，需要协助分析处理。
申请开启P2案例。
根据用户要求，已在CASE标题添加备注：“王学睿”方便区分。一线按照用户要求进行备注。'''
result = predict_multilevel(log_example)
print("分类结果:\n", result)
