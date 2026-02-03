"""
Binance Square RSS 详情爬虫
从现有 RSS 读取文章列表，爬取每篇文章的详细内容
"""
import requests
import xml.etree.ElementTree as ET
import time
import re
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class BinanceSquareCrawler:
    def __init__(self, rss_url: str = "https://rss.app/feeds/yRmgWoblxWMXGv0F.xml"):
        """
        初始化爬虫
        
        Args:
            rss_url: RSS feed 的 URL
        """
        self.rss_url = rss_url
        self.driver = None
        self.articles = []
    
    def _init_driver(self):
        """初始化 Selenium WebDriver"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            self.driver.implicitly_wait(10)
    
    def fetch_rss(self) -> List[Dict]:
        """
        获取并解析 RSS feed
        
        Returns:
            文章基本信息列表
        """
        print(f"正在获取 RSS: {self.rss_url}")
        
        response = requests.get(self.rss_url, timeout=30)
        response.raise_for_status()
        
        # 解析 XML
        root = ET.fromstring(response.content)
        
        # 定义命名空间
        namespaces = {
            'dc': 'http://purl.org/dc/elements/1.1/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'media': 'http://search.yahoo.com/mrss/'
        }
        
        articles = []
        channel = root.find('channel')
        if channel is None:
            print("未找到 channel 元素")
            return []
        
        for item in channel.findall('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pub_date = item.findtext('pubDate', '').strip()
            description = item.findtext('description', '').strip()
            creator = item.findtext('dc:creator', '', namespaces).strip()
            guid = item.findtext('guid', '').strip()
            
            # 跳过分类页面（链接不包含具体文章 ID）
            if '/square/news/' in link and not re.search(r'-\d+$', link):
                print(f"[跳过] 分类页面: {title[:50]}")
                continue
            
            if title and link:
                articles.append({
                    'title': title,
                    'link': link,
                    'date': pub_date,
                    'description': description,
                    'author': creator or 'Binance Square',
                    'guid': guid,
                    'content': ''  # 稍后填充
                })
        
        print(f"从 RSS 解析出 {len(articles)} 篇文章")
        return articles
    
    def fetch_article_content(self, article_url: str) -> str:
        """
        爬取单篇文章的详细内容
        
        Args:
            article_url: 文章 URL
            
        Returns:
            文章正文 HTML
        """
        try:
            self._init_driver()
            
            self.driver.get(article_url)
            time.sleep(3)
            
            # 滚动页面触发懒加载
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 获取页面源码
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            # 尝试多种选择器找到正文内容
            content = ''
            
            # Binance Square 文章正文可能的选择器
            selectors = [
                'div[class*="richtext"]',
                'div[class*="content"]',
                'article',
                'div[class*="post-content"]',
                'div[class*="article-content"]',
            ]
            
            for selector in selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 移除脚本和样式
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'footer', 'header']):
                        tag.decompose()
                    content = content_elem.decode_contents()
                    if len(content) > 100:  # 确保内容有意义
                        break
            
            if not content:
                # 如果找不到正文，使用 description
                print(f"  未找到正文内容，使用描述")
            
            return content
            
        except Exception as e:
            print(f"  获取文章内容失败: {e}")
            return ''
    
    def crawl(self, max_articles: int = 20, fetch_content: bool = True) -> List[Dict]:
        """
        爬取文章
        
        Args:
            max_articles: 最大爬取文章数量
            fetch_content: 是否获取文章详细内容
            
        Returns:
            文章列表
        """
        print("=" * 60)
        print("开始爬取 Binance Square RSS")
        print("=" * 60)
        
        # 1. 获取 RSS 文章列表
        articles = self.fetch_rss()
        
        if not articles:
            print("未获取到任何文章")
            return []
        
        # 限制数量
        articles = articles[:max_articles]
        
        # 2. 获取每篇文章的详细内容
        if fetch_content:
            for i, article in enumerate(articles, 1):
                print(f"[{i}/{len(articles)}] 获取详情: {article['title'][:50]}...")
                content = self.fetch_article_content(article['link'])
                if content:
                    article['content'] = content
                else:
                    # 如果获取不到正文，使用 description
                    article['content'] = article.get('description', '')
                
                time.sleep(1)  # 避免请求过快
        
        self.articles = articles
        return articles
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def __del__(self):
        self.close()


if __name__ == '__main__':
    crawler = BinanceSquareCrawler()
    try:
        articles = crawler.crawl(max_articles=3, fetch_content=True)
        print(f"\n成功爬取 {len(articles)} 篇文章")
        for article in articles:
            print(f"\n标题: {article['title'][:60]}")
            print(f"链接: {article['link'][:80]}")
            print(f"内容长度: {len(article.get('content', ''))}")
    finally:
        crawler.close()