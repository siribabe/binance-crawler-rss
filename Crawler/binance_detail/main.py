"""
主入口文件
"""
import os
import sys
from crawler import BinanceSquareCrawler
from rss_generator import RSSGenerator


def main():
    print("=" * 60)
    print("Binance Square RSS 详情爬虫")
    print("=" * 60)
    
    # 配置
    rss_url = "https://rss.app/feeds/yRmgWoblxWMXGv0F.xml"
    max_articles = 50
    fetch_content = True
    
    # 输出路径（动态计算）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "feeds", "binance_square_feed.xml")
    output_file = os.path.normpath(output_file)
    
    crawler = None
    try:
        # 1. 爬取文章
        print("\n[步骤 1/2] 爬取文章...")
        crawler = BinanceSquareCrawler(rss_url=rss_url)
        articles = crawler.crawl(max_articles=max_articles, fetch_content=fetch_content)
        
        if not articles:
            print("错误: 未获取到任何文章")
            return
        
        print(f"[OK] 成功爬取 {len(articles)} 篇文章")
        
        # 2. 生成 RSS
        print("\n[步骤 2/2] 生成 RSS feed...")
        generator = RSSGenerator(
            feed_title="Binance Square News",
            feed_description="Latest news from Binance Square with full content",
            feed_link="https://www.binance.com/en/square",
            feed_language="en"
        )
        
        generator.generate_rss(articles, output_file)
        print(f"[OK] RSS feed 已生成: {output_file}")
        
        # 显示结果
        print("\n文章列表:")
        for i, article in enumerate(articles[:5], 1):
            print(f"  {i}. {article['title'][:60]}...")
        if len(articles) > 5:
            print(f"  ... 还有 {len(articles) - 5} 篇文章")
        
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if crawler:
            crawler.close()


if __name__ == '__main__':
    main()