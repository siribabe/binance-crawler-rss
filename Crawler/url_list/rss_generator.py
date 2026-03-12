"""
RSS Feed 生成器
用于将 URL 列表爬虫获取的文章生成 RSS 格式
"""
from feedgen.feed import FeedGenerator
from typing import List, Dict
from datetime import datetime, timezone
import hashlib
import os
import xml.etree.ElementTree as ET


class RSSGenerator:
    def __init__(self,
                 feed_title: str = "URL List Feed",
                 feed_description: str = "Articles from custom URL list",
                 feed_link: str = "",
                 feed_language: str = "en"):
        self.fg = FeedGenerator()
        self.fg.title(feed_title)
        self.fg.description(feed_description)
        self.fg.link(href=feed_link or "about:blank", rel='alternate')
        self.fg.language(feed_language)
        self.fg.lastBuildDate(datetime.now(timezone.utc))
        self.fg.generator('URL List RSS Generator')
    
    def parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S GMT',
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S%z',
            '%B %d, %Y',
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        
        return datetime.now(timezone.utc)
    
    def add_article(self, article: Dict):
        fe = self.fg.add_entry()
        fe.title(article.get('title', 'Untitled'))
        fe.link(href=article.get('link', ''))
        
        description = article.get('description', '')
        if not description:
            content = article.get('content', '')
            description = content[:500] + '...' if len(content) > 500 else content
        fe.description(description or '')
        
        date_str = article.get('date', '')
        pub_date = self.parse_date(date_str)
        fe.pubDate(pub_date)
        
        link = article.get('link', '')
        guid = hashlib.md5(link.encode('utf-8')).hexdigest() if link else hashlib.md5(article.get('title', '').encode('utf-8')).hexdigest()
        fe.guid(guid, permalink=False)
        
        author = article.get('author', '') or 'Unknown'
        fe.author(name=author)
    
    def generate_rss(self, articles: List[Dict], output_file: str) -> str:
        print(f"正在生成 RSS feed，包含 {len(articles)} 篇文章...")
        
        sorted_articles = sorted(
            articles,
            key=lambda x: self.parse_date(x.get('date', '')),
            reverse=True
        )
        
        for article in sorted_articles:
            self.add_article(article)
        
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        self.fg.rss_file(output_file, pretty=True)
        
        self._add_content_encoded(output_file, sorted_articles)
        
        print(f"RSS feed 已生成: {output_file}")
        return output_file
    
    def _add_content_encoded(self, output_file: str, articles: List[Dict]):
        """后处理：添加 content:encoded 和 dc:creator，按 link 匹配避免顺序错乱"""
        NS = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'dc': 'http://purl.org/dc/elements/1.1/',
        }
        
        ET.register_namespace('content', NS['content'])
        ET.register_namespace('dc', NS['dc'])
        
        # 用 link 建立 article 查找表
        articles_by_link = {a.get('link', '').strip(): a for a in articles if a.get('link')}
        
        tree = ET.parse(output_file)
        root = tree.getroot()
        
        channel = root.find('channel')
        if channel is None:
            return
        
        items = list(channel.findall('item'))
        
        for item in items:
            link_elem = item.find('link')
            item_link = (link_elem.text or '').strip() if link_elem is not None else ''
            article = articles_by_link.get(item_link)
            if article is None:
                continue
            
            content = article.get('content', '')
            if content:
                enc = ET.Element('{' + NS['content'] + '}encoded')
                enc.text = content
                item.append(enc)
            
            author = article.get('author', '') or 'Unknown'
            creator = ET.Element('{' + NS['dc'] + '}creator')
            creator.text = author
            item.append(creator)
        
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
