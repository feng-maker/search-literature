'''
作者：宇宙第一帅
时间：2024/7/26
'''
from PyQt6.QtGui import QFont
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import quote
import re
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
class SearchWorker(QThread):
    """搜索工作线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, keywords, start_date, end_date, journals, strict_match=True):
        super().__init__()
        self.keywords = keywords
        self.start_date = start_date
        self.end_date = end_date
        self.journals = journals
        self.strict_match = strict_match
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
        self.timeout = 15

    def run(self):
        try:
            results = []
            total_journals = len(self.journals)

            for i, journal in enumerate(self.journals):
                self.progress.emit(int((i / total_journals) * 100))
                try:
                    journal_start_time = time.time()
                    journal_timeout = 45

                    if journal == "ICLR":
                        journal_results = self.search_iclr()
                    elif journal == "CVPR":
                        journal_results = self.search_cvpr()
                    elif journal == "NeurIPS":
                        journal_results = self.search_neurips()
                    else:
                        continue

                    if time.time() - journal_start_time > journal_timeout:
                        continue

                    filtered_results = self.filter_by_date(journal_results)
                    results.extend(filtered_results)

                except Exception as e:
                    continue

                time.sleep(0.5)

            results = self.remove_duplicates(results)
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))

    def filter_by_date(self, papers):
        """根据时间范围过滤结果"""
        filtered = []
        start_year = self.start_date.year
        end_year = self.end_date.year

        for paper in papers:
            try:
                # 尝试将年份转换为整数进行比较
                paper_year = int(paper["year"])
                if start_year <= paper_year <= end_year:
                    filtered.append(paper)
            except (ValueError, TypeError):
                # 如果年份无法转换为整数，不包含该论文
                continue

        return filtered

    def match_keywords(self, text):
        """检查文本是否匹配所有关键词（不区分顺序）- 严格模式"""
        if not text:
            return False
        text = text.lower()

        # 关键词匹配模式: 所有关键词必须在标题中出现
        all_keywords_match = True
        for keyword in self.keywords:
            keyword = keyword.lower()
            if keyword not in text:
                all_keywords_match = False
                break

        return all_keywords_match

    def match_keywords_combined(self, title, abstract=""):
        """检查标题或摘要是否匹配关键词 - 支持严格和宽松模式"""
        if not title and not abstract:
            return False

        combined_text = (title + " " + abstract).lower()

        if self.strict_match:
            # 严格模式：所有关键词必须出现
            for keyword in self.keywords:
                keyword = keyword.lower()
                if keyword not in combined_text:
                    return False
            return True
        else:
            # 宽松模式：至少有一个关键词出现
            for keyword in self.keywords:
                keyword = keyword.lower()
                if keyword in combined_text:
                    return True
            return False

    def search_iclr(self):
        """搜索ICLR论文"""
        papers = []

        try:
            url = "https://api.openreview.net/notes/search"
            params = {
                "term": ' '.join(self.keywords),
                "content.venueid": "ICLR.cc/2024/Conference",
                "limit": 1000,
                "details": "true"
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                notes = data.get('notes', [])

                if not notes:
                    for year in range(2023, 2019, -1):
                        params["content.venueid"] = f"ICLR.cc/{year}/Conference"
                        response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
                        if response.status_code == 200:
                            data = response.json()
                            notes.extend(data.get('notes', []))

                for note in notes:
                    try:
                        content = note.get('content', {})
                        title = content.get('title', '')
                        if not title:
                            continue

                        authors = content.get('authors', [])
                        authors = ', '.join(authors) if isinstance(authors, list) else str(authors)

                        creation_date = note.get('tcdate', '')
                        submission_date = note.get('tmdate', '')
                        venue = note.get('venue', '')
                        year_match = re.search(r'ICLR (\d{4})', venue)
                        year = year_match.group(1) if year_match else str(self.end_date.year)

                        try:
                            if creation_date:
                                date_obj = datetime.datetime.fromtimestamp(int(creation_date) / 1000)
                                date_str = date_obj.strftime("%Y-%m-%d")
                            else:
                                date_str = f"{year}-01-01"
                        except:
                            date_str = f"{year}-01-01"

                        paper_id = note.get('id', '')
                        paper_url = f"https://openreview.net/forum?id={paper_id}" if paper_id else ""

                        papers.append({
                            "title": title,
                            "authors": authors,
                            "year": year,
                            "date": date_str,
                            "journal": "ICLR",
                            "link": paper_url
                        })

                    except Exception:
                        continue

        except Exception:
            pass

        return papers

    def search_cvpr(self):
        """搜索CVPR论文"""
        papers = []
        years_to_search = range(2024, 2017, -1)

        for year in years_to_search:
            try:
                urls = [
                    f"https://openaccess.thecvf.com/CVPR{year}?day=all",
                    f"https://openaccess.thecvf.com/content_CVPR_{year}/html/"
                ]

                for url in urls:
                    try:
                        response = requests.get(url, headers=self.headers, timeout=self.timeout)
                        if response.status_code != 200:
                            continue

                        soup = BeautifulSoup(response.text, 'html.parser')

                        paper_elements = soup.find_all("dt", class_="ptitle")
                        if not paper_elements:
                            paper_elements = soup.find_all("div", class_="bibref")

                        for element in paper_elements:
                            try:
                                if element.name == "dt":
                                    title = element.text.strip()
                                    link = element.find("a")
                                else:
                                    title_elem = element.find("div", class_="title")
                                    title = title_elem.text.strip() if title_elem else ""
                                    link = element.find("a")

                                if not title:
                                    continue

                                paper_url = ""
                                if link:
                                    href = link.get("href", "")
                                    if href:
                                        if href.startswith("http"):
                                            paper_url = href
                                        else:
                                            paper_url = "https://openaccess.thecvf.com/" + href

                                authors = "未知作者"
                                if element.name == "dt":
                                    dd = element.find_next_sibling("dd")
                                    authors = dd.text.strip() if dd else "未知作者"
                                else:
                                    authors_elem = element.find("div", class_="authors")
                                    authors = authors_elem.text.strip() if authors_elem else "未知作者"

                                date_str = f"{year}-06-15"

                                papers.append({
                                    "title": title,
                                    "authors": authors,
                                    "year": str(year),
                                    "date": date_str,
                                    "journal": "CVPR",
                                    "link": paper_url
                                })

                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                continue

        return papers

    def search_neurips(self):
        """搜索NeurIPS论文"""
        papers = []

        try:
            years_to_search = range(2024, 2018, -1)

            for year in years_to_search:
                try:
                    url = f"https://papers.neurips.cc/paper/{year}"
                    response = requests.get(url, headers=self.headers, timeout=self.timeout)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        paper_links = soup.find_all("a", href=True)

                        for link in paper_links:
                            try:
                                title = link.text.strip()
                                if not title or len(title) < 10:
                                    continue

                                authors = ""
                                next_elem = link.find_next("i")
                                if next_elem:
                                    authors = next_elem.text.strip()

                                paper_url = f"https://papers.neurips.cc{link['href']}" if link['href'].startswith(
                                    '/') else link['href']

                                date_str = f"{year}-12-01"

                                papers.append({
                                    "title": title,
                                    "authors": authors,
                                    "year": str(year),
                                    "date": date_str,
                                    "journal": "NeurIPS",
                                    "link": paper_url
                                })

                            except Exception:
                                continue

                except Exception:
                    continue

                time.sleep(0.5)

        except Exception:
            pass

        return papers

    def remove_duplicates(self, results):
        """移除重复的搜索结果"""
        unique_results = []
        seen_titles = set()

        for paper in results:
            title = paper.get("title", "").lower().strip()
            # 如果标题长度 > 10 且之前没见过，则添加
            if len(title) > 10 and title not in seen_titles:
                seen_titles.add(title)
                unique_results.append(paper)

        return unique_results
