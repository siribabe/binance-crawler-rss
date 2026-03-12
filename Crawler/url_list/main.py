"""
URL 列表爬虫 - 主入口
从 urls.json 读取 URL 列表，爬取每篇文章并生成 RSS feed
"""
import os
import sys
from crawler import URLListCrawler
from rss_generator import RSSGenerator


def main():
    print("=" * 60)
    print("URL 列表 RSS Feed 生成器")
    print("=" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "feeds", "url_list_feed.xml")
    output_file = os.path.normpath(output_file)
    
    crawler = None
    try:
        print("\n[步骤 1/2] 爬取文章...")
        crawler = URLListCrawler()
        articles = crawler.crawl()
        
        if not articles:
            print("URL 列表为空或爬取失败，跳过 RSS 生成")
            return
        
        print(f"\n[OK] 成功爬取 {len(articles)} 篇文章")
        
        print("\n[步骤 2/2] 生成 RSS feed...")
        generator = RSSGenerator(
            feed_title="URL List Feed",
            feed_description="Articles from custom URL list",
            feed_link="",
            feed_language="en"
        )
        
        generator.generate_rss(articles, output_file)
        print(f"[OK] RSS feed 已生成: {output_file}")
        
        print("\n文章列表:")
        for i, article in enumerate(articles[:5], 1):
            title = (article.get('title') or '')[:60]
            print(f"  {i}. {title}...")
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
