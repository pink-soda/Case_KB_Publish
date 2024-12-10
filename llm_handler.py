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
        """
        max_attempts = 3
        attempt = 0
        last_error = None

        while attempt < max_attempts:
            try:
                attempt += 1
                logger.info(f"尝试第 {attempt} 次分类分析")

                # 构建prompt，根据尝试次数调整提示的严格程度
                category_context = self._format_category_hierarchy(category_hierarchy)
                prompt = f"""
                作为一个专业的技术支持分类专家，请仔细分析以下描述文本，并从给定的类别层级结构中选择最相关的类别。
                {'这是重试分析，请更仔细地考虑各个可能的类别。' if attempt > 1 else ''}

                类别层级结构：
                {category_context}

                描述文本：
                {description}

                请严格按照以下要求进行分析：
                1. 必须从上述类别层级结构中选择类别，不要创建新的类别
                2. 可以选择多个相关类别
                3. 每个选择的类别都需要给出0-1之间的置信度分数
                4. 如果找不到完全匹配的类别，选择最接近的上级类别
                5. 至少返回一个最相关的类别
                {'6. 这是重试分析，如果之前未找到匹配，请考虑更广泛的类别匹配' if attempt > 1 else ''}

                请以JSON格式返回结果，格式如下：
                {{
                    "categories": ["类别1", "类别2"],
                    "confidence_scores": [0.95, 0.85],
                    "explanation": "这里是选择这些类别的详细解释"
                }}
                """

                # 调用Azure LLM API
                response = self._call_azure_llm(prompt)
                logger.debug(f"LLM原始响应: {response}")

                # 解析响应
                result = self._parse_llm_response(response)
                logger.debug(f"解析后的结果: {result}")

                # 获取所有有效类别
                valid_categories = set(self._get_all_categories(category_hierarchy))
                logger.debug(f"有效类别列表: {valid_categories}")

                # 过滤出有效的类别和对应的置信度分数
                valid_indices = [
                    i for i, cat in enumerate(result.get('categories', []))
                    if cat in valid_categories
                ]

                if not valid_indices:
                    logger.warning(f"第 {attempt} 次尝试未找到任何有效的类别匹配")
                    if attempt < max_attempts:
                        last_error = "未找到有效的类别匹配"
                        continue
                    else:
                        # 所有重试都失败后返回默认结果
                        return {
                            'categories': ['未分类'],
                            'confidence_scores': [0.5],
                            'explanation': f'经过 {max_attempts} 次尝试，仍无法找到匹配的类别，建议人工审核。'
                        }

                filtered_result = {
                    'categories': [result.get('categories', [])[i] for i in valid_indices],
                    'confidence_scores': [result.get('confidence_scores', [])[i] for i in valid_indices],
                    'explanation': result.get('explanation', '无分析说明')
                }

                logger.info(f"第 {attempt} 次尝试成功，最终分类结果: {filtered_result}")
                return filtered_result

            except Exception as e:
                last_error = str(e)
                logger.error(f"第 {attempt} 次尝试失败: {last_error}")
                logger.error(traceback.format_exc())
                
                if attempt >= max_attempts:
                    return {
                        'categories': ['未分类'],
                        'confidence_scores': [0.5],
                        'explanation': f'经过 {max_attempts} 次尝试后分析失败: {last_error}'
                    }

    def _format_category_hierarchy(self, hierarchy: dict, level: int = 0) -> str:
        """
        递归格式化类别层级结构
        
        Args:
            hierarchy: 类别层级结构字典
            level: 当前缩进级别
            
        Returns:
            str: 格式化后的类别层级结构文本
        """
        if not hierarchy:
            return ""
        
        formatted_lines = []
        indent = "  " * level
        
        # 处理当前节点
        name = hierarchy.get('name', '')
        if name:
            formatted_lines.append(f"{indent}- {name}")
        
        # 递归处理子节点
        children = hierarchy.get('children', [])
        for child in children:
            child_text = self._format_category_hierarchy(child, level + 1)
            formatted_lines.append(child_text)
        
        return "\n".join(filter(None, formatted_lines))

    def _get_all_categories(self, hierarchy: dict) -> set:
        """
        递归获取所有类别名称
        """
        categories = {hierarchy.get('name', '')}
        for child in hierarchy.get('children', []):
            categories.update(self._get_all_categories(child))
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
            
            # 确保所有必需的字段都存在
            if not all(key in result for key in ['categories', 'confidence_scores']):
                logger.warning("LLM响应缺少必要字段，使用默认值")
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
            
            return result
        except Exception as e:
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
