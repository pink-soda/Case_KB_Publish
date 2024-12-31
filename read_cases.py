'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-30 16:23:22
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-30 17:10:48
FilePath: \Case_KB\read_cases.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import pyodbc
import pandas as pd
from datetime import datetime, timedelta
import time

# 定义字段映射关系
COLUMN_MAPPING = {
    'TicketNumber':'案例编号',
    'AccountIdName':'客户名称',
    'cmit_name':'联系人',
    'cmit_cellphone':'联系电话',
    'EmailAddress':'联系人邮箱',
    'Title':'案例标题',
    'OwnerIdName':'case owner',
    'Description':'案例定义',
    'StatusCode':'案例进度',
    'cmit_productidName':'系统版本',
    'cmit_companyname':'公司名称',
    'cmit_officephone':'公司电话'
}

def connect_to_sql():
    """建立与SQL Server的连接"""
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=10.0.19.41;"
        "DATABASE=CMIT_MSCRM;"
        "UID=crm_reader;"
        "PWD=1qaz@WSX"
    )
    
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"连接数据库时出错: {str(e)}")
        return None

def get_case_data(conn, ticket_numbers):
    """从Incident和Task表获取数据"""
    try:
        # 将案例编号列表转换为SQL IN子句的格式
        ticket_list = "','".join(ticket_numbers)
        
        # 从Incident表查询
        incident_query = f"""
        SELECT 
            i.TicketNumber, 
            i.Title, 
            i.OwnerIdName, 
            CASE i.StatusCode
                WHEN 1 THEN '正在进行'
                WHEN 5 THEN '问题已解决'
                WHEN 6 THEN '已取消'
                WHEN 1000 THEN '提供的信息'
                WHEN 2000 THEN '案例合并'
                ELSE '未知状态'
            END AS StatusCodeText, 
            i.AccountIdName, 
            i.Description, 
            i.cmit_productidName, 
            c.cmit_name, 
            c.cmit_cellphone, 
            c.EmailAddress, 
            c.cmit_companyname, 
            c.cmit_officephone
        FROM 
            [CMIT_MSCRM].[dbo].[Incident] i 
        JOIN 
            [dbo].[cmit_casecontact] c 
        ON 
            i.cmit_casecontactid = c.cmit_casecontactId
        WHERE 
            ticketnumber = {ticket_list}'
        """
        # 使用pandas读取数据
        df_incident = pd.read_sql(incident_query, conn)
        
        # 重命名列以匹配本地CSV
        df_incident = df_incident.rename(columns=COLUMN_MAPPING)
        
        return df_incident
        
    except Exception as e:
        print(f"查询数据时出错: {str(e)}")
        return None

def update_csv(sql_data, csv_path="cases.csv"):
    """更新本地CSV文件"""
    try:
        # 尝试不同的编码方式读取CSV文件
        try:
            df_local = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df_local = pd.read_csv(csv_path, encoding='gbk')
            except UnicodeDecodeError:
                df_local = pd.read_csv(csv_path, encoding='gb2312')
        
        # 确保案例编号列存在
        if '案例编号' not in df_local.columns:
            raise ValueError("CSV文件中没有找到'案例编号'列")
        
        # 为每个案例编号更新对应的字段
        for index, row in sql_data.iterrows():
            mask = df_local['案例编号'] == row['案例编号']
            for col in COLUMN_MAPPING.values():
                if col in row and col in df_local.columns:
                    df_local.loc[mask, col] = row[col]
        
        # 添加更新时间列
        df_local['更新时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存更新后的CSV文件时使用 utf-8-sig 编码（带BOM），这样Excel也能正确显示中文
        df_local.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"数据已成功更新到 {csv_path}")
        
    except Exception as e:
        print(f"更新CSV文件时出错: {str(e)}")

def get_cases_to_update(csv_path="cases.csv"):
    """获取需要更新的案例编号"""
    try:
        # 尝试不同的编码方式读取CSV文件
        try:
            df_local = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df_local = pd.read_csv(csv_path, encoding='gbk')
            except UnicodeDecodeError:
                df_local = pd.read_csv(csv_path, encoding='gb2312')
        
        # 确保必要的列存在
        if '案例编号' not in df_local.columns:
            raise ValueError("CSV文件中没有找到'案例编号'列")
            
        # 获取当前时间
        current_time = datetime.now()
        
        # 如果没有更新时间列，添加该列并设置为空
        if '更新时间' not in df_local.columns:
            df_local['更新时间'] = None
            
        # 将更新时间列转换为datetime类型，无效日期设为None
        df_local['更新时间'] = pd.to_datetime(df_local['更新时间'], errors='coerce')
        
        # 筛选出需要更新的行（更新时间为空或小于当前时间的行）
        mask = (df_local['更新时间'].isna()) | (df_local['更新时间'] < current_time)
        cases_to_update = df_local.loc[mask, '案例编号'].dropna().unique().tolist()
        
        if cases_to_update:
            print(f"找到 {len(cases_to_update)} 个需要更新的案例")
        
        return cases_to_update
        
    except Exception as e:
        print(f"读取CSV文件时出错: {str(e)}")
        return []

def main():
    try:
        # 获取需要更新的案例编号
        ticket_numbers = get_cases_to_update()
        
        if not ticket_numbers:
            print("没有需要更新的案例")
            return
            
        # 连接数据库
        conn = connect_to_sql()
        if conn is None:
            return
        
        try:
            # 获取数据
            df_sql = get_case_data(conn, ticket_numbers)
            if df_sql is not None and not df_sql.empty:
                # 更新CSV
                update_csv(df_sql)
            else:
                print("未找到匹配的数据")
                
        finally:
            # 关闭数据库连接
            conn.close()
            
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

def monitor_cases(interval_minutes=5):
    """持续监控案例更新，每隔指定时间检查一次"""
    print(f"开始监控案例更新，检查间隔：{interval_minutes}分钟")
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始检查更新...")
            main()
            time.sleep(interval_minutes * 60)  # 转换为秒
            
        except KeyboardInterrupt:
            print("\n监控已停止")
            break
        except Exception as e:
            print(f"监控过程出错: {str(e)}")
            time.sleep(60)  # 发生错误时等待1分钟后继续

if __name__ == "__main__":
    monitor_cases()  # 替换原来的 main() 