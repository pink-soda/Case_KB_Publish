'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-09 10:41:47
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-12 17:16:24
FilePath: \test\category_classifier.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import json

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

class CategoryHierarchyBuilder:
    def __init__(self, llm_handler, similarity_threshold=0.8, initial_hierarchy=None, initial_cases=None):
        self.llm_handler = llm_handler
        self.similarity_threshold = similarity_threshold
        self.hierarchy = initial_hierarchy if initial_hierarchy is not None else {}
        self.classified_cases = initial_cases if initial_cases is not None else []
        
        self.classification_prompt = """你是一个专业的操作系统技术支持分类专家。请分析以下技术支持案例，并创建或匹配一个三级分类结构。

        案例邮件内容：
        {email_content}

        当前已有的分类层级结构（如果为空则创建新的）：
        {existing_hierarchy}

        分析要求：
        1. 仔细分析邮件内容中的技术问题描述
        2. 识别关键的技术术语和问题特征
        3. 如果现有分类结构为空，创建新的三级分类
        4. 如果已有分类结构，评估是否可以匹配现有分类
        5. 三级分类说明：
            - 一级分类：问题种类分类，可多选。如：硬件问题、软件问题、网络问题、安全问题、性能问题、配置问题、故障排除、其他等等
            - 二级分类：案例背景信息分类，可多选。如：系统版本，复现频率，问题发生阶段，用户操作等等的描述
            - 三级分类：具体错误代码，可多选。示例：0x800f0922，0x80004005等等

        请严格按照以下JSON格式返回（不要添加任何其他内容）：
        {{
            "level1": "一级分类名称",
            "level2": "二级分类名称",
            "level3": "三级分类名称",
            "similarity": 0.0,  # 与现有分类的相似度（0-1），如果是新分类则为0
            "matched_path": "",  # 匹配到的现有分类路径，如果是新分类则为空
            "reasoning": "分类理由说明"
        }}
        """
        
        self.similarity_prompt = """你是一个专业的分类相似度评估专家。请评估以下两个技术支持案例的分类相似度。

        案例1分类：
        一级分类：{case1_level1}
        二级分类：{case1_level2}
        三级分类：{case1_level3}

        案例2分类：
        一级分类：{case2_level1}
        二级分类：{case2_level2}
        三级分类：{case2_level3}

        请分析这两个分类的相似度，返回一个0到1之间的数值，其中：
        - 1表示完全相同
        - 0.8以上表示非常相似
        - 0.5-0.8表示部分相似
        - 0.5以下表示差异较大
        - 0表示完全不同

        请严格按照以下JSON格式返回（不要添加任何其他内容）：
        {{
            "similarity": 0.95,
            "reasoning": "相似度评估理由"
        }}
        """

    def _add_to_hierarchy(self, level1, level2, level3):
        """将新的分类添加到层级结构中"""
        if level1 not in self.hierarchy:
            self.hierarchy[level1] = {}
        if level2 not in self.hierarchy[level1]:
            self.hierarchy[level1][level2] = []
        if level3 not in self.hierarchy[level1][level2]:
            self.hierarchy[level1][level2].append(level3)

    def _hierarchy_to_string(self):
        """将层级结构转换为字符串表示"""
        result = []
        for level1, level2_dict in self.hierarchy.items():
            result.append(f"- {level1}")
            for level2, level3_list in level2_dict.items():
                result.append(f"  - {level2}")
                for level3 in level3_list:
                    result.append(f"    - {level3}")
        return "\n".join(result)

    def _calculate_similarity(self, case1_levels, case2_levels):
        """计算两个分类的相似度"""
        prompt = self.similarity_prompt.format(
            case1_level1=case1_levels[0],
            case1_level2=case1_levels[1],
            case1_level3=case1_levels[2],
            case2_level1=case2_levels[0],
            case2_level2=case2_levels[1],
            case2_level3=case2_levels[2]
        )
        response = self.llm_handler._call_azure_llm(prompt)
        result = self.llm_handler._parse_llm_response(response)
        return result.get('similarity', 0)

    def _parse_hierarchy_response(self, response):
        """专门用于解析层级分类响应的方法"""
        # 如果响应已经是字典格式，直接返回
        if isinstance(response, dict):
            return response
            
        # 否则尝试使用原有的解析方法
        try:
            result = self.llm_handler._parse_llm_response(response)
            return result
        except Exception as e:
            raise Exception(f"解析层级响应失败: {str(e)}")

    def _parse_classification_response(self, response: str) -> dict:
        """
        专门用于解析分类响应的方法
        
        Args:
            response: LLM返回的响应字符串
            
        Returns:
            dict: 解析后的分类结果
        """
        try:
            # 如果响应经是字典格式，直接返回
            if isinstance(response, dict):
                return response
            
            # 清理响应文本，移除多余的空格和换行
            cleaned_response = response.replace('\n', '').replace('    ', '')
            
            # 尝试直接解析JSON
            try:
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果解析失败，尝试提取JSON部分
                import re
                json_pattern = r'\{[^{}]*\}'
                match = re.search(json_pattern, cleaned_response)
                if match:
                    result = json.loads(match.group())
                else:
                    raise Exception("无法解析LLM返回的JSON格式")
            
            # 验证所需字段
            required_fields = ['level1', 'level2', 'level3', 'similarity', 'matched_path', 'reasoning']
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                raise ValueError(f"响应缺少必要字段: {', '.join(missing_fields)}")
            
            # 确保similarity是浮点数
            result['similarity'] = float(result['similarity'])
            
            return result
            
        except Exception as e:
            raise Exception(f"解析分类响应失败: {str(e)}")

    def process_case(self, email_content: str) -> dict:
        """处理单个案例，返回分类结果"""
        try:
            # 准备当前的层级结构
            existing_hierarchy = self._hierarchy_to_string()
            
            # 获取分类建议
            prompt = self.classification_prompt.format(
                email_content=email_content,
                existing_hierarchy=existing_hierarchy
            )
            response = self.llm_handler._call_azure_llm(prompt)
            
            # 使用新的专用解析方法
            result = self._parse_classification_response(response)
            
            # 如果是第一个案例或没有匹配到现有分类
            if not self.hierarchy or result['similarity'] < self.similarity_threshold:
                self._add_to_hierarchy(result['level1'], result['level2'], result['level3'])
                
            # 存储已分类的案例
            self.classified_cases.append({
                'content': email_content,
                'classification': {
                    'level1': result['level1'],
                    'level2': result['level2'],
                    'level3': result['level3']
                }
            })
            
            return result
            
        except Exception as e:
            error_msg = f"处理案例时出错: {str(e)}"
            if 'response' in locals():
                error_msg += f"\n响应内容: {response}"
            raise Exception(error_msg)

    def get_current_hierarchy(self) -> dict:
        """返回当前的分类层级结构"""
        return self.hierarchy

    def get_classified_cases(self) -> list:
        """返回所有已分类的案例"""
        return self.classified_cases 