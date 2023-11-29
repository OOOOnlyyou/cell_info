import csv
import os
import re
import time
from alive_progress import alive_bar
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class GetCellDetail(object):
    """
    :parameter
        初始参数：
            account：安居客登录账号
            password：登录密码
            browserDriverPath：谷歌驱动所在路径（例如：D:\chromedriver）
            show：是否可视化模拟器界面
        目标参数：
            city：目标城市
            savePath：小区信息输出文件路径（只支持csv文件）
    """

    def __init__(self, account, password, browserDriverPath=None, show=True):
        self.__browser = self.__creatDriver(browserDriverPath, show)
        self.__account = account
        self.__password = password

    @staticmethod
    def __creatDriver(browserDriverPath, show):
        # 驱动配置
        opt = ChromeOptions()
        # ---设置浏览器可视化页面---
        if not show:
            opt.add_argument("--headless")
            opt.add_argument("--disable-gpu")
        # --
        opt.add_experimental_option('excludeSwitches', ['enable-automation'])
        opt.add_experimental_option("detach", True)
        opt.add_argument("--disable-blink-features=AutomationControlled")
        service = Service(executable_path=browserDriverPath)
        # -----实列化一个Chrome对象-----
        _browser = Chrome(options=opt, service=service)
        # _browser.maximize_window()  # 最大化浏览器窗口
        _browser.delete_all_cookies()
        _browser.implicitly_wait(10)
        # 解决特征识别的代码
        _browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                      get: () => undefined
                    })
                  """
        })
        return _browser

    def __logIn(self):
        self.__browser.get('https://login.anjuke.com/login/form')
        if 'login.anjuke.com/login/form' in self.__browser.current_url:
            print('登录中……')
            try:
                WebDriverWait(self.__browser, 10, 0.5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                # 进入iframe
                self.__browser.switch_to.frame('iframeLoginIfm')
                # 登录账号
                self.__browser.find_element(By.ID, "pwdTab").click()
                self.__browser.find_element(By.ID, "checkagree").click()
                self.__browser.find_element(By.ID, "pwdUserNameIpt").send_keys(self.__account)
                self.__browser.find_element(By.ID, "pwdIpt").send_keys(self.__password)
                self.__browser.implicitly_wait(2)
                self.__browser.find_element(By.ID, "pwdSubmitBtn").click()
            except:
                print('登录失败！')
            else:
                print('登录成功！')
                time.sleep(3)

    def __verify(self):
        if 'www.anjuke.com' in self.__browser.current_url and 'captcha-verify' in self.__browser.current_url:
            print('验证中……')
            time.sleep(5)
            print('验证成功！')

    @staticmethod
    def __readDetail(info_list):
        cell_detail = list()
        for info_elem in info_list:
            value = re.split(r'\s', info_elem.text)[1]
            cell_detail.append(value)
        return cell_detail

    def __getCellInfo(self, cell_elem):
        self.__browser.execute_script("arguments[0].target='_blank'", cell_elem)
        cell_elem.click()
        # 切换到子窗口
        self.__browser.switch_to.window(self.__browser.window_handles[-1])
        cell_name, cell_full_address, average_price, cell_detail, sale_source, rent_source = None, None, None, None, None, None
        try:
            cell_name = self.__browser.find_element(By.CLASS_NAME, "title").text
            cell_full_address = self.__browser.find_element(By.CLASS_NAME, "sub-title").text
        except Exception as e1:
            print(e1)
        try:
            average_price = self.__browser.find_element(By.CLASS_NAME, "average").text
        except Exception as e2:
            print(e2)
        try:
            info_list = self.__browser.find_elements(By.XPATH, '//div[@class="column-2"]  |  //div[@class="column-1"]')
            cell_detail = self.__readDetail(info_list)
        except Exception as e3:
            print(e3)
        try:
            sale_source = self.__browser.find_element(By.XPATH,
                                                      '//div[@class="sale"]/a | //div[@class="sale"]/span').text
            rent_source = self.__browser.find_element(By.XPATH,
                                                      '//div[@class="rent"]/a | //div[@class="rent"]/span').text
        except Exception as e4:
            print(e4)
        # 关闭当前子窗口,回到主窗口
        self.__browser.close()
        self.__browser.switch_to.window(self.__browser.window_handles[-1])
        return [cell_name, cell_full_address, average_price, sale_source, rent_source, cell_detail]

    @staticmethod
    def __toCsv(savePath, cellInfo):
        header = (
            'cell', 'full_address', 'avg_price', 'sale_source', 'rent_source', 'property_type', 'ownership_class',
            'completion_time', 'ownership_period', 'households', 'total_area', 'plot_ratio', 'greening_rate',
            'building_type', 'business_circle', 'unified_heating', 'water_power', 'parking_spot', 'property_fee',
            'parking_fee', 'parking_management_fee', 'property_company', 'address', 'developer'
        )
        cellInfoRow = cellInfo[:-1] + cellInfo[-1]
        flag = os.path.exists(savePath)
        with open(savePath, mode='at', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if not flag:
                writer.writerow(header)
            writer.writerow(cellInfoRow)
        print(cellInfoRow[0])

    def run(self, city, savePath=None):
        # 登录账号
        self.__logIn()
        # 如果是滑块验证，就停留5秒，手动滑块验证
        self.__verify()
        # 获取页面小区
        self.__browser.get(f'https://{city}.anjuke.com/community/')
        if savePath is None:
            savePath = city + '-cell_info.csv'
        # 获取小区总数
        total = eval(self.__browser.find_element(By.CLASS_NAME, "total-info").text.split()[1])
        # 获取区域
        regions = self.__browser.find_elements(By.XPATH, "//li[@class='region-item']/a")[1:]
        with alive_bar(total, title='GetCellDetail', force_tty=True) as bar:
            # 遍历区域获取小区
            for region in regions:
                self.__browser.execute_script("arguments[0].target='_blank'", region)
                region.click()
                self.__browser.switch_to.window(self.__browser.window_handles[-1])
                # 获取所有页数小区
                while True:
                    cell_list = self.__browser.find_elements(By.CLASS_NAME, "li-row")
                    for cell_elem in cell_list:
                        cell_info = self.__getCellInfo(cell_elem)
                        if cell_info != [None, None, None, None, None, None]:
                            self.__toCsv(savePath, cell_info)
                        bar()
                    try:
                        self.__browser.find_element(By.CLASS_NAME, "next-active").click()
                    except:
                        break
                self.__browser.close()
                self.__browser.switch_to.window(self.__browser.window_handles[-1])
        self.__browser.quit()
        print('OVER!!!')
