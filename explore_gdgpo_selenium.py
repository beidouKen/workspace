#!/usr/bin/env python3
"""
广东省政府采购网搜索页面探索脚本 - Selenium 版本
使用浏览器自动化来探索需要 JavaScript 渲染的页面
"""

import json
import time
from datetime import datetime
import sys
import os

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("[ERROR] 需要安装 selenium 库")
    print("请运行: pip install selenium")
    sys.exit(1)

class GDGPOSeleniumExplorer:
    def __init__(self):
        self.base_url = "https://gdgpo.czt.gd.gov.cn"
        self.driver = None
        self.report = {
            "探索时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "基础页面": {},
            "URL参数测试": {},
            "搜索表单结构": {},
            "搜索结果结构": {},
            "分页机制": {},
            "详情页链接": {},
            "弹窗处理": {},
            "其他发现": []
        }
    
    def init_driver(self):
        """初始化浏览器驱动"""
        print("\n[INFO] 初始化浏览器...")
        
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
            print("[OK] 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"[ERROR] 浏览器初始化失败: {str(e)}")
            print("\n[INFO] 请确保:")
            print("  1. 已安装 Chrome 浏览器")
            print("  2. 已安装 chromedriver")
            print("  3. chromedriver 版本与 Chrome 浏览器版本匹配")
            return False
    
    def take_screenshot(self, filename):
        """截图"""
        try:
            filepath = f"d:/openclaw/workspace/{filename}"
            self.driver.save_screenshot(filepath)
            print(f"[OK] 截图已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"[ERROR] 截图失败: {str(e)}")
            return None
    
    def explore_base_page(self):
        """探索基础搜索页面"""
        print("\n" + "="*60)
        print("步骤 1: 探索基础搜索页面")
        print("="*60)
        
        url = f"{self.base_url}/maincms-web/fullSearchingGd"
        print(f"URL: {url}")
        
        try:
            # 导航到页面
            self.driver.get(url)
            time.sleep(3)  # 等待页面加载
            
            # 获取当前URL（可能有重定向）
            current_url = self.driver.current_url
            print(f"当前URL: {current_url}")
            
            # 截图
            screenshot = self.take_screenshot("gdgpo_base_page.png")
            
            # 检查是否有 tipsPage 重定向
            has_tips_redirect = "tipsPage" in current_url
            
            # 检查弹窗
            popups = self._detect_popups()
            
            # 处理弹窗
            popup_handled = False
            if popups:
                print(f"[INFO] 检测到 {len(popups)} 个弹窗，尝试关闭...")
                popup_handled = self._close_popups()
                time.sleep(2)
                
                if popup_handled:
                    self.take_screenshot("gdgpo_base_page_after_popup_close.png")
            
            # 如果有 tipsPage 重定向，尝试返回首页
            if has_tips_redirect:
                print("[WARNING] 检测到 tipsPage 重定向")
                self.driver.get(url)
                time.sleep(3)
                current_url = self.driver.current_url
                self.take_screenshot("gdgpo_base_page_after_redirect.png")
            
            # 分析搜索表单
            search_forms = self._analyze_search_forms()
            search_inputs = self._analyze_search_inputs()
            search_buttons = self._analyze_search_buttons()
            
            # 获取页面 HTML
            page_source_length = len(self.driver.page_source)
            
            self.report["基础页面"] = {
                "url": url,
                "最终url": current_url,
                "有tipsPage重定向": has_tips_redirect,
                "检测到的弹窗": popups,
                "弹窗已处理": popup_handled,
                "搜索表单数量": len(search_forms),
                "搜索输入框数量": len(search_inputs),
                "搜索按钮数量": len(search_buttons),
                "页面HTML长度": page_source_length,
                "截图": screenshot
            }
            
            self.report["搜索表单结构"] = {
                "表单列表": search_forms,
                "输入框列表": search_inputs,
                "按钮列表": search_buttons
            }
            
            self.report["弹窗处理"] = {
                "检测到的弹窗": popups,
                "是否成功关闭": popup_handled
            }
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 错误: {str(e)}")
            self.report["基础页面"]["错误"] = str(e)
            return False
    
    def _detect_popups(self):
        """检测页面中的弹窗"""
        popups = []
        
        # 常见弹窗选择器
        popup_selectors = [
            (By.CLASS_NAME, "mainNoticeBox"),
            (By.CLASS_NAME, "noticeCloseBtn"),
            (By.CSS_SELECTOR, "[class*='modal']"),
            (By.CSS_SELECTOR, "[class*='popup']"),
            (By.CSS_SELECTOR, "[class*='dialog']"),
            (By.CSS_SELECTOR, "[class*='overlay']"),
        ]
        
        for by, selector in popup_selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    for elem in elements:
                        try:
                            is_displayed = elem.is_displayed()
                            if is_displayed:
                                popups.append({
                                    "选择器类型": by,
                                    "选择器": selector,
                                    "数量": len(elements),
                                    "是否可见": is_displayed,
                                    "HTML片段": elem.get_attribute('outerHTML')[:200]
                                })
                                break
                        except:
                            pass
            except:
                pass
        
        return popups
    
    def _close_popups(self):
        """关闭弹窗"""
        try:
            # 尝试多种关闭按钮选择器
            close_selectors = [
                (By.CLASS_NAME, "noticeCloseBtn"),
                (By.CSS_SELECTOR, ".mainNoticeBox .noticeCloseBtn"),
                (By.XPATH, "//*[contains(@class, 'close')]"),
                (By.XPATH, "//*[text()='x']"),
                (By.XPATH, "//*[text()='X']"),
                (By.XPATH, "//*[text()='关闭']"),
                (By.XPATH, "//*[text()='确定']"),
                (By.XPATH, "//*[contains(text(), '知道了')]"),
            ]
            
            for by, selector in close_selectors:
                try:
                    element = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    element.click()
                    print(f"[OK] 成功点击关闭按钮: {selector}")
                    return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            print(f"[ERROR] 关闭弹窗失败: {str(e)}")
            return False
    
    def _analyze_search_forms(self):
        """分析搜索表单"""
        forms = []
        try:
            form_elements = self.driver.find_elements(By.TAG_NAME, "form")
            for form in form_elements:
                form_info = {
                    "action": form.get_attribute("action"),
                    "method": form.get_attribute("method"),
                    "id": form.get_attribute("id"),
                    "class": form.get_attribute("class"),
                }
                forms.append(form_info)
        except:
            pass
        return forms
    
    def _analyze_search_inputs(self):
        """分析搜索输入框"""
        inputs = []
        
        # 查找所有输入框
        try:
            input_elements = self.driver.find_elements(By.TAG_NAME, "input")
            
            search_keywords = ['search', 'keyword', 'query', 'word', '搜索', '关键词']
            
            for inp in input_elements:
                try:
                    inp_type = inp.get_attribute("type") or ""
                    inp_name = inp.get_attribute("name") or ""
                    inp_id = inp.get_attribute("id") or ""
                    inp_placeholder = inp.get_attribute("placeholder") or ""
                    inp_class = inp.get_attribute("class") or ""
                    
                    # 判断是否是搜索框
                    is_search = any(keyword in inp_name.lower() or 
                                  keyword in inp_id.lower() or 
                                  keyword in inp_placeholder.lower() or
                                  keyword in inp_class.lower()
                                  for keyword in search_keywords)
                    
                    if is_search or inp_type.lower() in ['search', 'text']:
                        # 检查是否可见
                        is_displayed = inp.is_displayed()
                        
                        inputs.append({
                            "type": inp_type,
                            "name": inp_name,
                            "id": inp_id,
                            "class": inp_class,
                            "placeholder": inp_placeholder,
                            "value": inp.get_attribute("value") or "",
                            "是否可见": is_displayed,
                            "可能是搜索框": is_search,
                            "xpath": self._get_xpath(inp)
                        })
                except:
                    pass
        except:
            pass
        
        return inputs
    
    def _analyze_search_buttons(self):
        """分析搜索按钮"""
        buttons = []
        
        search_keywords = ['search', 'submit', '搜索', '查询', '检索']
        
        try:
            # 查找 button 标签
            button_elements = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in button_elements:
                try:
                    btn_text = btn.text.lower()
                    btn_type = (btn.get_attribute("type") or "").lower()
                    btn_class = (btn.get_attribute("class") or "").lower()
                    btn_id = (btn.get_attribute("id") or "").lower()
                    
                    is_search = any(keyword in btn_text or 
                                  keyword in btn_class or 
                                  keyword in btn_id 
                                  for keyword in search_keywords)
                    
                    if is_search or btn_type == 'submit':
                        is_displayed = btn.is_displayed()
                        buttons.append({
                            "tag": "button",
                            "type": btn_type,
                            "text": btn.text,
                            "id": btn.get_attribute("id") or "",
                            "class": btn.get_attribute("class") or "",
                            "是否可见": is_displayed,
                            "可能是搜索按钮": is_search,
                            "xpath": self._get_xpath(btn)
                        })
                except:
                    pass
            
            # 查找 input type=submit/button
            submit_elements = self.driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], input[type='button']")
            for inp in submit_elements:
                try:
                    inp_value = (inp.get_attribute("value") or "").lower()
                    inp_id = (inp.get_attribute("id") or "").lower()
                    inp_class = (inp.get_attribute("class") or "").lower()
                    
                    is_search = any(keyword in inp_value or 
                                  keyword in inp_class or 
                                  keyword in inp_id 
                                  for keyword in search_keywords)
                    
                    is_displayed = inp.is_displayed()
                    buttons.append({
                        "tag": "input",
                        "type": inp.get_attribute("type"),
                        "value": inp.get_attribute("value") or "",
                        "id": inp_id,
                        "class": inp_class,
                        "是否可见": is_displayed,
                        "可能是搜索按钮": is_search,
                        "xpath": self._get_xpath(inp)
                    })
                except:
                    pass
        except:
            pass
        
        return buttons
    
    def _get_xpath(self, element):
        """获取元素的 XPath"""
        try:
            return self.driver.execute_script(
                "function getXPath(element) {"
                "  if (element.id !== '') return '//*[@id=\"' + element.id + '\"]';"
                "  if (element === document.body) return '/html/body';"
                "  var ix = 0;"
                "  var siblings = element.parentNode.childNodes;"
                "  for (var i = 0; i < siblings.length; i++) {"
                "    var sibling = siblings[i];"
                "    if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';"
                "    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;"
                "  }"
                "}"
                "return getXPath(arguments[0]);",
                element
            )
        except:
            return ""
    
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
                self.driver.get(url)
                time.sleep(3)
                
                current_url = self.driver.current_url
                print(f"当前URL: {current_url}")
                
                # 截图
                screenshot = self.take_screenshot(f"gdgpo_test_{case['param']}.png")
                
                # 检查搜索框是否包含关键词
                input_has_value = self._check_input_has_value(case['value'])
                
                # 检查是否有搜索结果
                search_results = self._analyze_search_results()
                
                result = {
                    "参数": case['param'],
                    "值": case['value'],
                    "url": url,
                    "最终url": current_url,
                    "搜索框包含关键词": input_has_value,
                    "搜索结果数量": search_results['count'],
                    "是否成功触发搜索": input_has_value or search_results['count'] > 0,
                    "截图": screenshot
                }
                
                results.append(result)
                print(f"搜索框包含关键词: {input_has_value}")
                print(f"搜索结果数量: {search_results['count']}")
                
                # 如果找到了搜索结果，进一步分析
                if search_results['count'] > 0:
                    self.report["搜索结果结构"] = search_results
                
                time.sleep(2)
                
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
    
    def _check_input_has_value(self, expected_value):
        """检查输入框是否包含预期值"""
        try:
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                try:
                    value = inp.get_attribute("value") or ""
                    if value == expected_value:
                        return True
                except:
                    pass
        except:
            pass
        return False
    
    def _analyze_search_results(self):
        """分析搜索结果列表"""
        results = {
            "count": 0,
            "items": []
        }
        
        # 常见的结果列表选择器
        result_selectors = [
            (By.CLASS_NAME, "search-result"),
            (By.CLASS_NAME, "result-item"),
            (By.CLASS_NAME, "list-item"),
            (By.CSS_SELECTOR, "[class*='result']"),
            (By.CSS_SELECTOR, "[class*='list']"),
            (By.CSS_SELECTOR, "ul li"),
        ]
        
        for by, selector in result_selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements and len(elements) > 3:
                    results["count"] = len(elements)
                    
                    # 分析前3个结果
                    for i, elem in enumerate(elements[:3]):
                        try:
                            item = {"索引": i}
                            
                            # 提取标题
                            try:
                                title_elem = elem.find_element(By.CSS_SELECTOR, "h1, h2, h3, h4, a")
                                item["标题"] = title_elem.text
                            except:
                                pass
                            
                            # 提取链接
                            try:
                                link_elem = elem.find_element(By.TAG_NAME, "a")
                                item["链接"] = link_elem.get_attribute("href")
                            except:
                                pass
                            
                            # 提取日期（简单匹配）
                            try:
                                text = elem.text
                                if any(year in text for year in ['2024', '2025', '2026']):
                                    item["包含日期"] = True
                            except:
                                pass
                            
                            results["items"].append(item)
                        except:
                            pass
                    
                    break
            except:
                pass
        
        return results
    
    def analyze_pagination(self):
        """分析分页机制"""
        print("\n" + "="*60)
        print("步骤 3: 分析分页机制")
        print("="*60)
        
        pagination = {
            "count": 0,
            "elements": []
        }
        
        # 常见的分页选择器
        page_selectors = [
            (By.CLASS_NAME, "pagination"),
            (By.CLASS_NAME, "pager"),
            (By.CLASS_NAME, "page-nav"),
            (By.CSS_SELECTOR, "[class*='page']"),
            (By.CSS_SELECTOR, "[class*='pagin']"),
        ]
        
        for by, selector in page_selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    pagination["count"] = len(elements)
                    
                    for elem in elements:
                        try:
                            is_displayed = elem.is_displayed()
                            if is_displayed:
                                pagination["elements"].append({
                                    "选择器": selector,
                                    "是否可见": is_displayed,
                                    "HTML片段": elem.get_attribute('outerHTML')[:300],
                                })
                        except:
                            pass
                    
                    break
            except:
                pass
        
        self.report["分页机制"] = pagination
        print(f"分页元素数量: {pagination['count']}")
    
    def analyze_detail_links(self):
        """分析详情页链接格式"""
        print("\n" + "="*60)
        print("步骤 4: 分析详情页链接格式")
        print("="*60)
        
        links = []
        
        try:
            link_elements = self.driver.find_elements(By.TAG_NAME, "a")
            
            for a in link_elements:
                try:
                    href = a.get_attribute("href") or ""
                    
                    # 过滤掉明显不是详情页的链接
                    if any(keyword in href.lower() for keyword in ['javascript', '#', 'void']):
                        continue
                    
                    # 只保留可能是详情页的链接
                    if any(keyword in href.lower() for keyword in ['detail', 'view', 'show', 'content', 'article']):
                        links.append({
                            "href": href,
                            "链接文本": a.text[:100]
                        })
                        
                        if len(links) >= 10:
                            break
                except:
                    pass
        except:
            pass
        
        self.report["详情页链接"] = links
        print(f"详情页链接数量: {len(links)}")
    
    def generate_report(self):
        """生成最终报告"""
        print("\n" + "="*60)
        print("生成报告")
        print("="*60)
        
        # 保存JSON报告
        report_path = "d:/openclaw/workspace/gdgpo_selenium_exploration_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] JSON报告已保存: {report_path}")
        
        # 生成Markdown报告
        md_report = self._generate_markdown_report()
        md_path = "d:/openclaw/workspace/gdgpo_selenium_exploration_report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)
        
        print(f"[OK] Markdown报告已保存: {md_path}")
        
        return report_path, md_path
    
    def _generate_markdown_report(self):
        """生成Markdown格式的报告"""
        md = []
        md.append("# 广东省政府采购网搜索页面探索报告 (Selenium)\n\n")
        md.append(f"**探索时间**: {self.report['探索时间']}\n\n")
        md.append("---\n\n")
        
        # 基础页面
        md.append("## 1. 基础页面分析\n\n")
        base = self.report.get("基础页面", {})
        md.append(f"- **URL**: {base.get('url', 'N/A')}\n")
        md.append(f"- **最终URL**: {base.get('最终url', 'N/A')}\n")
        md.append(f"- **有tipsPage重定向**: {base.get('有tipsPage重定向', False)}\n")
        md.append(f"- **页面HTML长度**: {base.get('页面HTML长度', 0)} 字节\n")
        
        # 弹窗处理
        popup_info = self.report.get("弹窗处理", {})
        if popup_info.get("检测到的弹窗"):
            md.append("\n### 检测到的弹窗\n\n")
            for popup in popup_info["检测到的弹窗"]:
                md.append(f"- **选择器**: `{popup['选择器']}` (是否可见: {popup['是否可见']})\n")
            md.append(f"\n**弹窗是否成功关闭**: {popup_info.get('是否成功关闭', False)}\n")
        
        # URL参数测试
        md.append("\n## 2. URL参数测试结果\n\n")
        url_tests = self.report.get("URL参数测试", [])
        if url_tests:
            md.append("| 参数 | 搜索框包含关键词 | 搜索结果数量 | 是否成功 |\n")
            md.append("|------|----------------|-------------|----------|\n")
            for test in url_tests:
                if "错误" not in test:
                    success = "[OK]" if test.get('是否成功触发搜索', False) else "[FAIL]"
                    md.append(f"| `{test['参数']}` | {test.get('搜索框包含关键词', False)} | {test.get('搜索结果数量', 0)} | {success} |\n")
        
        # 搜索表单结构
        md.append("\n## 3. 搜索表单结构\n\n")
        forms = self.report.get("搜索表单结构", {})
        
        md.append(f"**搜索表单数量**: {len(forms.get('表单列表', []))}\n\n")
        
        if forms.get("输入框列表"):
            md.append("### 搜索输入框\n\n")
            visible_inputs = [inp for inp in forms["输入框列表"] if inp.get("是否可见")]
            if visible_inputs:
                for i, inp in enumerate(visible_inputs, 1):
                    md.append(f"**输入框 {i}**:\n")
                    md.append(f"- **name**: `{inp.get('name', 'N/A')}`\n")
                    md.append(f"- **id**: `{inp.get('id', 'N/A')}`\n")
                    md.append(f"- **type**: `{inp.get('type', 'N/A')}`\n")
                    md.append(f"- **placeholder**: `{inp.get('placeholder', 'N/A')}`\n")
                    md.append(f"- **class**: `{inp.get('class', 'N/A')}`\n")
                    md.append(f"- **是否可见**: {inp.get('是否可见', False)}\n")
                    md.append(f"- **xpath**: `{inp.get('xpath', 'N/A')}`\n\n")
            else:
                md.append("*没有找到可见的搜索输入框*\n\n")
        
        if forms.get("按钮列表"):
            md.append("### 搜索按钮\n\n")
            visible_buttons = [btn for btn in forms["按钮列表"] if btn.get("是否可见")]
            if visible_buttons:
                for i, btn in enumerate(visible_buttons, 1):
                    md.append(f"**按钮 {i}**:\n")
                    if btn["tag"] == "button":
                        md.append(f"- **text**: `{btn.get('text', 'N/A')}`\n")
                    else:
                        md.append(f"- **value**: `{btn.get('value', 'N/A')}`\n")
                    md.append(f"- **id**: `{btn.get('id', 'N/A')}`\n")
                    md.append(f"- **type**: `{btn.get('type', 'N/A')}`\n")
                    md.append(f"- **class**: `{btn.get('class', 'N/A')}`\n")
                    md.append(f"- **xpath**: `{btn.get('xpath', 'N/A')}`\n\n")
            else:
                md.append("*没有找到可见的搜索按钮*\n\n")
        
        # 搜索结果结构
        md.append("\n## 4. 搜索结果结构\n\n")
        results = self.report.get("搜索结果结构", {})
        md.append(f"- **结果数量**: {results.get('count', 0)}\n\n")
        
        if results.get("items"):
            md.append("### 示例结果条目\n\n")
            for item in results["items"]:
                md.append(f"**条目 {item['索引'] + 1}**:\n")
                if "标题" in item:
                    md.append(f"- **标题**: {item['标题']}\n")
                if "链接" in item:
                    md.append(f"- **链接**: {item['链接']}\n")
                md.append("\n")
        
        # 分页机制
        md.append("## 5. 分页机制\n\n")
        pagination = self.report.get("分页机制", {})
        md.append(f"- **分页元素数量**: {pagination.get('count', 0)}\n\n")
        
        # 详情页链接
        md.append("## 6. 详情页链接格式\n\n")
        detail_links = self.report.get("详情页链接", [])
        if detail_links:
            md.append("### 示例详情页链接\n\n")
            for i, link in enumerate(detail_links[:5], 1):
                md.append(f"**链接 {i}**:\n")
                md.append(f"- **URL**: `{link['href']}`\n")
                md.append(f"- **文本**: {link['链接文本']}\n\n")
        else:
            md.append("*没有找到详情页链接*\n\n")
        
        # 自动化脚本建议
        md.append("---\n\n")
        md.append("## 自动化脚本建议\n\n")
        
        md.append("根据 Selenium 探索结果:\n\n")
        
        # 根据实际结果生成建议
        visible_inputs = [inp for inp in forms.get("输入框列表", []) if inp.get("是否可见")]
        visible_buttons = [btn for btn in forms.get("按钮列表", []) if btn.get("是否可见")]
        
        if visible_inputs:
            md.append("1. **搜索输入框已找到**，可以使用以下 XPath 定位:\n")
            for inp in visible_inputs[:2]:
                if inp.get("xpath"):
                    md.append(f"   - `{inp['xpath']}`\n")
        else:
            md.append("1. **未找到可见的搜索输入框**，可能需要:\n")
            md.append("   - 检查页面是否完全加载\n")
            md.append("   - 是否需要先关闭弹窗\n")
            md.append("   - 页面结构是否有变化\n")
        
        md.append("\n")
        
        successful_param = None
        for test in self.report.get("URL参数测试", []):
            if test.get("是否成功触发搜索", False):
                successful_param = test["参数"]
                break
        
        if successful_param:
            md.append(f"2. **URL参数**: 使用 `{successful_param}` 参数可以直接触发搜索\n")
            md.append(f"   - 示例: `fullSearchingGd?{successful_param}=体育`\n")
        else:
            md.append("2. **URL参数**: 测试的参数均未能直接触发搜索，建议:\n")
            md.append("   - 使用表单提交方式进行搜索\n")
            md.append("   - 或通过 JavaScript 直接操作页面元素\n")
        
        md.append("\n")
        
        if popup_info.get("检测到的弹窗"):
            md.append("3. **弹窗处理**: 页面加载后需要先关闭弹窗\n")
            md.append("   - 建议使用显式等待确保弹窗加载完成\n")
            md.append("   - 使用 try-except 处理弹窗可能不出现的情况\n")
        
        md.append("\n---\n\n")
        md.append("*此报告由 GDGPOSeleniumExplorer 自动生成*\n")
        
        return ''.join(md)
    
    def run(self):
        """执行完整的探索流程"""
        print("\n[START] 开始探索广东省政府采购网搜索页面 (使用 Selenium)")
        print("="*60)
        
        # 初始化浏览器
        if not self.init_driver():
            print("[ERROR] 浏览器初始化失败，无法继续")
            return
        
        try:
            # 步骤1: 探索基础页面
            if not self.explore_base_page():
                print("[ERROR] 基础页面探索失败")
                return
            
            # 步骤2: 测试URL参数
            self.test_url_parameters()
            
            # 步骤3: 分析分页
            self.analyze_pagination()
            
            # 步骤4: 分析详情页链接
            self.analyze_detail_links()
            
            # 步骤5: 生成报告
            json_path, md_path = self.generate_report()
            
            print("\n" + "="*60)
            print("[SUCCESS] 探索完成！")
            print("="*60)
            print(f"\n报告文件:")
            print(f"  - JSON: {json_path}")
            print(f"  - Markdown: {md_path}")
            print("\n")
            
        except Exception as e:
            print(f"[ERROR] 探索过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 关闭浏览器
            if self.driver:
                print("[INFO] 关闭浏览器...")
                self.driver.quit()

if __name__ == "__main__":
    explorer = GDGPOSeleniumExplorer()
    explorer.run()
