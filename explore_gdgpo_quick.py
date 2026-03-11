#!/usr/bin/env python3
"""
广东省政府采购网搜索页面探索脚本 - Selenium + webdriver-manager 版本
自动下载和管理 ChromeDriver，无需手动配置
"""

import json
import time
from datetime import datetime
import sys

print("[INFO] 正在导入依赖库...")

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    print("[OK] Selenium 导入成功")
except ImportError as e:
    print(f"[ERROR] Selenium 导入失败: {e}")
    print("请运行: pip install selenium")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    print("[OK] webdriver_manager 导入成功")
except ImportError as e:
    print(f"[ERROR] webdriver_manager 导入失败: {e}")
    print("请运行: pip install webdriver-manager")
    sys.exit(1)

class QuickGDGPOExplorer:
    """快速探索器 - 专注于核心信息"""
    
    def __init__(self):
        self.base_url = "https://gdgpo.czt.gd.gov.cn"
        self.driver = None
        self.findings = {
            "探索时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "页面可访问": False,
            "弹窗情况": {},
            "搜索输入框": [],
            "搜索按钮": [],
            "URL参数测试": [],
            "后续建议": []
        }
    
    def init_driver(self):
        """初始化浏览器"""
        print("\n[INFO] 初始化 Chrome 浏览器...")
        print("[INFO] 首次运行会自动下载 ChromeDriver，请稍候...")
        
        try:
            # 使用 webdriver-manager 自动管理驱动
            service = Service(ChromeDriverManager().install())
            
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(5)
            
            print("[OK] 浏览器初始化成功")
            return True
            
        except Exception as e:
            print(f"[ERROR] 浏览器初始化失败: {str(e)}")
            return False
    
    def explore(self):
        """快速探索"""
        print("\n" + "="*60)
        print("开始探索广东省政府采购网搜索页面")
        print("="*60)
        
        url = f"{self.base_url}/maincms-web/fullSearchingGd"
        
        try:
            # 步骤 1: 访问页面
            print(f"\n[1/6] 访问页面: {url}")
            self.driver.get(url)
            self.findings["页面可访问"] = True
            time.sleep(3)
            
            # 截图
            self.driver.save_screenshot("d:/openclaw/workspace/screenshot_01_initial.png")
            print("[OK] 截图: screenshot_01_initial.png")
            
            # 步骤 2: 检查弹窗
            print("\n[2/6] 检查弹窗...")
            popup_found = self._check_and_close_popup()
            self.findings["弹窗情况"]["检测到弹窗"] = popup_found
            self.findings["弹窗情况"]["是否成功关闭"] = False
            
            if popup_found:
                time.sleep(2)
                self.driver.save_screenshot("d:/openclaw/workspace/screenshot_02_after_popup.png")
                print("[OK] 截图: screenshot_02_after_popup.png")
            
            # 步骤 3: 查找搜索框
            print("\n[3/6] 查找搜索输入框...")
            inputs = self._find_search_inputs()
            self.findings["搜索输入框"] = inputs
            print(f"[INFO] 找到 {len(inputs)} 个可能的搜索输入框")
            
            # 步骤 4: 查找搜索按钮
            print("\n[4/6] 查找搜索按钮...")
            buttons = self._find_search_buttons()
            self.findings["搜索按钮"] = buttons
            print(f"[INFO] 找到 {len(buttons)} 个可能的搜索按钮")
            
            # 步骤 5: 测试 URL 参数
            print("\n[5/6] 测试 URL 参数...")
            self._test_url_params()
            
            # 步骤 6: 尝试手动搜索
            print("\n[6/6] 尝试执行搜索...")
            search_success = self._try_search()
            
            if search_success:
                self.driver.save_screenshot("d:/openclaw/workspace/screenshot_03_search_results.png")
                print("[OK] 截图: screenshot_03_search_results.png")
            
        except Exception as e:
            print(f"[ERROR] 探索过程出错: {str(e)}")
            self.findings["错误"] = str(e)
    
    def _check_and_close_popup(self):
        """检查并关闭弹窗"""
        try:
            # 检查常见弹窗
            popup_selectors = [
                (By.CLASS_NAME, "mainNoticeBox"),
                (By.CLASS_NAME, "noticeCloseBtn"),
                (By.XPATH, "//*[contains(@class, 'modal')]"),
                (By.XPATH, "//*[contains(@class, 'popup')]"),
            ]
            
            for by, selector in popup_selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    if elements and elements[0].is_displayed():
                        self.findings["弹窗情况"]["弹窗选择器"] = selector
                        print(f"[INFO] 检测到弹窗: {selector}")
                        
                        # 尝试关闭
                        close_selectors = [
                            (By.CLASS_NAME, "noticeCloseBtn"),
                            (By.XPATH, "//*[text()='x']"),
                            (By.XPATH, "//*[text()='X']"),
                            (By.XPATH, "//*[contains(text(), '关闭')]"),
                        ]
                        
                        for close_by, close_sel in close_selectors:
                            try:
                                close_btn = self.driver.find_element(close_by, close_sel)
                                if close_btn.is_displayed():
                                    close_btn.click()
                                    self.findings["弹窗情况"]["是否成功关闭"] = True
                                    self.findings["弹窗情况"]["关闭按钮"] = close_sel
                                    print(f"[OK] 成功关闭弹窗")
                                    return True
                            except:
                                pass
                        
                        return True  # 找到了弹窗但未能关闭
                except:
                    pass
            
            print("[INFO] 未检测到弹窗")
            return False
            
        except Exception as e:
            print(f"[WARN] 弹窗检查出错: {str(e)}")
            return False
    
    def _find_search_inputs(self):
        """查找搜索输入框"""
        inputs = []
        
        try:
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            
            for inp in all_inputs:
                try:
                    if not inp.is_displayed():
                        continue
                    
                    inp_type = inp.get_attribute("type") or ""
                    inp_name = inp.get_attribute("name") or ""
                    inp_id = inp.get_attribute("id") or ""
                    inp_placeholder = inp.get_attribute("placeholder") or ""
                    inp_class = inp.get_attribute("class") or ""
                    
                    # 判断是否可能是搜索框
                    search_keywords = ['search', 'keyword', 'query', '搜索', '关键']
                    is_likely_search = any(
                        kw in inp_name.lower() or 
                        kw in inp_id.lower() or 
                        kw in inp_placeholder.lower() or
                        kw in inp_class.lower()
                        for kw in search_keywords
                    )
                    
                    if is_likely_search or inp_type.lower() in ['text', 'search']:
                        info = {
                            "type": inp_type,
                            "name": inp_name,
                            "id": inp_id,
                            "placeholder": inp_placeholder,
                            "class": inp_class[:100],  # 限制长度
                            "可能性": "高" if is_likely_search else "中",
                        }
                        
                        # 尝试获取 XPath
                        try:
                            xpath = self.driver.execute_script(
                                """
                                function getXPath(el) {
                                    if (el.id) return '//*[@id="' + el.id + '"]';
                                    if (el === document.body) return '/html/body';
                                    var ix = 0;
                                    var siblings = el.parentNode.childNodes;
                                    for (var i = 0; i < siblings.length; i++) {
                                        var sib = siblings[i];
                                        if (sib === el) {
                                            return getXPath(el.parentNode) + '/' + el.tagName.toLowerCase() + '[' + (ix+1) + ']';
                                        }
                                        if (sib.nodeType === 1 && sib.tagName === el.tagName) ix++;
                                    }
                                }
                                return getXPath(arguments[0]);
                                """,
                                inp
                            )
                            info["xpath"] = xpath
                        except:
                            info["xpath"] = "无法获取"
                        
                        inputs.append(info)
                        print(f"  - 找到输入框: id={inp_id or '(无)'}, name={inp_name or '(无)'}")
                except:
                    pass
        except:
            pass
        
        return inputs
    
    def _find_search_buttons(self):
        """查找搜索按钮"""
        buttons = []
        
        try:
            # 查找 button 标签
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            
            for btn in all_buttons:
                try:
                    if not btn.is_displayed():
                        continue
                    
                    btn_text = btn.text.strip()
                    btn_type = btn.get_attribute("type") or ""
                    btn_id = btn.get_attribute("id") or ""
                    btn_class = btn.get_attribute("class") or ""
                    
                    # 判断是否可能是搜索按钮
                    search_keywords = ['search', 'submit', '搜索', '查询', '检索']
                    is_likely_search = any(
                        kw in btn_text.lower() or 
                        kw in btn_id.lower() or 
                        kw in btn_class.lower()
                        for kw in search_keywords
                    )
                    
                    if is_likely_search or btn_type.lower() == 'submit':
                        info = {
                            "tag": "button",
                            "text": btn_text,
                            "type": btn_type,
                            "id": btn_id,
                            "class": btn_class[:100],
                            "可能性": "高" if is_likely_search else "中",
                        }
                        
                        # 尝试获取 XPath
                        try:
                            xpath = self.driver.execute_script(
                                """
                                function getXPath(el) {
                                    if (el.id) return '//*[@id="' + el.id + '"]';
                                    var ix = 0;
                                    var siblings = el.parentNode.childNodes;
                                    for (var i = 0; i < siblings.length; i++) {
                                        var sib = siblings[i];
                                        if (sib === el) {
                                            return getXPath(el.parentNode) + '/' + el.tagName.toLowerCase() + '[' + (ix+1) + ']';
                                        }
                                        if (sib.nodeType === 1 && sib.tagName === el.tagName) ix++;
                                    }
                                }
                                return getXPath(arguments[0]);
                                """,
                                btn
                            )
                            info["xpath"] = xpath
                        except:
                            info["xpath"] = "无法获取"
                        
                        buttons.append(info)
                        print(f"  - 找到按钮: text='{btn_text}', id={btn_id or '(无)'}")
                except:
                    pass
        except:
            pass
        
        return buttons
    
    def _test_url_params(self):
        """测试 URL 参数"""
        test_params = ["keywords", "searchWord", "keyword"]
        
        for param in test_params:
            try:
                url = f"{self.base_url}/maincms-web/fullSearchingGd?{param}=体育"
                print(f"  - 测试: ?{param}=体育")
                self.driver.get(url)
                time.sleep(2)
                
                # 检查输入框是否有值
                has_value = False
                try:
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    for inp in inputs:
                        if inp.get_attribute("value") == "体育":
                            has_value = True
                            break
                except:
                    pass
                
                self.findings["URL参数测试"].append({
                    "参数": param,
                    "是否有效": has_value
                })
                
                if has_value:
                    print(f"    [OK] 参数有效！")
                else:
                    print(f"    [FAIL] 参数无效")
                
            except Exception as e:
                print(f"    [ERROR] 测试失败: {str(e)}")
    
    def _try_search(self):
        """尝试执行搜索"""
        try:
            # 回到基础页面
            self.driver.get(f"{self.base_url}/maincms-web/fullSearchingGd")
            time.sleep(2)
            
            # 尝试找到并使用第一个搜索框
            if self.findings["搜索输入框"]:
                inp_info = self.findings["搜索输入框"][0]
                
                # 尝试通过 ID 定位
                if inp_info.get("id"):
                    try:
                        inp = self.driver.find_element(By.ID, inp_info["id"])
                        inp.clear()
                        inp.send_keys("体育")
                        print(f"[OK] 成功输入搜索词")
                        time.sleep(1)
                        
                        # 尝试点击搜索按钮
                        if self.findings["搜索按钮"]:
                            btn_info = self.findings["搜索按钮"][0]
                            if btn_info.get("id"):
                                try:
                                    btn = self.driver.find_element(By.ID, btn_info["id"])
                                    btn.click()
                                    print(f"[OK] 成功点击搜索按钮")
                                    time.sleep(3)
                                    return True
                                except:
                                    pass
                    except:
                        pass
            
            print("[WARN] 无法自动执行搜索")
            return False
            
        except Exception as e:
            print(f"[ERROR] 搜索失败: {str(e)}")
            return False
    
    def generate_report(self):
        """生成报告"""
        print("\n" + "="*60)
        print("生成探索报告")
        print("="*60)
        
        # JSON 报告
        json_path = "d:/openclaw/workspace/gdgpo_quick_exploration.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.findings, f, ensure_ascii=False, indent=2)
        print(f"[OK] JSON 报告: {json_path}")
        
        # 简化的文本报告
        txt_path = "d:/openclaw/workspace/gdgpo_quick_exploration.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("广东省政府采购网 - 快速探索报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"探索时间: {self.findings['探索时间']}\n\n")
            
            f.write("1. 页面访问\n")
            f.write(f"   - 可访问: {'是' if self.findings['页面可访问'] else '否'}\n\n")
            
            f.write("2. 弹窗情况\n")
            popup_info = self.findings.get('弹窗情况', {})
            f.write(f"   - 检测到弹窗: {'是' if popup_info.get('检测到弹窗') else '否'}\n")
            if popup_info.get('检测到弹窗'):
                f.write(f"   - 成功关闭: {'是' if popup_info.get('是否成功关闭') else '否'}\n")
                if popup_info.get('弹窗选择器'):
                    f.write(f"   - 选择器: {popup_info['弹窗选择器']}\n")
            f.write("\n")
            
            f.write("3. 搜索输入框\n")
            if self.findings['搜索输入框']:
                for i, inp in enumerate(self.findings['搜索输入框'], 1):
                    f.write(f"   输入框 {i}:\n")
                    f.write(f"     - ID: {inp.get('id', '(无)')}\n")
                    f.write(f"     - Name: {inp.get('name', '(无)')}\n")
                    f.write(f"     - Placeholder: {inp.get('placeholder', '(无)')}\n")
                    f.write(f"     - XPath: {inp.get('xpath', '无')}\n")
                    f.write(f"     - 可能性: {inp.get('可能性', '未知')}\n\n")
            else:
                f.write("   未找到明显的搜索输入框\n\n")
            
            f.write("4. 搜索按钮\n")
            if self.findings['搜索按钮']:
                for i, btn in enumerate(self.findings['搜索按钮'], 1):
                    f.write(f"   按钮 {i}:\n")
                    f.write(f"     - 文字: {btn.get('text', '(无)')}\n")
                    f.write(f"     - ID: {btn.get('id', '(无)')}\n")
                    f.write(f"     - XPath: {btn.get('xpath', '无')}\n")
                    f.write(f"     - 可能性: {btn.get('可能性', '未知')}\n\n")
            else:
                f.write("   未找到明显的搜索按钮\n\n")
            
            f.write("5. URL 参数测试\n")
            if self.findings['URL参数测试']:
                for test in self.findings['URL参数测试']:
                    result = "有效" if test['是否有效'] else "无效"
                    f.write(f"   - {test['参数']}: {result}\n")
            else:
                f.write("   未进行测试\n")
            f.write("\n")
            
            f.write("=" * 60 + "\n")
            f.write("建议\n")
            f.write("=" * 60 + "\n")
            f.write("1. 查看生成的截图文件了解页面实际状态\n")
            f.write("2. 如果找到了输入框和按钮，使用其 XPath 进行自动化\n")
            f.write("3. 如果 URL 参数无效，则必须通过表单提交搜索\n")
            f.write("4. 建议使用浏览器开发者工具手动确认元素\n")
        
        print(f"[OK] 文本报告: {txt_path}")
        
        return json_path, txt_path
    
    def run(self):
        """运行探索"""
        if not self.init_driver():
            print("[ERROR] 无法初始化浏览器，探索终止")
            return
        
        try:
            self.explore()
            json_path, txt_path = self.generate_report()
            
            print("\n" + "="*60)
            print("探索完成！")
            print("="*60)
            print(f"\n报告文件:")
            print(f"  - JSON: {json_path}")
            print(f"  - TXT: {txt_path}")
            print(f"\n截图文件:")
            print(f"  - screenshot_01_initial.png")
            print(f"  - screenshot_02_after_popup.png (如果有弹窗)")
            print(f"  - screenshot_03_search_results.png (如果搜索成功)")
            print("\n")
            
        except Exception as e:
            print(f"[ERROR] 探索失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                print("[INFO] 5 秒后关闭浏览器...")
                time.sleep(5)
                self.driver.quit()
                print("[OK] 浏览器已关闭")

if __name__ == "__main__":
    explorer = QuickGDGPOExplorer()
    explorer.run()
