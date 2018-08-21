from datetime import datetime, timedelta
import time
from PyQt5.QAxContainer import *

'''Input options'''
k = 0.5
profit_rate = 0.015


class ViewController:
    def __init__(self):
        super().__init__()

        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        [self.code, self.code_curr] = ["", ""]
        [self.name, self.name_curr] = ["", ""]
        self.login()

        # kiwoom Open API event Trigger
        self.kiwoom.OnEventConnect.connect(self.event_connect)
        self.kiwoom.OnReceiveTrData.connect(self.receive_tr_data)

    def login(self):
        self.kiwoom.dynamicCall("CommConnect()")

    def event_connect(self, err_code):
        if err_code == 0:
            print("Login Succeed")
            self.get_item_list()

    # 종목 리스트 요청
    def get_item_list(self):
        print("Getting item list")
        with open("code_name.txt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                words = line.split()

                date = datetime.strptime(words[0], "%Y-%m-%d")     # "2018-02-02"

                # # Now this program uses date input... is this code needed?
                # if date.weekday() in [5, 6]:
                #     if date.weekday() == 5:
                #         date = date - timedelta(days=1)    # if Saturday change date to Friday
                #         date_prev = date_prev - timedelta(days=1)
                #     elif date.weekday() == 6:
                #         date = date - timedelta(days=2)    # if Sunday change date to Friday
                #         date_prev = date_prev - timedelta(days=2)

                self.code = words[1]     # "000020"
                while len(self.code) < 6:   # HACK: 0s should be prepended to code
                    self.code = "0" + self.code
                self.name = words[2]     # "동화약품"

                if self.code_curr == "":
                    self.code_curr = self.code
                if self.name_curr == "":
                    self.name_curr = self.name
                self.get_stock_price_by_day(self.code, date)

    def get_stock_price_by_day(self, code, date):
        for date in [date, date + timedelta(days=1)]:
            self.kiwoom.dynamicCall("SetInputValue(QStirng, QString)", "종목코드", code)
            self.kiwoom.dynamicCall("SetInputValue(QStirng, QString)", "조회일자", date.strftime("%Y%m%d"))
            self.kiwoom.dynamicCall("SetInputValue(QStirng, QString)", "표시구분", "1")
            self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "일별주가요청", "opt10086", 0, "5001")

    def receive_tr_data(self, s_scr_no, s_rq_name, s_tr_code, s_record_name, s_prev_next,
                        n_data_length, s_error_code, s_message, s_splmMsg):
        try:
            if s_tr_code == "opt10086":
                if s_rq_name == "일별주가요청":
                    item = []
                    for label in ["날짜", "종가", "시가", "고가", "저가", "등락률"]:
                        rtn = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)",
                                                      s_tr_code, s_rq_name, 0, label).strip()
                        if label == "등락률":
                            rtn = float(rtn)
                        else:
                            rtn = abs(int(rtn))

                        item.append(rtn)

                    if len(item) == 6:      # Safe check
                        if self.name == self.name_curr:
                            item.insert(1, self.name)
                            item.insert(1, self.code)
                        else:
                            item.insert(1, self.name_curr)
                            item.insert(1, self.code_curr)

                    self.code_curr = self.code
                    self.name_curr = self.name

                    # [20180816, '우리은행', '000030', 10600, 11050, 11100, 10300, -6.19]
                    # date(0), symbol(1), name(2), close(3), open(4), high(5), low(6), change(7)

                    print(item)
            time.sleep(1)
        except:     # Catch all possible errors
            print("*** Error occurred: {} {}".format(self.code, self.name))
