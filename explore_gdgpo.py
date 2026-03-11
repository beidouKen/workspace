#!/usr/bin/env python3
"""
广东省政府采购网搜索页面探索脚本
用于收集页面结构信息、测试URL参数、分析DOM结构
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse, parse_qs
import sys

class GDGPOExplorer:
    def __init__(self):
        self.base_url = "https://gdgpo.czt.gd.gov.cn"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        self.report = {
            "探索时间": time.strftime("%Y-%m-%d %H:%M:%S"),
            "基础页面": {},
            "URL参数测试": {},
            "搜索表单结构": {},
            "搜索结果结构": {},
            "分页机制": {},
            "详情页链接": {},
            "其他发现": []
        }
    
    def explore_base_page(self):
        """探索基础搜索页面"""
        print("\n" + "="*60)
        print("步骤 1: 探索基础搜索页面")
        print("="*60)
        
        url = f"{self.base_url}/maincms-web/fullSearchingGd"
        print(f"URL: {url}")
        
        try:
            response = self.session.get(url, timeout=15, allow_redirects=True)
            print(f"状态码: {response.status_code}")
            print(f"最终URL: {response.url}")
            print(f"是否有重定向: {len(response.history) > 0}")
            
            if len(response.history) > 0:
                print("重定向历史:")
                for i, resp in enumerate(response.history):
                    print(f"  {i+1}. {resp.status_code} -> {resp.url}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否有弹窗
            popups = self._detect_popups(soup)
            
            # 分析搜索表单
            search_forms = self._analyze_search_forms(soup)
            
            # 分析搜索输入框
            search_inputs = self._analyze_search_inputs(soup)
            
            # 分析搜索按钮
            search_buttons = self._analyze_search_buttons(soup)
            
            self.report["基础页面"] = {
                "url": url,
                "最终url": response.url,
                "状态码": response.status_code,
                "有重定向": len(response.history) > 0,
                "重定向类型": "tipsPage" if "tipsPage" in response.url else "其他" if len(response.history) > 0 else "无",
                "检测到的弹窗": popups,
                "搜索表单数量": len(search_forms),
                "搜索输入框数量": len(search_inputs),
                "搜索按钮数量": len(search_buttons)
            }
            
            self.report["搜索表单结构"] = {
                "表单列表": search_forms,
                "输入框列表": search_inputs,
                "按钮列表": search_buttons
            }
            
            return soup, response
            
        except Exception as e:
            print(f"[ERROR] 错误: {str(e)}")
            self.report["基础页面"]["错误"] = str(e)
            return None, None
    
    def _detect_popups(self, soup):
        """检测页面中的弹窗"""
        popups = []
        
        # 常见弹窗选择器
        popup_selectors = [
            {'selector': '.mainNoticeBox', 'name': '主通知弹窗'},
            {'selector': '.noticeCloseBtn', 'name': '通知关闭按钮'},
            {'selector': '[class*="modal"]', 'name': '模态框'},
            {'selector': '[class*="popup"]', 'name': '弹出框'},
            {'selector': '[class*="dialog"]', 'name': '对话框'},
            {'selector': '[class*="overlay"]', 'name': '遮罩层'},
        ]
        
        for item in popup_selectors:
            elements = soup.select(item['selector'])
            if elements:
                popups.append({
                    "类型": item['name'],
                    "选择器": item['selector'],
                    "数量": len(elements),
                    "示例HTML": str(elements[0])[:200] + "..." if len(str(elements[0])) > 200 else str(elements[0])
                })
        
        return popups
    
    def _analyze_search_forms(self, soup):
        """分析搜索表单"""
        forms = []
        for form in soup.find_all('form'):
            form_info = {
                "action": form.get('action', ''),
                "method": form.get('method', ''),
                "id": form.get('id', ''),
                "class": form.get('class', []),
                "inputs": []
            }
            
            for inp in form.find_all(['input', 'select', 'textarea']):
                form_info["inputs"].append({
                    "tag": inp.name,
                    "type": inp.get('type', ''),
                    "name": inp.get('name', ''),
                    "id": inp.get('id', ''),
                    "placeholder": inp.get('placeholder', ''),
                    "class": inp.get('class', [])
                })
            
            forms.append(form_info)
        
        return forms
    
    def _analyze_search_inputs(self, soup):
        """分析搜索输入框"""
        inputs = []
        
        # 查找可能的搜索输入框
        search_keywords = ['search', 'keyword', 'query', 'word', '搜索', '关键词']
        
        for inp in soup.find_all('input'):
            inp_type = inp.get('type', '').lower()
            inp_name = inp.get('name', '').lower()
            inp_id = inp.get('id', '').lower()
            inp_placeholder = inp.get('placeholder', '').lower()
            
            # 判断是否是搜索框
            is_search = any(keyword in inp_name or keyword in inp_id or keyword in inp_placeholder 
                          for keyword in search_keywords)
            
            if is_search or inp_type == 'search' or inp_type == 'text':
                inputs.append({
                    "type": inp.get('type', ''),
                    "name": inp.get('name', ''),
                    "id": inp.get('id', ''),
                    "class": inp.get('class', []),
                    "placeholder": inp.get('placeholder', ''),
                    "value": inp.get('value', ''),
                    "可能是搜索框": is_search
                })
        
        return inputs
    
    def _analyze_search_buttons(self, soup):
        """分析搜索按钮"""
        buttons = []
        
        search_keywords = ['search', 'submit', '搜索', '查询', '检索']
        
        # 查找button标签
        for btn in soup.find_all('button'):
            btn_text = btn.get_text(strip=True).lower()
            btn_type = btn.get('type', '').lower()
            btn_class = ' '.join(btn.get('class', [])).lower()
            btn_id = btn.get('id', '').lower()
            
            is_search = any(keyword in btn_text or keyword in btn_class or keyword in btn_id 
                          for keyword in search_keywords)
            
            if is_search or btn_type == 'submit':
                buttons.append({
                    "tag": "button",
                    "type": btn.get('type', ''),
                    "text": btn.get_text(strip=True),
                    "id": btn.get('id', ''),
                    "class": btn.get('class', []),
                    "可能是搜索按钮": is_search
                })
        
        # 查找input type=submit/button
        for inp in soup.find_all('input', type=['submit', 'button']):
            inp_value = inp.get('value', '').lower()
            inp_id = inp.get('id', '').lower()
            inp_class = ' '.join(inp.get('class', [])).lower()
            
            is_search = any(keyword in inp_value or keyword in inp_class or keyword in inp_id 
                          for keyword in search_keywords)
            
            buttons.append({
                "tag": "input",
                "type": inp.get('type', ''),
                "value": inp.get('value', ''),
                "id": inp.get('id', ''),
                "class": inp.get('class', []),
                "可能是搜索按钮": is_search
            })
        
        return buttons
    
    def test_url_parameters(self):
        """测试不同的URL参数"""
        print("\n" + "="*60)
        print("步骤 2: 测试URL参数")
        print("="*60)
        
        test_cases = [
            {"param": "keywords", "value": "体育"},
            {"param": "searchWord", "value": "体育"},
            {"param": "keyword", "value": "体育"},
        ]
        
        results = []
        
        for case in test_cases:
            print(f"\n测试参数: {case['param']}={case['value']}")
            url = f"{self.base_url}/maincms-web/fullSearchingGd?{case['param']}={case['value']}"
            print(f"URL: {url}")
            
            try:
                response = self.session.get(url, timeout=15, allow_redirects=True)
                print(f"状态码: {response.status_code}")
                print(f"最终URL: {response.url}")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 检查搜索框是否包含关键词
                input_value = self._check_input_value(soup, case['value'])
                
                # 检查是否有搜索结果
                search_results = self._analyze_search_results(soup)
                
                result = {
                    "参数": case['param'],
                    "值": case['value'],
                    "url": url,
                    "最终url": response.url,
                    "状态码": response.status_code,
                    "搜索框是否包含关键词": input_value,
                    "搜索结果数量": search_results['count'],
                    "是否成功触发搜索": input_value or search_results['count'] > 0
                }
                
                results.append(result)
                print(f"搜索框包含关键词: {input_value}")
                print(f"搜索结果数量: {search_results['count']}")
                
                time.sleep(2)  # 礼貌等待
                
            except Exception as e:
                print(f"[ERROR] 错误: {str(e)}")
                results.append({
                    "参数": case['param'],
                    "值": case['value'],
                    "错误": str(e)
                })
        
        self.report["URL参数测试"] = results
        
        # 找出成功的参数
        successful_params = [r for r in results if r.get('是否成功触发搜索', False)]
        if successful_params:
            print(f"\n[OK] 成功的参数: {[r['参数'] for r in successful_params]}")
        else:
            print("\n[WARNING] 没有找到能成功触发搜索的URL参数")
    
    def _check_input_value(self, soup, expected_value):
        """检查输入框是否包含预期值"""
        for inp in soup.find_all('input'):
            if inp.get('value', '') == expected_value:
                return True
        return False
    
    def _analyze_search_results(self, soup):
        """分析搜索结果列表"""
        results = {
            "count": 0,
            "items": []
        }
        
        # 常见的结果列表选择器
        result_selectors = [
            '.search-result',
            '.result-item',
            '.list-item',
            '[class*="result"]',
            '[class*="list"]',
            'ul li',
            '.item'
        ]
        
        for selector in result_selectors:
            elements = soup.select(selector)
            if elements and len(elements) > 3:  # 至少要有几个才算是结果列表
                results["count"] = len(elements)
                
                # 分析前3个结果的结构
                for i, elem in enumerate(elements[:3]):
                    item = {
                        "索引": i,
                        "HTML片段": str(elem)[:300] + "..." if len(str(elem)) > 300 else str(elem)
                    }
                    
                    # 尝试提取标题
                    title_elem = elem.find(['h1', 'h2', 'h3', 'h4', 'a'])
                    if title_elem:
                        item["标题"] = title_elem.get_text(strip=True)
                    
                    # 尝试提取链接
                    link_elem = elem.find('a')
                    if link_elem:
                        item["链接"] = link_elem.get('href', '')
                    
                    # 尝试提取日期
                    date_patterns = soup.find_all(string=lambda text: text and ('2024' in text or '2025' in text or '2026' in text))
                    if date_patterns:
                        item["可能的日期"] = date_patterns[0].strip()
                    
                    results["items"].append(item)
                
                break  # 找到一个就够了
        
        return results
    
    def analyze_search_results_page(self, soup):
        """深入分析搜索结果页面结构"""
        print("\n" + "="*60)
        print("步骤 3: 分析搜索结果结构")
        print("="*60)
        
        if not soup:
            print("[WARNING] 没有可用的页面进行分析")
            return
        
        # 分析搜索结果
        search_results = self._analyze_search_results(soup)
        
        # 分析分页
        pagination = self._analyze_pagination(soup)
        
        # 分析详情页链接格式
        detail_links = self._analyze_detail_links(soup)
        
        self.report["搜索结果结构"] = search_results
        self.report["分页机制"] = pagination
        self.report["详情页链接"] = detail_links
        
        print(f"搜索结果数量: {search_results['count']}")
        print(f"分页元素数量: {pagination['count']}")
        print(f"详情页链接数量: {len(detail_links)}")
    
    def _analyze_pagination(self, soup):
        """分析分页机制"""
        pagination = {
            "count": 0,
            "elements": []
        }
        
        # 常见的分页选择器
        page_selectors = [
            '.pagination',
            '.pager',
            '.page-nav',
            '[class*="page"]',
            '[class*="pagin"]'
        ]
        
        for selector in page_selectors:
            elements = soup.select(selector)
            if elements:
                pagination["count"] = len(elements)
                
                for elem in elements:
                    pagination["elements"].append({
                        "选择器": selector,
                        "HTML": str(elem)[:300] + "..." if len(str(elem)) > 300 else str(elem),
                        "链接数量": len(elem.find_all('a')),
                        "按钮数量": len(elem.find_all('button'))
                    })
                
                break
        
        return pagination
    
    def _analyze_detail_links(self, soup):
        """分析详情页链接格式"""
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            
            # 过滤掉明显不是详情页的链接
            if any(keyword in href.lower() for keyword in ['javascript', '#', 'void', 'http://www', 'https://www']):
                continue
            
            # 只保留可能是详情页的链接
            if any(keyword in href.lower() for keyword in ['detail', 'view', 'show', 'content', 'article']):
                full_url = urljoin(self.base_url, href)
                links.append({
                    "原始href": href,
                    "完整URL": full_url,
                    "链接文本": a.get_text(strip=True)[:100]
                })
        
        return links[:10]  # 只返回前10个
    
    def explore_with_js_rendering(self):
        """尝试使用其他方法探索（如果需要JavaScript渲染）"""
        print("\n" + "="*60)
        print("检查是否需要JavaScript渲染")
        print("="*60)
        
        # 简单检查页面是否严重依赖JavaScript
        url = f"{self.base_url}/maincms-web/fullSearchingGd"
        
        try:
            response = self.session.get(url, timeout=15)
            
            # 检查关键指标
            has_react = 'react' in response.text.lower()
            has_vue = 'vue' in response.text.lower()
            has_angular = 'angular' in response.text.lower()
            has_spa_indicators = any(framework in response.text.lower() 
                                    for framework in ['app.js', 'bundle.js', 'main.js', 'chunk'])
            
            minimal_html = len(response.text) < 5000
            
            js_required = has_react or has_vue or has_angular or (has_spa_indicators and minimal_html)
            
            self.report["其他发现"].append({
                "发现": "JavaScript渲染检查",
                "可能需要JS": js_required,
                "检测到React": has_react,
                "检测到Vue": has_vue,
                "检测到Angular": has_angular,
                "检测到SPA指标": has_spa_indicators,
                "HTML长度": len(response.text)
            })
            
            if js_required:
                print("[WARNING] 此页面可能需要JavaScript渲染才能正确显示内容")
                print("   建议使用浏览器工具（如Selenium、Playwright、Puppeteer）进行采集")
            else:
                print("[OK] 此页面可以通过静态HTML解析")
                
        except Exception as e:
            print(f"[ERROR] 错误: {str(e)}")
    
    def generate_report(self):
        """生成最终报告"""
        print("\n" + "="*60)
        print("生成报告")
        print("="*60)
        
        # 保存JSON报告
        report_path = "d:/openclaw/workspace/gdgpo_exploration_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] JSON报告已保存: {report_path}")
        
        # 生成Markdown报告
        md_report = self._generate_markdown_report()
        md_path = "d:/openclaw/workspace/gdgpo_exploration_report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)
        
        print(f"[OK] Markdown报告已保存: {md_path}")
        
        return report_path, md_path
    
    def _generate_markdown_report(self):
        """生成Markdown格式的报告"""
        md = []
        md.append("# 广东省政府采购网搜索页面探索报告\n")
        md.append(f"**探索时间**: {self.report['探索时间']}\n")
        md.append("---\n")
        
        # 基础页面
        md.append("\n## 1. 基础页面分析\n")
        base = self.report.get("基础页面", {})
        md.append(f"- **URL**: {base.get('url', 'N/A')}\n")
        md.append(f"- **最终URL**: {base.get('最终url', 'N/A')}\n")
        md.append(f"- **状态码**: {base.get('状态码', 'N/A')}\n")
        md.append(f"- **重定向**: {base.get('重定向类型', 'N/A')}\n")
        
        if base.get("检测到的弹窗"):
            md.append("\n### 检测到的弹窗\n")
            for popup in base["检测到的弹窗"]:
                md.append(f"- **{popup['类型']}**: `{popup['选择器']}` (数量: {popup['数量']})\n")
        
        # URL参数测试
        md.append("\n## 2. URL参数测试结果\n")
        url_tests = self.report.get("URL参数测试", [])
        if url_tests:
            md.append("\n| 参数 | 搜索框包含关键词 | 搜索结果数量 | 是否成功 |\n")
            md.append("|------|----------------|-------------|----------|\n")
            for test in url_tests:
                if "错误" not in test:
                    success = "[OK]" if test.get('是否成功触发搜索', False) else "[FAIL]"
                    md.append(f"| `{test['参数']}` | {test.get('搜索框是否包含关键词', False)} | {test.get('搜索结果数量', 0)} | {success} |\n")
        
        # 搜索表单结构
        md.append("\n## 3. 搜索表单结构\n")
        forms = self.report.get("搜索表单结构", {})
        
        if forms.get("输入框列表"):
            md.append("\n### 搜索输入框\n")
            for i, inp in enumerate(forms["输入框列表"][:5], 1):
                if inp.get("可能是搜索框"):
                    md.append(f"\n**输入框 {i}** (可能的搜索框):\n")
                    md.append(f"- **name**: `{inp.get('name', 'N/A')}`\n")
                    md.append(f"- **id**: `{inp.get('id', 'N/A')}`\n")
                    md.append(f"- **type**: `{inp.get('type', 'N/A')}`\n")
                    md.append(f"- **placeholder**: `{inp.get('placeholder', 'N/A')}`\n")
        
        if forms.get("按钮列表"):
            md.append("\n### 搜索按钮\n")
            for i, btn in enumerate(forms["按钮列表"][:5], 1):
                if btn.get("可能是搜索按钮"):
                    md.append(f"\n**按钮 {i}** (可能的搜索按钮):\n")
                    if btn["tag"] == "button":
                        md.append(f"- **text**: `{btn.get('text', 'N/A')}`\n")
                    else:
                        md.append(f"- **value**: `{btn.get('value', 'N/A')}`\n")
                    md.append(f"- **id**: `{btn.get('id', 'N/A')}`\n")
                    md.append(f"- **type**: `{btn.get('type', 'N/A')}`\n")
        
        # 搜索结果结构
        md.append("\n## 4. 搜索结果结构\n")
        results = self.report.get("搜索结果结构", {})
        md.append(f"- **结果数量**: {results.get('count', 0)}\n")
        
        if results.get("items"):
            md.append("\n### 示例结果条目\n")
            for item in results["items"][:3]:
                md.append(f"\n**条目 {item['索引'] + 1}**:\n")
                if "标题" in item:
                    md.append(f"- **标题**: {item['标题']}\n")
                if "链接" in item:
                    md.append(f"- **链接**: {item['链接']}\n")
                if "可能的日期" in item:
                    md.append(f"- **日期**: {item['可能的日期']}\n")
        
        # 分页机制
        md.append("\n## 5. 分页机制\n")
        pagination = self.report.get("分页机制", {})
        md.append(f"- **分页元素数量**: {pagination.get('count', 0)}\n")
        
        # 详情页链接
        md.append("\n## 6. 详情页链接格式\n")
        detail_links = self.report.get("详情页链接", [])
        if detail_links:
            md.append("\n### 示例详情页链接\n")
            for i, link in enumerate(detail_links[:5], 1):
                md.append(f"\n**链接 {i}**:\n")
                md.append(f"- **URL**: `{link['完整URL']}`\n")
                md.append(f"- **文本**: {link['链接文本']}\n")
        
        # 其他发现
        if self.report.get("其他发现"):
            md.append("\n## 7. 其他发现\n")
            for finding in self.report["其他发现"]:
                md.append(f"\n### {finding.get('发现', '未命名发现')}\n")
                for key, value in finding.items():
                    if key != "发现":
                        md.append(f"- **{key}**: {value}\n")
        
        md.append("\n---\n")
        md.append("\n## 自动化脚本建议\n")
        md.append("\n根据探索结果，建议使用以下策略编写自动化脚本:\n\n")
        
        # 根据实际探索结果生成建议
        js_required = any(f.get("可能需要JS", False) for f in self.report.get("其他发现", []))
        
        if js_required:
            md.append("1. **使用浏览器自动化工具**（如Selenium、Playwright、Puppeteer），因为页面需要JavaScript渲染\n")
        else:
            md.append("1. **可以使用静态HTML解析**（如BeautifulSoup、lxml），无需浏览器渲染\n")
        
        successful_param = None
        for test in self.report.get("URL参数测试", []):
            if test.get("是否成功触发搜索", False):
                successful_param = test["参数"]
                break
        
        if successful_param:
            md.append(f"2. **URL参数**: 使用 `{successful_param}` 参数可以直接触发搜索\n")
            md.append(f"   - 示例: `fullSearchingGd?{successful_param}=体育`\n")
        else:
            md.append("2. **URL参数**: 测试的参数均未能直接触发搜索，可能需要通过表单提交\n")
        
        if base.get("检测到的弹窗"):
            md.append("3. **弹窗处理**: 页面加载后需要先关闭弹窗才能继续操作\n")
            for popup in base["检测到的弹窗"][:2]:
                md.append(f"   - 关闭选择器: `{popup['选择器']}`\n")
        
        md.append("\n---\n")
        md.append("\n*此报告由 GDGPOExplorer 自动生成*\n")
        
        return ''.join(md)
    
    def run(self):
        """执行完整的探索流程"""
        print("\n[START] 开始探索广东省政府采购网搜索页面")
        print("="*60)
        
        # 步骤1: 探索基础页面
        soup, response = self.explore_base_page()
        
        # 步骤2: 测试URL参数
        self.test_url_parameters()
        
        # 步骤3: 分析搜索结果（使用最后一个测试的页面）
        if soup:
            self.analyze_search_results_page(soup)
        
        # 步骤4: 检查JS需求
        self.explore_with_js_rendering()
        
        # 步骤5: 生成报告
        json_path, md_path = self.generate_report()
        
        print("\n" + "="*60)
        print("[SUCCESS] 探索完成！")
        print("="*60)
        print(f"\n报告文件:")
        print(f"  - JSON: {json_path}")
        print(f"  - Markdown: {md_path}")
        print("\n")

if __name__ == "__main__":
    explorer = GDGPOExplorer()
    explorer.run()
