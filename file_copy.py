'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-17 10:29:55
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-17 11:06:11
FilePath: \Case_KB\file_copy.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
import shutil
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('file_copy.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def copy_files():
    # 源目录和目标目录
    source_dir = r"\\10.0.37.113\共享文件\二线团队及流程资料\Python\2024-12-16_15-04-09"
    pdf_target_dir = r"E:\Case_KB\emails"
    txt_target_dir = r"E:\Case_KB\emails_words"
    
    # 确保目标目录存在
    Path(pdf_target_dir).mkdir(parents=True, exist_ok=True)
    Path(txt_target_dir).mkdir(parents=True, exist_ok=True)
    
    # 计数器
    pdf_count = 0
    txt_count = 0
    
    try:
        # 遍历所有子目录和文件
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                source_file = os.path.join(root, file)
                
                try:
                    # 处理 PDF 文件
                    if file.lower().endswith('.pdf'):
                        target_file = os.path.join(pdf_target_dir, file)
                        shutil.copy2(source_file, target_file)
                        pdf_count += 1
                        logger.info(f"已复制 PDF 文件: {file}")
                    
                    # 处理 TXT 文件
                    elif file.lower().endswith('.txt'):
                        target_file = os.path.join(txt_target_dir, file)
                        shutil.copy2(source_file, target_file)
                        txt_count += 1
                        logger.info(f"已复制 TXT 文件: {file}")
                        
                except Exception as e:
                    logger.error(f"复制文件 {file} 时出错: {str(e)}")
                    
        logger.info(f"复制完成！共复制 {pdf_count} 个 PDF 文件和 {txt_count} 个 TXT 文件")
        print(f"复制完成！共复制 {pdf_count} 个 PDF 文件和 {txt_count} 个 TXT 文件")
        
    except Exception as e:
        logger.error(f"遍历目录时出错: {str(e)}")
        print(f"发生错误: {str(e)}")

def delete_null_files():
    # 目标目录
    pdf_dir = r"E:\Case_KB\emails"
    txt_dir = r"E:\Case_KB\emails_words"
    
    # 计数器
    deleted_count = 0
    
    try:
        # 处理两个目录
        for directory in [pdf_dir, txt_dir]:
            for file in os.listdir(directory):
                if "_Null" in file:
                    try:
                        file_path = os.path.join(directory, file)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"已删除文件: {file}")
                    except Exception as e:
                        logger.error(f"删除文件 {file} 时出错: {str(e)}")
        
        logger.info(f"删除完成！共删除 {deleted_count} 个包含'_Null'的文件")
        print(f"删除完成！共删除 {deleted_count} 个包含'_Null'的文件")
        
    except Exception as e:
        logger.error(f"删除文件时出错: {str(e)}")
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    #copy_files()
    delete_null_files()  # 添加这行来执行删除操作

