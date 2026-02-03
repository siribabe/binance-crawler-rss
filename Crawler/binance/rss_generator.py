"""
RSS Feed生成器模块
用于将爬取的文章生成RSS格式的feed
"""
from feedgen.feed import FeedGenerator
from typing import List, Dict
from datetime import datetime
from datetime import timezone
import re
import hashlib
import xml.etree.ElementTree as ET

class RSSGenerator:
    def __init__(self, 
                 feed_title: str = "Binance Blog",
                 feed_description: str = "Latest articles from Binance Blog",
                 feed_link: str = "https://www.binance.com/en/blog",
                 feed_language: str = "en"):
        """
        初始化RSS生成器
        
        Args:
            feed_title: Feed标题
            feed_description: Feed描述
            feed_link: Feed链接
            feed_language: Feed语言
        """
        self.fg = FeedGenerator()
        self.fg.title(feed_title)
        self.fg.description(feed_description)
        self.fg.link(href=feed_link, rel='alternate')
        self.fg.language(feed_language)
        self.fg.lastBuildDate(datetime.now(timezone.utc))
        self.fg.generator('Binance Blog RSS Generator')
    
    def parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串为datetime对象
        
        Args:
            date_str: 日期字符串
            
        Returns:
            datetime对象，如果解析失败则返回当前时间
        """
        if not date_str:
            return datetime.now(timezone.utc)
        
        # 常见的日期格式
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S+00:00',
            '%B %d, %Y',
            '%d %B %Y',
            '%m/%d/%Y',
        ]
        
        # 尝试从ISO格式或datetime属性中提取
        iso_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', date_str)
        if iso_match:
            date_str = iso_match.group(1).replace('T', ' ')
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        
        # 如果都失败了，返回当前时间
        print(f"无法解析日期: {date_str}, 使用当前时间")
        return datetime.now(timezone.utc)
    
    def add_article(self, article: Dict):
        """
        添加一篇文章到RSS feed
        
        Args:
            article: 文章字典，包含 title, link, date, description, content 等
        """
        fe = self.fg.add_entry()
        
        # 标题
        fe.title(article.get('title', 'Untitled'))
        
        # 链接
        fe.link(href=article.get('link', ''))
        
        # 描述（短摘要；完整正文在 content:encoded 中）
        description = article.get('description', '')
        if not description:
            raw = article.get('content', '') or ''
            # 若正文是 HTML，只取前 500 字符做摘要（可能含标签）
            description = raw[:500] + '...' if len(raw) > 500 else raw
        fe.description(description or '')
        
        # 发布时间
        date_str = article.get('date') or article.get('pub_date', '')
        pub_date = self.parse_date(date_str)
        fe.pubDate(pub_date)
        
        # GUID（唯一标识符，与参考一致用 isPermaLink="false" 的 hash）
        link_for_guid = article.get('link', '')
        if link_for_guid:
            guid_str = hashlib.md5(link_for_guid.encode('utf-8')).hexdigest()
        else:
            guid_str = hashlib.md5(article.get('title', '').encode('utf-8')).hexdigest()
        fe.guid(guid_str, permalink=False)
        
        # 作者（与参考一致，没有时用 "Binance Blog"）
        author = article.get('author', '') or 'Binance Blog'
        fe.author(name=author)
        
        # 分类（如果有）
        category = article.get('category', '')
        if category:
            fe.category(term=category)
    
    def generate_rss(self, articles: List[Dict], output_file: str = 'feeds/binance_blog_feed.xml'):
        """
        生成RSS feed文件
        
        Args:
            articles: 文章列表
            output_file: 输出文件路径
        """
        print(f"正在生成RSS feed，包含 {len(articles)} 篇文章...")
        
        # 按日期排序（最新的在前）
        sorted_articles = sorted(
            articles,
            key=lambda x: self.parse_date(x.get('date') or x.get('pub_date', '')),
            reverse=True
        )
        
        # 添加每篇文章
        for article in sorted_articles:
            self.add_article(article)
        
        # 生成RSS文件
        import os
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        
        self.fg.rss_file(output_file, pretty=True)

        # 后处理：补上 xmlns、dc:identifier、dc:creator、content:encoded，与参考格式一致
        self._patch_rss_for_reference_format(output_file, sorted_articles)

        print(f"RSS feed已生成: {output_file}")
        
        return output_file

    def _patch_rss_for_reference_format(self, output_file: str, sorted_articles: List[Dict]):
        """
        对已生成的 RSS 文件做后处理，补上 xmlns、dc:identifier、dc:creator、content:encoded，
        使输出与参考的 cdn.feedcontrol.net 格式一致。
        """
        NS = {
            'atom': 'http://www.w3.org/2005/Atom',
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'media': 'http://search.yahoo.com/mrss/',
        }

        tree = ET.parse(output_file)
        root = tree.getroot()
        """
        # 1) 给根元素 <rss> 加上命名空间属性（仅当尚未存在时添加，避免 xmlns:dc redefined）
        ns_to_set = {
            'xmlns:atom': NS['atom'],
            'xmlns:content': NS['content'],
            'xmlns:dc': NS['dc'],
            'xmlns:media': NS['media'],
        }
        for attr_name, attr_value in ns_to_set.items():
            if attr_name not in root.attrib:
                root.set(attr_name, attr_value)
        if 'version' not in root.attrib:
            root.set('version', '2.0')
        """

        # 2) 找到 channel，再找到其下所有 item
        channel = root.find('channel')
        if channel is None:
            return
        items = list(channel.findall('item'))

        # 3) 按顺序与 sorted_articles 一一对应，为每个 item 插入 dc:identifier、dc:creator、content:encoded
        for i, item in enumerate(items):
            if i >= len(sorted_articles):
                break
            article = sorted_articles[i]
            link = article.get('link', '')
            author = article.get('author', '') or 'Binance Blog'
            content = article.get('content', '')

            # 纯文本正文转成简单 HTML（与参考里 content:encoded 为 HTML 一致）
            if content and not content.strip().startswith('<'):
                import html
                content = '<p>' + html.escape(content).replace('\n', '</p><p>') + '</p>'

            def make_element(tag: str, text: str, ns_key: str):
                el = ET.Element('{' + NS[ns_key] + '}' + tag)
                el.text = (text or '').strip()
                return el

            # dc:identifier = link
            item.append(make_element('identifier', link, 'dc'))
            # dc:creator = author
            item.append(make_element('creator', author, 'dc'))
            # content:encoded = 正文 HTML
            enc = ET.Element('{' + NS['content'] + '}encoded')
            enc.text = (content or '').strip()
            item.append(enc)

        # 让 content 命名空间输出为 content:encoded，而不是 ns1:encoded
        ET.register_namespace('content', NS['content'])
        ET.register_namespace('dc', NS['dc'])
        # 避免 feedgen 已有的 xmlns 与 ET 写回时自动补的声明重复，导致 "xmlns:dc redefined"
        root.attrib.pop('xmlns:dc', None)
        root.attrib.pop('xmlns:content', None)
        
        tree.write(output_file, encoding='utf-8', default_namespace=None, method='xml')
    
    def get_rss_string(self) -> str:
        """
        获取RSS字符串（用于直接输出或通过API返回）
        
        Returns:
            RSS XML字符串
        """
        return self.fg.rss_str(pretty=True).decode('utf-8')


if __name__ == '__main__':
    # 测试代码
    generator = RSSGenerator()
    
    # 示例文章
    test_articles = [
        {
            'title': 'Test Article 1',
            'link': 'https://www.binance.com/en/blog/test-1',
            'date': '2024-01-15',
            'description': 'This is a test article',
            'content': 'Full content of the test article...',
            'author': 'Test Author',
            'category': 'Test'
        }
    ]
    
    generator.generate_rss(test_articles, 'feeds/test_feed.xml')
    print("测试完成")
