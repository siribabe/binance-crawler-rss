"""
主入口文件
用于运行爬虫并生成RSS feed
"""
import os
import sys
from crawler import BinanceBlogCrawler
from rss_generator import RSSGenerator


def main():
    """
    主函数：爬取博客并生成RSS feed
    """
    print("=" * 60)
    print("币安博客RSS Feed生成器")
    print("=" * 60)
    
    # 配置参数
    blog_url = "https://www.binance.com/en/blog"
    max_articles = 30  # 爬取的文章数量
    fetch_content = True  # 是否获取文章详细内容
    # 根据脚本位置动态计算输出路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "feeds", "binance_blog_feed.xml")
    output_file = os.path.normpath(output_file)
    
    try:
        # 1. 创建爬虫实例并爬取文章
        print("\n[步骤 1/3] 开始爬取博客文章...")
        crawler = BinanceBlogCrawler(base_url=blog_url)
        articles = crawler.crawl_blog(
            max_articles=max_articles,
            fetch_content=fetch_content
        )
        
        if not articles:
            print("错误: 未能爬取到任何文章")
            return
        
        print(f"[OK] 成功爬取 {len(articles)} 篇文章")
        
        # 2. 生成RSS feed
        print("\n[步骤 2/3] 生成RSS feed...")
        generator = RSSGenerator(
            feed_title="Binance Blog",
            feed_description="Latest articles from Binance Blog",
            feed_link=blog_url,
            feed_language="en"
        )
        
        output_path = generator.generate_rss(articles, output_file)
        print(f"[OK] RSS feed已生成")
        
        # 3. 显示结果
        print("\n[步骤 3/3] 完成!")
        print(f"\nRSS Feed文件位置: {os.path.abspath(output_path)}")
        print(f"\n文章列表:")
        for i, article in enumerate(articles[:5], 1):  # 只显示前5篇
            print(f"  {i}. {article['title'][:60]}...")
        if len(articles) > 5:
            print(f"  ... 还有 {len(articles) - 5} 篇文章")
        
        print("\n" + "=" * 60)
        print("提示: 如果RSS feed格式不正确，请检查网站HTML结构")
        print("      并修改 crawler.py 中的选择器")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'crawler' in locals():
            crawler.close()


if __name__ == '__main__':
    main()

