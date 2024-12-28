'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-12 11:07:46
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-28 00:43:31
FilePath: \Case_KB\process_emails.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
import json
from category_classifier import CategoryHierarchyBuilder
from llm_handler import LLMHandler
import fitz  # 确保在文件顶部导入 PyMuPDF
import traceback
import requests  # 添加到文件顶部的导入语句中
import time
import logging

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

def get_email_files(email_folder: str) -> list:
    """获取邮件文件列表"""
    email_files = []
    for root, _, files in os.walk(email_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                # 使用正斜杠拼接路径
                path = os.path.join(root, file).replace('\\', '/')
                # 确保路径以 ./ 开头
                if not path.startswith('./'):
                    path = './' + path
                email_files.append(path)
    return email_files

def read_email_content(file_path):
    """读取邮件文件内容"""
    try:
        if file_path.lower().endswith('.pdf'):
            # 使用 PyMuPDF 读取 PDF 文件
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        else:
            # 对于其他类型的文件，尝试作为文本文件读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
    except Exception as e:
        print(f"无法读取文件 {file_path}: {str(e)}")
        return None

def save_results(hierarchy: dict, cases: list, hierarchy_file: str, cases_file: str):
    """保存分类结果到文件"""
    try:
        # 只有当文件路径包含目录时才创建目录
        hierarchy_dir = os.path.dirname(hierarchy_file)
        cases_dir = os.path.dirname(cases_file)
        
        if hierarchy_dir:
            os.makedirs(hierarchy_dir, exist_ok=True)
        if cases_dir:
            os.makedirs(cases_dir, exist_ok=True)
        
        # 保存层级结构
        with open(hierarchy_file, 'w', encoding='utf-8') as f:
            json.dump(hierarchy, f, ensure_ascii=False, indent=2)
        
        # 保存案例数据
        with open(cases_file, 'w', encoding='utf-8') as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise Exception(f"保存结果失败: {str(e)}")

def create_initial_hierarchy(email_folder: str, hierarchy_file: str, cases_file: str) -> dict:
    """创建初始的分类层级结构"""
    try:
        # 获取邮件文件列表
        email_files = get_email_files(email_folder)
        if not email_files:
            raise Exception("未找到邮件文件")
        
        # 初始化分类器
        llm_handler = LLMHandler()
        builder = CategoryHierarchyBuilder(llm_handler, cases_file=cases_file)
        
        processed_count = 0
        retry_delay = 3  # 初始重试延迟时间（秒）
        
        # 处理每个邮件文件
        for i, file_path in enumerate(email_files, 1):
            try:
                print(f"处理第 {i}/{len(email_files)} 个文件: {file_path}")
                
                # 读取邮件内容
                email_content = read_email_content(file_path)
                if not email_content:
                    print(f"警告：文件 {file_path} 内容为空，跳过")
                    continue
                
                # 处理案例
                result = builder.process_case(email_content, file_path)
                processed_count += 1
                
                # 定期保存结果
                if processed_count % 2 == 0 or i == len(email_files):
                    save_results(
                        builder.get_current_hierarchy(),
                        builder.get_classified_cases(),
                        'category_hierarchy.json',
                        'classified_cases.json'
                    )
                
            except Exception as e:
                error_msg = f"处理文件 {file_path} 时出错: {str(e)}"
                print(error_msg)
                
                # 检查是否是API限流错误
                if "Azure OpenAI API 限流错误" in str(e):
                    print(f"API限流，等待{retry_delay}秒后继续...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    i -= 1  # 重试当前文件
                    continue
                
                logger.error(error_msg)
                logger.error("错误详情:", exc_info=True)
        
        if processed_count == 0:
            raise Exception("没有成功处理任何文件")
        
        # 最后保存一次结果
        save_results(
            builder.get_current_hierarchy(),
            builder.get_classified_cases(),
            'category_hierarchy.json',
            'classified_cases.json'
        )
        
        # 返回构建的层级结构
        return builder.get_current_hierarchy()
        
    except Exception as e:
        error_msg = f"创建分类层级结构失败: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        logger.error("错误详情:", exc_info=True)
        raise Exception(error_msg)

def load_existing_data(hierarchy_file, cases_file):
    """加载现有的分类层级和案例数据"""
    hierarchy = {}
    cases = []
    
    if os.path.exists(hierarchy_file):
        with open(hierarchy_file, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
    
    if os.path.exists(cases_file):
        with open(cases_file, 'r', encoding='utf-8') as f:
            cases = json.load(f)
    
    return hierarchy, cases

def get_processed_files(cases):
    """从已处理的案例中获取已处理的文件列表"""
    processed = set()
    for case in cases:
        path = case.get('file_path', '')
        # 标准化路径格式
        normalized_path = path.replace('\\', '/')
        if not normalized_path.startswith('./'):
            normalized_path = './' + normalized_path
        processed.add(normalized_path)
    return processed

def find_new_files(email_folder_path, processed_files):
    """查找新添加的邮件文件"""
    new_files = []
    for root, _, files in os.walk(email_folder_path):
        for file in files:
            if file.endswith('.pdf'):
                file_path = os.path.join(root, file)
                # 标准化路径格式
                normalized_path = file_path.replace('\\', '/')
                if not normalized_path.startswith('./'):
                    normalized_path = './' + normalized_path
                # 检查是否已处理
                if normalized_path not in processed_files:
                    new_files.append(normalized_path)
                    print(f"发现新文件: {normalized_path}")  # 添加调试日志
    print(f"已处理文件列表: {processed_files}")  # 添加调试日志
    return new_files

def update_hierarchy(email_folder_path, hierarchy_file, cases_file):
    """更新现有的分类层级结构"""
    try:
        # 加载现有数据
        existing_hierarchy, existing_cases = load_existing_data(hierarchy_file, cases_file)
        processed_files = get_processed_files(existing_cases)
        
        # 查找新文件
        new_files = find_new_files(email_folder_path, processed_files)
        
        if not new_files:
            print("没有发现新的邮件文件")
            return
        
        # 始化LLM处理器和分类构建器
        llm_handler = LLMHandler()
        builder = CategoryHierarchyBuilder(llm_handler, cases_file=cases_file)
        
        # 如果有现有数据，将其加载到builder中
        if existing_hierarchy:
            builder.hierarchy = existing_hierarchy
        if existing_cases:
            builder.classified_cases = existing_cases
        
        total_files = len(new_files)
        print(f"找到 {total_files} 个新邮件文件")
        
        # 处理每个新邮件文件
        for i, email_file in enumerate(new_files, 1):
            print(f"处理第 {i}/{total_files} 个新文件: {email_file}")
            
            # 读取邮件内容
            email_content = read_email_content(email_file)
            if email_content is None:
                continue
            
            try:
                # 处理邮件并获取分类结果
                result = builder.process_case(email_content, email_file)
                
                # 添加文件路径到案例中
                builder.classified_cases[-1]['file_path'] = email_file
                
                print(f"分类结果: {result}")
                
                # 定期保存分类层级结构
                if i % 10 == 0 or i == total_files:
                    save_results(
                        builder.get_current_hierarchy(),
                        builder.get_classified_cases(),
                        hierarchy_file,
                        cases_file
                    )
                    
            except Exception as e:
                print(f"处理文件 {email_file} 时出错: {str(e)}")
                print(f"错误详情: ", traceback.format_exc())
                continue
        
        # 最后保存一次结果
        save_results(
            builder.get_current_hierarchy(),
            builder.get_classified_cases(),
            hierarchy_file,
            cases_file
        )
        print("分类层级结构更新完成！")
        
        # 发送GET请求刷新页面
        try:
            requests.get('http://127.0.0.1:5000/email-classification')
        except:
            pass  # 忽略请求可能的错误
        
        return {
            'status': 'success',
            'hierarchy': builder.get_current_hierarchy(),
            'cases': builder.get_classified_cases()
        }
        
    except Exception as e:
        error_msg = f"更新分类层级结构失败: {str(e)}\n错误详情:\n{traceback.format_exc()}"
        print(error_msg)
        raise Exception(error_msg)

def process_classification_result(result):
    """处理分类结果，确保空值被正确处理"""
    return {
        'level1': result.get('level1') or "案例中不存在该级别分类",
        'level2': result.get('level2') or "案例中不存在该级别分类",
        'level3': result.get('level3') or "案例中不存在该级别分类",
        'confidence': {
            'level1': float(result.get('similarity', {}).get('level1', 0)),
            'level2': float(result.get('similarity', {}).get('level2', 0)),
            'level3': float(result.get('similarity', {}).get('level3', 0))
        }
    }

#def save_hierarchy(hierarchy, file_path):
#    with open(file_path, 'w', encoding='utf-8') as f:
#        json.dump(hierarchy, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # 设置输入输出路径
    email_folder = ".\emails"  # 邮件文件夹路径
    hierarchy_file = ".\category_hierarchy.json"  # 分类层级结构文件
    cases_file = ".\classified_cases.json"  # 分类案例文件
    
    # 检查是否存在分类文件
    if not os.path.exists(hierarchy_file) or not os.path.exists(cases_file):
        print("首次运行，创建初始分类层级结构...")
        hierarchy = create_initial_hierarchy(email_folder, hierarchy_file, cases_file)
        save_results(hierarchy, [], hierarchy_file, cases_file)
    else:
        print("更新现有分类层级结构...")
        update_hierarchy(email_folder, hierarchy_file, cases_file) 