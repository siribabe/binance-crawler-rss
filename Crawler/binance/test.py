from crawler import BinanceBlogCrawler

# 测试爬取少量文章
crawler = BinanceBlogCrawler()
try:
    articles = crawler.crawl_blog(max_articles=3, fetch_content=False)
    print(f"\n成功爬取 {len(articles)} 篇文章\n")
    
    for i, article in enumerate(articles, 1):
        print(f"文章 {i}:")
        print(f"  标题: {article.get('title', 'N/A')[:60]}")
        print(f"  链接: {article.get('link', 'N/A')[:80]}")
        print(f"  日期: {article.get('date', 'N/A')}")
        print()
finally:
    crawler.close()