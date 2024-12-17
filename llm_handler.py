from openai import AzureOpenAI
import json
import os
from dotenv import load_dotenv
import logging
from azure.core.credentials import AzureKeyCredential
#from azure.ai.textanalytics import TextAnalyticsClient
import traceback

logger = logging.getLogger(__name__)

class LLMHandler:
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        # 初始化Azure OpenAI客户端
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY_2"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # 部署名称
        self.deployment_name = os.getenv("MODEL_NAME")        

    def analyze_description_with_categories(self, description: str, category_hierarchy: dict) -> dict:
        """
        使用Azure LLM分析描述文本，并根据知识图谱中的类别进行分类
        返回格式：只返回最小子类别及其置信度和解释
        """
        try:
            # 格式化类别层级结构
            formatted_hierarchy = self._format_category_hierarchy(category_hierarchy)
            
            # 构建prompt
            prompt = f"""
            请分析以下技术支持描述，并从给定的类别层级中选择最合适的最小子类别进行分类。
            请只返回一个最具体的子类别（最深层级的类别）。

            描述文本：
            {description}

            可选的类别层级：
            {formatted_hierarchy}

            请以JSON格式返回结果，包含以下字段：
            1. categories: 包含一个元素的列表，表示最合适的最小子类别
            2. confidence_scores: 对应的置信度（0-1之间的浮点数）
            3. explanation: 选择该类别的理由说明

            示例返回格式：
            {{
                "categories": ["音频设备问题"],
                "confidence_scores": [0.9],
                "explanation": "根据描述中提到的音频设备故障特征，该问题属于音频设备问题类别。"
            }}
            """

            # 获取LLM的分析结果
            response = self._call_azure_llm(prompt)
            result = self._parse_llm_response(response)
            logger.info(f"LLM原始分析结果: {result}")

            # 确保只返回一个类别
            if result.get('categories'):
                category = result['categories'][0]
                if " - " in category:
                    # 如果返回的是完整路径，只取最后一个类别
                    category = category.split(" - ")[-1].strip()
                    result['categories'] = [category]

            return {
                'categories': result.get('categories', ['未分类']),
                'confidence_scores': result.get('confidence_scores', [0.5]),
                'explanation': result.get('explanation', '')
            }

        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
            return {
                'categories': ['未分类'],
                'confidence_scores': [0.5],
                'explanation': f'分析失败: {str(e)}'
            }

    def _format_category_hierarchy(self, hierarchy: dict, level: int = 0) -> str:
        """
        递归格式化类别层级结构
        """
        if not hierarchy:
            return ""
        
        formatted_lines = []
        indent = "  " * level
        
        for category, value in hierarchy.items():
            # 添加当前类别
            formatted_lines.append(f"{indent}- {category}")
            
            if isinstance(value, dict):
                # 处理子类别
                if 'children' in value:
                    for child in value['children']:
                        if isinstance(child, dict) and 'name' in child:
                            # 添加子类别
                            formatted_lines.append(f"{indent}  - {child['name']}")
                            # 处理三级类别
                            if 'children' in child:
                                for grandchild in child['children']:
                                    if isinstance(grandchild, dict) and 'name' in grandchild:
                                        formatted_lines.append(f"{indent}    - {grandchild['name']}")
        
        return "\n".join(formatted_lines)

    def _get_all_categories(self, hierarchy: dict) -> set:
        """
        递归获取所有类别名称，包括所有层级
        """
        logger.debug(f"正在处理层级: {hierarchy}")
        categories = set()
        
        # 处理当前层级
        if isinstance(hierarchy, dict):
            for key, value in hierarchy.items():
                logger.debug(f"处理键: {key}, 值类型: {type(value)}")
                # 添加当前类别
                categories.add(key)
                
                if isinstance(value, dict):
                    # 处理子类别
                    if 'children' in value:
                        # 添加当前节点的名称
                        if 'name' in value:
                            categories.add(value['name'])
                        # 递归处理子节点
                        for child in value['children']:
                            if isinstance(child, dict) and 'name' in child:
                                categories.add(child['name'])
                                # 继续处理更深层的子节点
                                if 'children' in child:
                                    for grandchild in child['children']:
                                        if isinstance(grandchild, dict) and 'name' in grandchild:
                                            categories.add(grandchild['name'])
                    else:
                        # 处理没有children的节点
                        categories.update(self._get_all_categories(value))
        
        logger.debug(f"当前层级收集到的类别: {categories}")
        return categories - {''}  # 移除空字符串

    def _call_azure_llm(self, prompt: str) -> str:
        """
        调用Azure OpenAI API
        
        Args:
            prompt: 要发送给LLM的提示文本
            
        Returns:
            str: LLM的响应内容
        """
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的技术支持分类专家，擅长分析技术问题并进行准确分类。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"调用Azure LLM失败: {str(e)}")
            raise

    def _parse_llm_response(self, response: str) -> dict:
        """
        解析LLM的响应内容为字典格式
        """
        try:
            # 打印原始响应以便调试
            print("原始响应:", response)
            
            # 如果响应已经是字典格式，直接返回
            if isinstance(response, dict):
                return response
            
            # 确保响应不是空的
            if not response or not isinstance(response, str):
                raise ValueError(f"无效的响应格式: {type(response)}")
            
            # 清理响应文本，移除多余的空格和换行
            cleaned_response = response.strip().replace('\n', '').replace('    ', '')
            print("清理后的响应:", cleaned_response)
            
            # 尝试直接解析JSON
            try:
                result = json.loads(cleaned_response)
                print("成功解析JSON:", result)
            except json.JSONDecodeError:
                # 如果解析失败，尝试提取JSON部分
                import re
                json_pattern = r'\{[^{}]*\}'
                match = re.search(json_pattern, cleaned_response)
                if match:
                    json_str = match.group()
                    print("提取的JSON字符串:", json_str)
                    try:
                        result = json.loads(json_str)
                        print("成功解析提取的JSON:", result)
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误位置: 行 {e.lineno}, 列 {e.colno}")
                        print(f"JSON解析错误信息: {e.msg}")
                        raise
                else:
                    raise Exception("无法从响应中提取有效的JSON格式")
            
            # 确保所有必需的字段都存在
            required_fields = ['categories', 'confidence_scores']
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                logger.warning(f"LLM响应缺少必要字段: {missing_fields}，使用默认值")
                return {
                    "categories": result.get('categories', ["未分类"]),
                    "confidence_scores": [0.5] * len(result.get('categories', ["未分类"])),
                    "explanations": result.get('explanations', ["无解释"])
                }
            
            # 确保置信度在0-1之间
            result['confidence_scores'] = [
                min(max(float(score), 0), 1) 
                for score in result['confidence_scores']
            ]
            
            print("最终处理结果:", result)
            return result
            
        except Exception as e:
            print(f"解析LLM响应时出现错误: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print(f"原始响应内容: {response}")
            logger.error(f"解析LLM响应失败: {str(e)}")
            return {
                "categories": ["未分类"],
                "confidence_scores": [0.5],
                "explanations": ["解析失败"]
            }

    def generate_email(self, reference_emails: str, progress_description: str, case_info: dict) -> str:
        """
        基于参考案例的历史邮件和当前进度生成新的邮件内容
        
        Args:
            reference_emails: 参考案例的历史邮件内容
            progress_description: 当前进度描述
            case_info: 案例的基本信息
        
        Returns:
            str: 生成的邮件内容
        """
        try:
            prompt = f"""
            你是一个专业的技术支持工程师，需要根据案例基本信息来对相关用户回复一封邮件，根据当前进度的描述，给出合适的指导意见，你需要以参考案例的历史邮件作为参考，生成一封新的进度更新邮件。

            参考案例的历史邮件内容：
            {reference_emails}

            当前进度描述：
            {progress_description}

            案例基本信息：
            {case_info}
            
            要求：
            1. 保持专业、礼貌的语气
            2. 参考历史邮件的格式和风格
            3. 包含问候语和结束语
            4. 清晰描述当前的处理进度
            5. 如果有下一步计划，请一并说明
            6. 保持邮件简洁明了
            7. 使用中文编写

            请直接生成邮件内容，不要添加任何额外的说明。
            """

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的技术支持工程师，擅长编写技术支持邮件。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # 适当提高创造性
                max_tokens=1000   # 允许较长的回复
            )

            email_content = response.choices[0].message.content.strip()
            
            # 如果返回的内容包含多余的引号或格式标记，清理它们
            email_content = email_content.strip('`').strip('"')
            
            return email_content

        except Exception as e:
            logger.error(f"生成邮件失败: {str(e)}")
            raise Exception(f"生成邮件失败: {str(e)}")

    def _get_category_with_parents(self, category: str, hierarchy: dict) -> list:
        """
        获取类别及其所有父类别
        返回格式: [一级分类, 二级分类, 三级分类]
        """
        logger.info(f"开始查找类别 '{category}' 的父类")
        
        # 如果输入的类别包含完整路径（用 " - " 分隔），先尝试提取最后一个类别
        if " - " in category:
            categories = category.split(" - ")
            target_category = categories[-1].strip()  # 获取最后一个类别名称
            logger.info(f"从完整路径中提取目标类别: {target_category}")
        else:
            target_category = category
        
        def search_in_hierarchy(current_category: str, current_hierarchy: dict, path: list = None) -> list:
            if path is None:
                path = []
                
            for level1, value1 in current_hierarchy.items():
                logger.debug(f"检查一级分类: {level1}")
                current_path = [level1]
                
                # 检查一级分类是否匹配
                if current_category == level1:
                    logger.info(f"找到一级分类匹配: {current_path}")
                    return current_path
                
                if isinstance(value1, dict):
                    logger.debug(f"检查 {level1} 的子分类")
                    # 检查二级分类
                    if 'children' in value1:
                        for child in value1['children']:
                            if isinstance(child, dict):
                                child_name = child.get('name')
                                logger.debug(f"检查二级分类: {child_name}")
                                if child_name == current_category:
                                    current_path.append(child_name)
                                    logger.info(f"找到二级分类匹配，完整路径: {current_path}")
                                    return current_path
                                
                                # 检查三级分类
                                if 'children' in child:
                                    for grandchild in child['children']:
                                        if isinstance(grandchild, dict):
                                            grandchild_name = grandchild.get('name')
                                            logger.debug(f"检查三级分类: {grandchild_name}")
                                            if grandchild_name == current_category:
                                                current_path.extend([child_name, grandchild_name])
                                                logger.info(f"找到三级分类匹配，完整路径: {current_path}")
                                                return current_path
            
            logger.warning(f"未找到类别 '{current_category}' 的父类")
            return []

        # 使用提取出的目标类别进行搜索
        result = search_in_hierarchy(target_category, hierarchy)
        if not result and " - " in category:
            # 如果使用最后一个类别没找到，尝试使用完整路径中的其他部分
            for cat in category.split(" - "):
                cat = cat.strip()
                result = search_in_hierarchy(cat, hierarchy)
                if result:
                    break
        
        logger.info(f"类别 '{category}' 的最终完整路径: {result}")
        return result
