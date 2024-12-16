'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-09 10:41:47
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-16 21:09:05
FilePath: \test\category_classifier.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import json
import openai

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
        4. 评估分类的置信度，置信度评分说明：
           - 完全匹配: 0.9-1.0
           - 高度相关: 0.7-0.9
           - 中等相关: 0.5-0.7
           - 低相关: 0.3-0.5
           - 可能相关: 0.1-0.3
           - 不相关: 0.0-0.1

        请严格按照以下JSON格式返回（不要添加任何其他内容）：
        {{
            "level1": "一级分类名称",
            "level2": "二级分类名称",
            "level3": "三级分类名称",
            "confidence": {{
                "level1": 0.95,  // 一级分类的置信度
                "level2": 0.85,  // 二级分类的置信度
                "level3": 0.75   // 三级分类的置信度
            }},
            "reasoning": "分类理由说明"
        }}

        注意：
        - 每个层级的分类都需要独立评估置信度
        - 如果某个层级的分类不确定，可以给出较低的置信度
        - 置信度应该反映分类的准确性和确定性
        - 如果案例内容模糊或者可能属于多个分类，请选择最相关的一个，并相应降低置信度
        - 如果完全无法确定分类，请将所有分类设为"未分类"，置信度设为0
        - 必须返回上述格式的JSON，不要添加任何额外的文本或说明
        """
        self.cases_file = 'classified_cases.json'  # 添加文件路径属性

    def classify_case(self, email_content: str, hierarchy: str) -> dict:
        prompt = self.prompt_template.format(
            hierarchy=hierarchy,
            email_content=email_content
        )
        response = self.llm_handler._call_azure_llm(prompt)
        result = self.llm_handler._parse_llm_response(response)
        
        # 确保返回结果包含置信度信息
        return {
            'level1': result['level1'],
            'level2': result['level2'],
            'level3': result['level3'],
            'confidence': {
                'level1': result['confidence']['level1'],
                'level2': result['confidence']['level2'],
                'level3': result['confidence']['level3']
            }
        }

class CategoryHierarchyBuilder:
    def __init__(self, llm_handler, cases_file='classified_cases.json', initial_hierarchy=None, initial_cases=None):
        self.llm_handler = llm_handler
        self.hierarchy = initial_hierarchy or {}
        self.classified_cases = initial_cases or []
        self.similarity_threshold = 0.8
        self.max_retries = 3
        self.cases_file = cases_file
        
        self.classification_prompt = """你是一个专业的操作系统技术支持分类专家。请分析以下技术支持案例，并创建或匹配一个三级分类结构。

        案例邮件内容：
        {email_content}

        当前已有的分类层级结构（如果为空则创建新的）
        {existing_hierarchy}

        分析要求：
        1. 仔细分析邮件内容中的技术问题描述
        2. 识别关键的技术术语和问题特征
        3. 如果现有分类结构为空，创建新的三级分类
        4. 如果已有分类结构，评估是否可以匹配现有分类
        5. 三级分类说明：
            - 一级分类：问题种类分类，可多选。如：硬件问题、软件问题、网络问题、安全问题、性能问题、配置问题、故障排除、其他等等
            - 二级分类：案例背景信息分类，可为空，也可多选。如：系统版本，复现频率，问题发生阶段，用户操作等等的描述
            - 三级分类：具体错误代码，可为空，也可多选。示例：0x800f0922，0x80004005等等
        6. 匹配现有分类的相似度说明：
            - 相似度的比较仅发生在同级别分类中，即：一级分类与一级分类比较，二级分类与二级分类比较，三级分类与三级分类比较。
            - 相似度得分的含义：
                - 完全匹配: 0.9-1.0
                - 高度相关: 0.7-0.9
                - 中等相关: 0.5-0.7
                - 低度相关: 0.3-0.5
                - 可能相关: 0.1-0.3
                - 不相关: 0.0-0.1
            - 如果同一级别中存在多个分类，则逐一比较每个分类，相似度得分在0.8以上则认为匹配成功，否则认为未匹配。
            - 如果未匹配到现有分类，需要在对应级别创建新的分类

        注意：必须严格按照以下JSON格式返回，所有字段都必须包含且不能为空：
        {{
            "level1": "一级分类名称",
            "level2": "二级分类名称",
            "level3": "三级分类名称",
            "similarity": {{
                "level1": 0.95,  // 与有一级分类的相似度（0-1），如果是新分类则为0
                "level2": 0.85,  // 与现有二级分类的相似度（0-1），如果是新分类则为0
                "level3": 0.75   // 与现有三级分类的相似度（0-1），如果是新分类则为0
            }},
            "matched_path_level1": "",  // 匹配到的现有一级分类路径，如果是新分类则为空字符串
            "matched_path_level2": "",  // 匹配到的现有二级分类路径，如果是新分类则为空字符串
            "matched_path_level3": "",  // 匹配到的现有三级分���路径，如果是新分类则为空字符串
            "reasoning": "分类理由说明"  // 必须提供分类理由
        }}
        所有字段都是必需的，不能省略任字段。如果某个字段没有值，使用空字符串""，不要使用null或省略该字段。
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
        """专门用于解析分类响应的方法"""
        try:
            # 如果响应已经是字典格式，直接返回
            if isinstance(response, dict):
                return response
            
            # 清理响应文本，移除多余的空格和换行
            cleaned_response = response.replace('\n', '').replace('    ', '')
            
            # 提取JSON部分
            start = cleaned_response.find('{')
            end = cleaned_response.rfind('}') + 1
            json_str = cleaned_response[start:end]
            
            # 解析JSON
            result = json.loads(json_str)
            
            # 验证所需字段
            required_fields = ['level1', 'level2', 'level3', 'similarity', 'matched_path_level1', 'matched_path_level2', 'matched_path_level3', 'reasoning']
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                raise ValueError(f"响应缺少必要字段: {', '.join(missing_fields)}")
            
            # 确保similarity字段包含所有必要的子字段
            if 'similarity' in result:
                required_similarity_fields = ['level1', 'level2', 'level3']
                missing_similarity_fields = [field for field in required_similarity_fields if field not in result['similarity']]
                if missing_similarity_fields:
                    raise ValueError(f"similarity字段缺少必要的子字段: {', '.join(missing_similarity_fields)}")
            
            return result
            
        except Exception as e:
            raise Exception(f"解析分类响应失败: {str(e)}")

    def process_case(self, email_content: str, file_path: str = None) -> dict:
        """处理单个案例，返回分类结果"""
        try:
            existing_hierarchy = self._hierarchy_to_string()
            attempts = 0
            last_error = None
            response = None
            while attempts < self.max_retries:
                try:
                    prompt = self.classification_prompt.format(
                        email_content=email_content,
                        existing_hierarchy=existing_hierarchy
                    )
                    response = self.llm_handler._call_azure_llm(prompt)
                    result = self._parse_classification_response(response)
                    break
                except Exception as e:
                    attempts += 1
                    last_error = e
                    if isinstance(e, openai.RateLimitError):
                        raise Exception(f"Azure OpenAI API 限流错误: {str(e)}")
                    if attempts == self.max_retries:
                        error_msg = f"处理案例时出错（尝试{attempts}次后失败）: {str(last_error)}"
                        if response:
                            error_msg += f"\n响应内容: {response}"
                        raise Exception(error_msg)
                    continue
            
            # 计算总体置信度得分
            similarity_score = {
                'level1': float(result['similarity']['level1']),
                'level2': float(result['similarity']['level2']), 
                'level3': float(result['similarity']['level3'])
            }
            
            # 如果是第一个案例或没有匹配到现有分类(任一层级相似度<0.8)
            if not self.hierarchy or any(score < self.similarity_threshold for score in similarity_score.values()):
                self._add_to_hierarchy(result['level1'], result['level2'], result['level3'])
            
            # 存储已分类的案例，包含置信度得分
            case_data = {
                'content': email_content,
                'file_path': file_path,  # 添加文件路径
                'classification': {
                    'level1': result['level1'],
                    'level2': result['level2'],
                    'level3': result['level3']
                },
                'category_score': similarity_score,
                'reasoning': result.get('reasoning', '')
            }
            self.classified_cases.append(case_data)
            
            # 保存到JSON文件
            self._save_classified_cases()
            
            return result
            
        except Exception as e:
            error_msg = f"处理案例时出错: {str(e)}"
            if response:  # 使用之前初始化的response变量
                error_msg += f"\n响应内容: {response}"
            raise Exception(error_msg)

    def _save_classified_cases(self):
        """保存分类结果到JSON文件"""
        try:
            with open(self.cases_file, 'w', encoding='utf-8') as f:
                json.dump(self.classified_cases, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存分类结果时出错: {str(e)}")

    def get_current_hierarchy(self) -> dict:
        """返回当前的分类层级结构"""
        return self.hierarchy

    def get_classified_cases(self) -> list:
        """返回所有已分类的案例"""
        return self.classified_cases 