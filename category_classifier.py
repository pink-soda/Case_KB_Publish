'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-09 10:41:47
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-09 10:42:02
FilePath: \test\category_classifier.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
class CategoryClassifier:
    def __init__(self, llm_handler):
        self.llm_handler = llm_handler
        self.prompt_template = """你是一个专业的技术支持分类专家。请基于以下分类层级结构，对给定的技术支持案例进行分类。

        分类层级结构：
        {hierarchy}

        案例邮件内容：
        {email_content}

        分析要求：
        1. 仔细分析邮件内容中的技术问题描述
        2. 识别关键的技术术语和问题特征
        3. 根据问题的性质选择最合适的分类
        4. 评估分类的置信度

        请严格按照以下JSON格式返回（不要添加任何其他内容）：
        {{
            "level1": "一级分类名称",
            "level2": "二级分类名称",
            "level3": "三级分类名称",
            "confidence": 0.95,
            "reasoning": "分类理由说明"
        }}

        注意：
        - 如果案例内容模糊或者可能属于多个分类，请选择最相关的一个，并相应降低置信度
        - 如果完全无法确定分类，请将所有分类设为"未分类"，置信度设为0
        - 必须返回上述格式的JSON，不要添加任何额外的文本或说明
        """

    def classify_case(self, email_content: str, hierarchy: str) -> dict:
        prompt = self.prompt_template.format(
            hierarchy=hierarchy,
            email_content=email_content
        )
        response = self.llm_handler._call_azure_llm(prompt)
        return self.llm_handler._parse_llm_response(response) 