import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QTableWidget, QTableWidgetItem, QComboBox, 
                           QDateEdit, QMessageBox, QListWidget, QProgressBar)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
import datetime
from searchwork import  SearchWorker
class LiteratureSearchGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文献检索系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # 创建搜索条件区域
        search_frame = QWidget()
        search_layout = QVBoxLayout()
        search_frame.setLayout(search_layout)
        
        # 关键词输入
        keyword_layout = QHBoxLayout()
        keyword_label = QLabel("关键词:")
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("请输入要搜索的关键词（多个关键词用空格分隔）")
        keyword_layout.addWidget(keyword_label)
        keyword_layout.addWidget(self.keyword_input)
        search_layout.addLayout(keyword_layout)
        
        # 时间范围选择
        date_layout = QHBoxLayout()
        date_label = QLabel("时间范围:")
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate(2020, 1, 1))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate(2024, 12, 31))
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("至"))
        date_layout.addWidget(self.end_date)
        search_layout.addLayout(date_layout)
        
        # 期刊选择
        journal_layout = QHBoxLayout()
        journal_label = QLabel("选择期刊:")
        self.journal_list = QListWidget()
        self.journal_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        journals = ["ICLR", "CVPR", "NeurIPS"]  # 移除Nature、Science和ICML
        self.journal_list.addItems(journals)
        # 默认全选
        for i in range(self.journal_list.count()):
            self.journal_list.item(i).setSelected(True)
        journal_layout.addWidget(journal_label)
        journal_layout.addWidget(self.journal_list)
        search_layout.addLayout(journal_layout)
        
        # 搜索设置
        settings_layout = QHBoxLayout()
        
        # 搜索按钮
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.start_search)
        settings_layout.addWidget(self.search_button)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_search)
        self.cancel_button.setEnabled(False)
        settings_layout.addWidget(self.cancel_button)
        
        # 搜索策略选择
        self.strict_match = QComboBox()
        self.strict_match.addItem("宽松匹配（至少包含一个关键词）", False)
        self.strict_match.addItem("严格匹配（必须包含所有关键词）", True)
        settings_layout.addWidget(self.strict_match)
        
        search_layout.addLayout(settings_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        search_layout.addWidget(self.progress_bar)
        
        # 搜索状态
        self.status_label = QLabel("")
        search_layout.addWidget(self.status_label)
        
        layout.addWidget(search_frame)
        
        # 创建结果显示区域
        result_frame = QWidget()
        result_layout = QVBoxLayout()
        result_frame.setLayout(result_layout)
        
        # 结果统计和操作
        stats_layout = QHBoxLayout()
        self.result_count_label = QLabel("找到0篇文献")
        stats_layout.addWidget(self.result_count_label)
        
        # 结果过滤选项
        filter_label = QLabel("过滤:")
        stats_layout.addWidget(filter_label)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("输入关键词过滤结果")
        self.filter_input.textChanged.connect(self.filter_results)
        stats_layout.addWidget(self.filter_input)
        
        # 结果排序选项
        sort_label = QLabel("排序方式:")
        stats_layout.addWidget(sort_label)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["默认排序", "按年份降序", "按年份升序", "按标题排序", "按关键词匹配度"])
        self.sort_combo.currentIndexChanged.connect(self.sort_results)
        stats_layout.addWidget(self.sort_combo)
        
        result_layout.addLayout(stats_layout)
        
        # 创建表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(["标题", "作者", "期刊", "发表时间", "文献地址", "关键词匹配"])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        # 双击显示详情
        self.result_table.cellDoubleClicked.connect(self.show_paper_details)
        result_layout.addWidget(self.result_table)
        
        layout.addWidget(result_frame)
        
        # 初始化搜索线程和结果存储
        self.search_thread = None
        self.search_results = []
        self.search_keywords = []
        
    def start_search(self):
        """开始搜索"""
        # 清空状态
        self.status_label.setText("")
        
        # 获取搜索条件
        keyword_text = self.keyword_input.text().strip()
        if not keyword_text:
            QMessageBox.warning(self, "警告", "请输入搜索关键词")
            return
            
        # 将输入的关键词拆分为列表
        keywords = keyword_text.split()
        if not keywords:
            QMessageBox.warning(self, "警告", "请输入有效的关键词")
            return
            
        self.search_keywords = keywords  # 保存关键词用于结果分析
            
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        selected_journals = [item.text() for item in self.journal_list.selectedItems()]
        
        # 获取匹配严格程度
        is_strict = self.strict_match.currentData()
        
        # 验证输入
        if not selected_journals:
            QMessageBox.warning(self, "警告", "请至少选择一个期刊")
            return
            
        if start_date > end_date:
            QMessageBox.warning(self, "警告", "结束日期不能早于开始日期")
            return
            
        # 禁用搜索按钮，启用取消按钮
        self.search_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"正在搜索：{', '.join(keywords)}，时间范围：{start_date.year}-{end_date.year}，期刊：{', '.join(selected_journals)}")
        
        # 创建并启动搜索线程
        self.search_thread = SearchWorker(keywords, start_date, end_date, selected_journals, is_strict)
        self.search_thread.progress.connect(self.update_progress)
        self.search_thread.finished.connect(self.show_results)
        self.search_thread.error.connect(self.show_error)
        self.search_thread.start()
        
    def cancel_search(self):
        """取消搜索"""
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.terminate()
            self.search_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.status_label.setText("搜索已取消")
        
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def show_results(self, results):
        """显示搜索结果"""
        # 启用搜索按钮，禁用取消按钮
        self.search_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        print(f"收到搜索结果：{len(results)}篇论文")
        
        # 保存原始结果
        self.search_results = results
        
        # 添加关键词匹配信息
        self.analyze_results()
        
        # 获取用户选择的时间范围
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        
        # 过滤结果：移除不在时间范围内和没有任何关键词匹配的结果
        filtered_results = []
        for paper in results:
            # 获取论文日期
            date_str = paper.get("date", paper.get("year", "1900-01-01"))
            try:
                if "-" in date_str:
                    paper_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    paper_date = datetime.date(int(date_str), 1, 1)
                
                # 检查是否在时间范围内且至少匹配一个关键词
                if (start_date <= paper_date <= end_date and 
                    paper.get("match_rate", 0) > 0):
                    filtered_results.append(paper)
            except (ValueError, TypeError):
                print(f"无法解析日期: {date_str}")
                continue
        
        # 根据匹配模式筛选和排序结果
        if self.strict_match.currentData():  # 严格匹配模式
            # 只保留完全匹配的论文，并按时间排序
            display_results = [paper for paper in filtered_results if paper.get("match_rate", 0) == 1.0]
            display_results = self.sort_by_date(display_results)
        else:  # 宽松匹配模式
            # 先按匹配度分组，再在每组内按时间排序
            display_results = self.sort_by_match_rate_and_date(filtered_results)
        
        # 更新结果统计
        total_count = len(filtered_results)
        display_count = len(display_results)
        
        if self.strict_match.currentData():
            self.result_count_label.setText(f"找到{display_count}篇严格匹配文献 (总共{total_count}篇)")
        else:
            self.result_count_label.setText(f"找到{total_count}篇文献")
        
        # 显示结果
        self.display_results(display_results)
        
        if not display_results:
            if self.strict_match.currentData():
                QMessageBox.information(self, "提示", f"未找到严格匹配的文献（总共{total_count}篇）")
                self.status_label.setText(f"搜索完成：未找到严格匹配的文献（总共{total_count}篇）")
            else:
                QMessageBox.information(self, "提示", "未找到符合条件的文献")
                self.status_label.setText("搜索完成：未找到符合条件的文献")
        else:
            if self.strict_match.currentData():
                self.status_label.setText(f"搜索完成：找到{display_count}篇严格匹配文献（总共{total_count}篇）")
            else:
                self.status_label.setText(f"搜索完成：共找到{total_count}篇符合条件的文献")
                
    def sort_by_date(self, papers):
        """按日期排序（降序）"""
        def get_date_key(paper):
            date_str = paper.get("date", paper.get("year", "1900-01-01"))
            try:
                if "-" in date_str:
                    return datetime.datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    return datetime.datetime(int(date_str), 1, 1)
            except:
                return datetime.datetime(1900, 1, 1)
        
        return sorted(papers, key=get_date_key, reverse=True)
        
    def sort_by_match_rate_and_date(self, papers):
        """先按匹配度分组，再在每组内按时间排序"""
        # 按匹配率分组
        groups = {}
        for paper in papers:
            match_rate = paper.get("match_rate", 0)
            if match_rate not in groups:
                groups[match_rate] = []
            groups[match_rate].append(paper)
        
        # 对每组按时间排序，然后按匹配率降序合并
        sorted_results = []
        for match_rate in sorted(groups.keys(), reverse=True):
            sorted_results.extend(self.sort_by_date(groups[match_rate]))
        
        return sorted_results
        
    def sort_results(self, index):
        """根据所选条件对结果排序"""
        if not self.search_results:
            return
            
        # 首先过滤时间范围
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        
        filtered_results = []
        for paper in self.search_results:
            try:
                date_str = paper.get("date", paper.get("year", "1900-01-01"))
                if "-" in date_str:
                    paper_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    paper_date = datetime.date(int(date_str), 1, 1)
                
                if start_date <= paper_date <= end_date and paper.get("match_rate", 0) > 0:
                    filtered_results.append(paper)
            except (ValueError, TypeError):
                continue
        
        if index == 1:  # 按年份降序
            filtered_results = self.sort_by_date(filtered_results)
        elif index == 2:  # 按年份升序
            filtered_results = self.sort_by_date(filtered_results)[::-1]
        elif index == 3:  # 按标题排序
            filtered_results.sort(key=lambda x: x.get("title", "").lower())
        elif index == 4:  # 按关键词匹配度和时间
            filtered_results = self.sort_by_match_rate_and_date(filtered_results)
            
        self.display_results(filtered_results)
        self.result_count_label.setText(f"找到{len(filtered_results)}篇文献")
        
    def analyze_results(self):
        """分析搜索结果，添加关键词匹配信息"""
        for paper in self.search_results:
            title = paper.get("title", "").lower()
            # 计算匹配的关键词数量
            matched_keywords = []
            for keyword in self.search_keywords:
                if keyword.lower() in title:
                    matched_keywords.append(keyword)
            
            # 添加匹配信息
            match_rate = len(matched_keywords) / len(self.search_keywords)
            match_info = f"匹配 {len(matched_keywords)}/{len(self.search_keywords)}"
            paper["match_info"] = match_info
            paper["match_rate"] = match_rate
            paper["matched_keywords"] = matched_keywords
    
    def display_results(self, results):
        """在表格中显示结果"""
        self.result_table.setRowCount(len(results))
        
        # 设置表格列宽
        self.result_table.setColumnWidth(0, 400)  # 标题列加宽
        self.result_table.setColumnWidth(1, 200)  # 作者列
        self.result_table.setColumnWidth(2, 100)  # 期刊列
        self.result_table.setColumnWidth(3, 120)  # 发表时间列
        self.result_table.setColumnWidth(4, 250)  # 链接列
        self.result_table.setColumnWidth(5, 120)  # 匹配信息列
        
        for row, paper in enumerate(results):
            # 创建标题项并设置工具提示
            title_item = QTableWidgetItem(paper["title"])
            title_item.setToolTip(paper["title"])  # 鼠标悬停显示完整标题
            self.result_table.setItem(row, 0, title_item)
            
            # 设置作者
            author_item = QTableWidgetItem(paper["authors"])
            author_item.setToolTip(paper["authors"])  # 鼠标悬停显示完整作者列表
            self.result_table.setItem(row, 1, author_item)
            
            # 设置期刊
            self.result_table.setItem(row, 2, QTableWidgetItem(paper["journal"]))
            
            # 设置发表时间（包含具体日期）
            date_str = paper.get("date", paper["year"])
            self.result_table.setItem(row, 3, QTableWidgetItem(date_str))
            
            # 创建可点击的链接
            link_item = QTableWidgetItem(paper["link"])
            link_item.setForeground(Qt.GlobalColor.blue)
            link_item.setToolTip("点击访问论文链接")
            self.result_table.setItem(row, 4, link_item)
            
            # 显示关键词匹配信息
            match_item = QTableWidgetItem(paper.get("match_info", ""))
            match_rate = paper.get("match_rate", 0)
            if match_rate == 1.0:
                match_item.setForeground(Qt.GlobalColor.darkGreen)
            elif match_rate >= 0.5:
                match_item.setForeground(Qt.GlobalColor.blue)
            else:
                match_item.setForeground(Qt.GlobalColor.darkGray)
            self.result_table.setItem(row, 5, match_item)
            
        # 允许标题自动换行显示
        self.result_table.setWordWrap(True)
        # 自动调整行高以适应内容
        self.result_table.resizeRowsToContents()
    
    def show_paper_details(self, row, column):
        """显示论文详细信息"""
        if row < 0 or row >= len(self.search_results):
            return
            
        paper = self.search_results[row]
        
        # 创建详情窗口
        details = f"标题: {paper.get('title', '')}\n\n"
        details += f"作者: {paper.get('authors', '')}\n\n"
        details += f"期刊: {paper.get('journal', '')}\n\n"
        details += f"年份: {paper.get('year', '')}\n\n"
        details += f"链接: {paper.get('link', '')}\n\n"
        
        # 添加关键词匹配分析
        details += f"关键词匹配:\n"
        for keyword in self.search_keywords:
            if keyword.lower() in paper.get('title', '').lower():
                details += f" - '{keyword}': 在标题中找到\n"
            else:
                details += f" - '{keyword}': 未匹配\n"
        
        QMessageBox.information(self, "论文详情", details)
            
    def filter_results(self):
        """根据输入过滤结果"""
        filter_text = self.filter_input.text().lower()
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        
        # 首先过滤时间范围
        time_filtered_results = []
        for paper in self.search_results:
            try:
                date_str = paper.get("date", paper.get("year", "1900-01-01"))
                if "-" in date_str:
                    paper_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    paper_date = datetime.date(int(date_str), 1, 1)
                
                if start_date <= paper_date <= end_date and paper.get("match_rate", 0) > 0:
                    time_filtered_results.append(paper)
            except (ValueError, TypeError):
                continue
        
        if not filter_text:
            self.display_results(time_filtered_results)
            self.result_count_label.setText(f"找到{len(time_filtered_results)}篇文献")
            return
            
        # 在时间过滤的基础上进行关键词过滤
        keyword_filtered_results = []
        for paper in time_filtered_results:
            title = paper.get("title", "").lower()
            authors = paper.get("authors", "").lower()
            journal = paper.get("journal", "").lower()
            
            if (filter_text in title or 
                filter_text in authors or 
                filter_text in journal):
                keyword_filtered_results.append(paper)
                
        self.display_results(keyword_filtered_results)
        self.result_count_label.setText(f"找到{len(keyword_filtered_results)}篇文献 (已过滤)")
            
    def show_error(self, error_msg):
        """显示错误信息"""
        self.search_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"搜索失败：{error_msg}")
        QMessageBox.critical(self, "错误", f"搜索失败: {error_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LiteratureSearchGUI()
    window.show()
    sys.exit(app.exec())
