"""
URL 列表爬虫
从 urls.json 读取 URL 列表，逐个访问并提取文章内容，支持不同来源的网页
"""
import json
import os
import time
from typing import List, Dict
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class URLListCrawler:
    def __init__(self, urls_file: str = None):
        """
        初始化爬虫
        
        Args:
            urls_file: urls.json 文件路径，默认为同目录下的 urls.json
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.urls_file = urls_file or os.path.join(script_dir, "urls.json")
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
            chrome_options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.implicitly_wait(10)
    
    def load_urls(self) -> List[str]:
        """
        从 urls.json 加载 URL 列表
        
        Returns:
            URL 字符串列表
        """
        if not os.path.exists(self.urls_file):
            print(f"警告: 配置文件不存在 {self.urls_file}，将使用空列表")
            return []
        
        try:
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"错误: urls.json 格式无效: {e}")
            return []
        
        # 支持两种格式: ["url1", "url2"] 或 {"urls": ["url1", "url2"]}
        if isinstance(data, list):
            urls = data
        elif isinstance(data, dict) and 'urls' in data:
            urls = data['urls']
        else:
            print("错误: urls.json 格式应为 ['url1', 'url2'] 或 {'urls': ['url1', 'url2']}")
            return []
        
        # 过滤有效 URL
        valid_urls = []
        for u in urls:
            if isinstance(u, str) and u.strip().startswith('http'):
                valid_urls.append(u.strip())
        
        return valid_urls
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """提取文章标题"""
        # og:title (Open Graph，多数网站都有)
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # 常规 title 标签
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        
        # twitter:title
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content'].strip()
        
        # 第一个 h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # 从 URL 生成备选标题
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if path:
            return path.split('/')[-1].replace('-', ' ').title()
        return "Untitled"
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """提取发布日期"""
        # time 标签的 datetime 属性
        time_elem = soup.find('time', attrs={'datetime': True})
        if time_elem:
            return time_elem['datetime'].strip()
        
        # article:published_time
        meta_date = soup.find('meta', property='article:published_time')
        if meta_date and meta_date.get('content'):
            return meta_date['content'].strip()
        
        # datePublished
        meta_date = soup.find('meta', attrs={'itemprop': 'datePublished'})
        if meta_date and meta_date.get('content'):
            return meta_date['content'].strip()
        
        return ''
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """提取作者"""
        # meta author
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author and meta_author.get('content'):
            return meta_author['content'].strip()
        
        # article:author
        meta_author = soup.find('meta', property='article:author')
        if meta_author and meta_author.get('content'):
            return meta_author['content'].strip()
        
        # 常见作者选择器
        for sel in ['[rel="author"]', '.author', '.byline', '[itemprop="author"]']:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if text and len(text) < 100:
                    return text
        
        return ''
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取正文内容，使用多种选择器尝试适配不同网站"""
        # 移除脚本和样式
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
            tag.decompose()
        
        # 常见文章正文选择器（按优先级）
        content_selectors = [
            'article',
            '[role="article"]',
            'main',
            '.article-content',
            '.post-content',
            '.content',
            '.entry-content',
            '.post-body',
            'div[class*="richtext"]',
            'div[class*="content"]',
            'div[class*="article-body"]',
            'div[class*="post-body"]',
            '.prose',
        ]
        
        for selector in content_selectors:
            try:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 排除太小的容器（可能是导航等）
                    text_len = len(content_elem.get_text(strip=True))
                    if text_len > 200:
                        content = content_elem.decode_contents()
                        if len(content) > 200:
                            return content
            except Exception:
                continue
        
        # 后备：取 body 内最大的文本块
        body = soup.find('body')
        if body:
            # 找最大的连续文本块
            paragraphs = body.find_all(['p', 'div'], recursive=True)
            best = None
            best_len = 0
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > best_len and len(text) > 100:
                    best = p
                    best_len = len(text)
            if best:
                return best.decode_contents()
        
        return ''
    
    def fetch_article(self, url: str) -> Dict:
        """
        爬取单篇文章
        
        Args:
            url: 文章 URL
            
        Returns:
            文章字典，包含 title, link, date, author, content, description
        """
        try:
            self._init_driver()
            self.driver.get(url)
            time.sleep(3)
            
            # 滚动触发懒加载
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            title = self._extract_title(soup, url)
            date_str = self._extract_date(soup)
            author = self._extract_author(soup)
            content = self._extract_content(soup)
            
            # 描述：正文前 500 字或 og:description
            description = ''
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                description = og_desc['content'].strip()
            if not description and content:
                desc_soup = BeautifulSoup(content, 'lxml')
                desc_text = desc_soup.get_text(separator=' ', strip=True)[:500]
                description = desc_text + '...' if len(desc_text) >= 500 else desc_text
            
            return {
                'title': title,
                'link': url,
                'date': date_str,
                'author': author or 'Unknown',
                'content': content,
                'description': description,
            }
            
        except Exception as e:
            print(f"  获取文章失败 {url[:60]}...: {e}")
            return {
                'title': 'Failed to fetch',
                'link': url,
                'date': '',
                'author': '',
                'content': '',
                'description': str(e),
            }
    
    def crawl(self) -> List[Dict]:
        """
        爬取所有 URL 对应的文章
        
        Returns:
            文章列表
        """
        print("=" * 60)
        print("URL 列表爬虫")
        print("=" * 60)
        
        urls = self.load_urls()
        if not urls:
            print("URL 列表为空，无需爬取")
            return []
        
        print(f"共 {len(urls)} 个 URL 待爬取\n")
        articles = []
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] 正在爬取: {url[:70]}...")
            article = self.fetch_article(url)
            articles.append(article)
            time.sleep(1)  # 避免请求过快
        
        self.articles = articles
        return articles
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
    
    def __del__(self):
        self.close()


if __name__ == '__main__':
    crawler = URLListCrawler()
    try:
        articles = crawler.crawl()
        print(f"\n成功爬取 {len(articles)} 篇文章")
        for a in articles[:3]:
            print(f"  标题: {a['title'][:50]}")
            print(f"  链接: {a['link'][:60]}")
    finally:
        crawler.close()
