from email_classifier import EmailClassifier
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # 初始化分类器
        logger.info("开始初始化邮件分类器...")
        email_dir = r"E:\Case_KB\emails_words"
        classifier = EmailClassifier(email_dir)
        logger.info("邮件分类器初始化完成")
        
        # 进行分类
        logger.info("开始进行邮件分类...")
        results = classifier.classify_emails()
        logger.info(f"邮件分类完成，共处理 {len(results)} 个文件")
        
        # 保存结果
        logger.info("开始保存分类结果...")
        output_file = 'email_classification_results.json'
        classifier.save_results(results, output_file)
        logger.info(f"分类结果已保存到 {output_file}")
        
        # 打印分类统计
        print("\n分类统计:")
        for category in classifier.categories:
            print(f"{category}: {len(classifier.categories[category])}封邮件")
            
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 