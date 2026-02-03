"""
RSS Feed 生成器
"""
from feedgen.feed import FeedGenerator
from typing import List, Dict
from datetime import datetime, timezone
import re
import hashlib
import os


class RSSGenerator:
    def __init__(self,
                 feed_title: str = "Binance Square News",
                 feed_description: str = "Latest news from Binance Square",
                 feed_link: str = "https://www.binance.com/en/square",
                 feed_language: str = "en"):
        self.fg = FeedGenerator()
        self.fg.title(feed_title)
        self.fg.description(feed_description)
        self.fg.link(href=feed_link, rel='alternate')
        self.fg.language(feed_language)
        self.fg.lastBuildDate(datetime.now(timezone.utc))
        self.fg.generator('Binance Square RSS Generator')
    
    def parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RSS 标准格式
            '%a, %d %b %Y %H:%M:%S GMT',
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
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
        
        print(f"无法解析日期: {date_str}")
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
        
        # GUID
        link = article.get('link', '')
        guid = article.get('guid', '')
        if not guid:
            guid = hashlib.md5(link.encode('utf-8')).hexdigest() if link else hashlib.md5(article.get('title', '').encode('utf-8')).hexdigest()
        fe.guid(guid, permalink=False)
        
        # 作者
        author = article.get('author', '') or 'Binance Square'
        fe.author(name=author)
    
    def generate_rss(self, articles: List[Dict], output_file: str):
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
        
        # 后处理：添加 content:encoded
        self._add_content_encoded(output_file, sorted_articles)
        
        print(f"RSS feed 已生成: {output_file}")
        return output_file
    
    def _add_content_encoded(self, output_file: str, articles: List[Dict]):
        import xml.etree.ElementTree as ET
        
        NS = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'dc': 'http://purl.org/dc/elements/1.1/',
        }
        
        ET.register_namespace('content', NS['content'])
        ET.register_namespace('dc', NS['dc'])
        
        tree = ET.parse(output_file)
        root = tree.getroot()
        
        channel = root.find('channel')
        if channel is None:
            return
        
        items = list(channel.findall('item'))
        
        for i, item in enumerate(items):
            if i >= len(articles):
                break
            article = articles[i]
            
            content = article.get('content', '')
            if content:
                enc = ET.Element('{' + NS['content'] + '}encoded')
                enc.text = content
                item.append(enc)
            
            # dc:creator
            author = article.get('author', '') or 'Binance Square'
            creator = ET.Element('{' + NS['dc'] + '}creator')
            creator.text = author
            item.append(creator)
        
        tree.write(output_file, encoding='utf-8', xml_declaration=True)