"""
币安博客爬虫模块
用于爬取 https://www.binance.com/en/blog 的文章内容
"""
from bs4 import BeautifulSoup
import time
from typing import List, Dict
from datetime import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class BinanceBlogCrawler:
    def __init__(self, base_url: str = "https://www.binance.com/en/blog"):
        """
        初始化爬虫
        
        Args:
            base_url: 博客基础URL
        """
        self.base_url = base_url
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.implicitly_wait(10)
        self.articles = []
    
    def fetch_page(self, url: str, retry: int = 3, wait_selector: str = None) -> BeautifulSoup:
        """
        获取并解析网页（使用Selenium）
        
        Args:
            url: 要获取的URL
            retry: 重试次数
            wait_selector: 等待元素出现的CSS选择器
            
        Returns:
            BeautifulSoup对象
        """
        for attempt in range(retry):
            try:
                self.driver.get(url)
                
                # 增加等待时间，确保页面完全加载
                time.sleep(5)  # 从3秒增加到5秒
                
                # 滚动页面以触发懒加载（如果页面有懒加载）
                # 先滚动到底部，再回到顶部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 等待懒加载内容
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                # 如果提供了等待选择器，等待元素出现
                if wait_selector:
                    try:
                        WebDriverWait(self.driver, 20).until(  # 从15秒增加到20秒
                            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                        )
                        # 额外等待一下，确保内容完全渲染
                        time.sleep(2)
                    except:
                        print(f"警告: 等待选择器 {wait_selector} 未找到，继续执行...")
                
                # 获取页面HTML
                html = self.driver.page_source
                return BeautifulSoup(html, 'lxml')
            except Exception as e:
                if attempt == retry - 1:
                    print(f"获取页面失败 {url}: {e}")
                    raise
                time.sleep(2 ** attempt)
        return None
    
    def extract_article_list(self, soup: BeautifulSoup) -> List[Dict]:
        """
        从博客首页提取文章列表
        
        Args:
            soup: 解析后的HTML
            
        Returns:
            文章信息列表，每个元素包含 title, link, date, category 等
        """
        articles = []
        
        # 使用你提供的选择器路径找到所有文章链接
        article_links = soup.select('#__APP a[href*="/blog/"]')

        # 如果上面找不到，尝试备用选择器
        if not article_links:
            article_links = soup.select('a[href*="/blog/"]')

        articles = []
        for article_index, link_elem in enumerate(article_links, 1):
            try:
                # 提取文章链接
                link = link_elem.get('href', '')
                if not link or '/blog/' not in link:
                    print(f"[跳过] 第 {article_index} 篇：链接无效或不是博客链接。link={repr(link)[:80]}")
                    continue
                
                if not link.startswith('http'):
                    link = f"https://www.binance.com{link}" if link.startswith('/') else f"{self.base_url}/{link}"
                '''
                # 提取标题（优先从链接文本，如果没有则从父容器找）
                title = link_elem.get_text(strip=True)
                if not title:
                    # 尝试从父容器找标题
                    parent = link_elem.find_parent(['div', 'article'])
                    if parent:
                        title_elem = parent.find(['h1', 'h2', 'h3', 'h4', 'span', 'div'], class_=re.compile(r'title|heading', re.I))
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                '''
                # 提取标题
                title = ''

                # 优先查找包含 line-clamp 类的div（标题容器）
                title_elem = link_elem.select_one('div[class*="line-clamp"]')
                if title_elem:
                    title = title_elem.get_text(strip=True)

                    # 调试：打印标题提取信息
                    print(f"\n=== 标题提取调试（第 {article_index} 篇文章）===")
                    print(f"找到的标题元素: {title_elem}")
                    print(f"标题元素HTML: {str(title_elem)[:200]}")
                    print(f"提取的标题: {title}")
                    print(f"标题长度: {len(title)}")
                    print(f"标题元素类名: {title_elem.get('class', [])}")
                    print("=" * 50)

                # 如果没找到，尝试找 text-SecondaryText 类
                if not title:
                    title_elem = link_elem.select_one('div[class*="text-SecondaryText"]')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(articles) == 0:
                            print(f"[第 {article_index} 篇] 使用text-SecondaryText找到标题: {title[:100]}")

                # 如果还是没找到，尝试找 typography-body 类
                if not title:
                    title_elem = link_elem.select_one('div[class*="typography-body"]')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                # 最后的后备方案
                if not title:
                    title = link_elem.get_text(strip=True)
                    print(f"[第 {article_index} 篇] 使用后备方案找到标题: {title[:100]}")


                # 找到包含这个链接的父容器（文章卡片）
                card = link_elem.find_parent(['div', 'article'])
                
                # 提取发布日期
                date_str = ''
                # 先尝试从链接元素内部找
                tertiary_container = link_elem.find('div', class_=lambda x: x and 'text-TertiaryText' in ' '.join(x) if isinstance(x, list) else 'text-TertiaryText' in str(x))
                if tertiary_container:
                    first_div = tertiary_container.find('div', recursive=False)
                    if first_div:
                        date_str = first_div.get_text(strip=True)

                # 如果没找到，再从card中找
                if not date_str and card:
                    tertiary_container = card.find('div', class_=lambda x: x and 'text-TertiaryText' in ' '.join(x) if isinstance(x, list) else 'text-TertiaryText' in str(x))
                    if tertiary_container:
                        first_div = tertiary_container.find('div', recursive=False)
                        if first_div:
                            date_str = first_div.get_text(strip=True)

                # 最后的后备方案
                if not date_str and card:
                    date_elem = card.find(['time', 'span', 'div'], class_=re.compile(r'date|time|published', re.I))
                    if date_elem:
                        date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
                
                # 提取分类
                category = ''
                if card:
                    category_elem = card.find(['span', 'div', 'a'], class_=re.compile(r'category|tag', re.I))
                    if category_elem:
                        category = category_elem.get_text(strip=True)
                
                # 提取摘要/描述
                description = ''
                if card:
                    desc_elem = card.find(['p', 'div'], class_=re.compile(r'description|excerpt|summary', re.I))
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                
                # 提取图片
                image_url = ''
                if card:
                    img_elem = card.find('img')
                    if img_elem:
                        image_url = img_elem.get('src', '') or img_elem.get('data-src', '') or img_elem.get('data-lazy-src', '')
                
                if not title:
                    print(f"[警告] 第 {article_index} 篇文章标题提取失败，链接: {link[:80]}")
                    # 尝试使用链接的最后部分作为标题
                    if link:
                        # 从链接中提取可能的标题（URL的最后部分）
                        link_parts = link.rstrip('/').split('/')
                        if link_parts:
                            potential_title = link_parts[-1].replace('-', ' ').title()
                            print(f"  尝试使用链接生成标题: {potential_title[:50]}")
                            title = potential_title  # 使用生成的标题
                

                if title and link:
                    articles.append({
                        'title': title,
                        'link': link,
                        'date': date_str,
                        'category': category,
                        'description': description,
                        'image_url': image_url
                    })
                else:
                    if not title:
                        print(f"[跳过] 第 {article_index} 篇文章：标题为空")
                    if not link:
                        print(f"[跳过] 第 {article_index} 篇文章：链接为空")
            except Exception as e:
                print(f"提取文章信息时出错: {e}")
                continue
        
        return articles
    
    def extract_article_content(self, article_url: str) -> Dict:
        """
        提取单篇文章的详细内容
        
        Args:
            article_url: 文章URL
            
        Returns:
            包含文章详细信息的字典
        """
        try:
            soup = self.fetch_page(article_url)
            
            # 文章详情页中标题与正文的容器（与你在开发者工具中看到的 JS path 对应）
            # 对应: #__APP > ... > div.bn-flex.flex-col.gap-2.desktop:gap-4
            content_elem = soup.select_one('#__APP div[class*="bn-flex"][class*="flex-col"][class*="gap-2"]')
            content = ''
            if content_elem:
                # 移除脚本和样式，避免把无关内容算进正文
                for tag in content_elem.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                # 先按纯文本取，保证有内容；若你要 content:encoded 用 HTML，可再改为取内部 HTML
                content = content_elem.decode_contents()
            
            # 提取作者
            author_elem = soup.find(['span', 'div', 'a'], class_=re.compile(r'author|writer', re.I))
            author = author_elem.get_text(strip=True) if author_elem else ''
            
            # 提取发布时间（更精确）
            time_elem = soup.find('time', datetime=True) or soup.find(['span', 'div'], class_=re.compile(r'date|published', re.I))
            pub_date = ''
            if time_elem:
                pub_date = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
            
            return {
                'content': content,
                'author': author,
                'pub_date': pub_date
            }
        except Exception as e:
            print(f"提取文章内容失败 {article_url}: {e}")
            return {
                'content': '',
                'author': '',
                'pub_date': ''
            }
    
    def crawl_blog(self, max_articles: int = 20, fetch_content: bool = True) -> List[Dict]:
        """
        爬取博客文章
        
        Args:
            max_articles: 最大爬取文章数量
            fetch_content: 是否获取文章详细内容
            
        Returns:
            文章列表
        """
        print(f"开始爬取 {self.base_url}...")
        
        # 获取博客首页
        soup = self.fetch_page(self.base_url, wait_selector='#__APP a[href*="/blog/"]')
        if not soup:
            print("无法获取博客首页")
            return []
        
        # 提取文章列表
        articles = self.extract_article_list(soup)
        print(f"找到 {len(articles)} 篇文章")
        
        # 限制文章数量
        articles = articles[:max_articles]
        
        # 获取每篇文章的详细内容
        if fetch_content:
            for i, article in enumerate(articles, 1):
                print(f"正在处理第 {i}/{len(articles)} 篇文章: {article['title'][:50]}...")
                content_info = self.extract_article_content(article['link'])
                article.update(content_info)
                
                # 避免请求过快
                time.sleep(1)
        
        self.articles = articles
        return articles
    
    def save_articles_to_file(self, filename: str = 'articles.json'):
        """
        将文章保存到JSON文件（用于调试）
        
        Args:
            filename: 输出文件名
        """
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        print(f"文章已保存到 {filename}")

    def close(self):
        """关闭浏览器"""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass

    def __del__(self):
        """清理浏览器资源"""
        self.close()


if __name__ == '__main__':
    # 测试代码
    crawler = BinanceBlogCrawler()
    articles = crawler.crawl_blog(max_articles=5, fetch_content=True)
    print(f"\n成功爬取 {len(articles)} 篇文章")
    for article in articles:
        print(f"\n标题: {article['title']}")
        print(f"链接: {article['link']}")
        print(f"日期: {article['date']}")