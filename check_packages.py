import pkg_resources
import sys

required_packages = [
    'flask',
    'flask-cors',
    'pandas',
    'pymongo',  # 用于 MongoHandler
]

def check_packages():
    for package in required_packages:
        try:
            pkg_resources.require(package)
            print(f"✓ {package} 已安装")
        except pkg_resources.DistributionNotFound:
            print(f"✗ {package} 未安装")
            print(f"  请运行: pip install {package}")

if __name__ == "__main__":
    print("检查依赖包...")
    check_packages() 