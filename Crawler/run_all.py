"""
总开关：依次运行所有爬虫
"""
import subprocess
import sys
import os
from datetime import datetime


def run_crawler(crawler_name: str, script_path: str) -> bool:
    """
    运行单个爬虫
    
    Args:
        crawler_name: 爬虫名称（用于显示）
        script_path: 脚本路径
    
    Returns:
        是否成功
    """
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始运行: {crawler_name}")
    print(f"{'='*60}")
    
    try:
        # 获取脚本所在目录作为工作目录
        working_dir = os.path.dirname(script_path)
        
        # 运行 Python 脚本
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=working_dir,
            check=False
        )
        
        if result.returncode == 0:
            print(f"\n[OK] {crawler_name} 运行成功")
            return True
        else:
            print(f"\n[失败] {crawler_name} 运行失败，退出码: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n[错误] {crawler_name} 运行出错: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("       Binance 爬虫总开关")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义要运行的爬虫列表
    crawlers = [
        ("Binance Blog 爬虫", os.path.join(base_dir, "binance", "main.py")),
        ("Binance Square 详情爬虫", os.path.join(base_dir, "binance_detail", "main.py")),
    ]
    
    # 统计结果
    results = []
    
    # 依次运行每个爬虫
    for crawler_name, script_path in crawlers:
        if not os.path.exists(script_path):
            print(f"\n[跳过] {crawler_name}: 脚本不存在 ({script_path})")
            results.append((crawler_name, None))
            continue
        
        success = run_crawler(crawler_name, script_path)
        results.append((crawler_name, success))
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("       运行汇总")
    print("=" * 60)
    
    for crawler_name, success in results:
        if success is None:
            status = "⏭️ 跳过"
        elif success:
            status = "✅ 成功"
        else:
            status = "❌ 失败"
        print(f"  {status}  {crawler_name}")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
