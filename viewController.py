import sys
from datetime import datetime, timedelta
from collections import deque
import time
from PyQt5.QAxContainer import *
import csv
import threading

'''Input options'''
daily_num = 8
k = 0.5
profit_rate = 1.33     # 1.5 for 1.5%
rate_limit = 10      # 10 for 10%
three_day_mode_on = False

'''Local variables'''
is_processing = 0
working_dates = []
if three_day_mode_on:
    queue_recv = deque(maxlen=3)
else:
    queue_recv = deque(maxlen=2)

above_target_price_dict = {}    # key: date, value: item
above_profit_target_price_dict = {}  # key: date, value: item
companies_above_target_price_dict = {}    # key: date, value: company list
companies_above_profit_target_price_dict = {}  # key: date, value: company list
complement_companies_set_dict = {}      # companies_above_profit_target - companies_above_target


class ViewController:
    def __init__(self):
        super().__init__()

        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.code = ""
        self.name = ""
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
            # self.get_item_list()

    # 종목 리스트 요청
    def get_item_list(self):
        threading.Thread(target=self._get_item_list).start()

    def _get_item_list(self):
        global is_processing
        print("Generating working dates")
        with open("code_name.txt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                words = line.split()

                working_dates.append(datetime.strptime(words[0], "%Y-%m-%d"))
                if words[2] == "끝":
                    if three_day_mode_on:
                        working_dates.append(datetime.strptime(words[1], "%Y-%m-%d"))
                    break

        print("Getting item list")
        with open("code_name.txt", encoding="utf-8") as f:
            curr_date = ""
            cnt = 0
            for line in f:
                line = line.strip()
                words = line.split()

                if curr_date != words[0]:
                    curr_date = words[0]
                    cnt = 1
                else:
                    if cnt >= daily_num:
                        continue
                    cnt = cnt + 1

                if words[2] == "끝":
                    while not three_day_mode_on and is_processing != 2:
                        time.sleep(1)
                    while three_day_mode_on and is_processing != 3:
                        time.sleep(1)
                    try:
                        try:
                            for date, item in above_target_price_dict.items():
                                above_target_price_dict[date].sort(key=lambda q: q[3], reverse=True)
                                above_target_price_dict[date] = above_target_price_dict[date][:daily_num]
                                above_profit_target_price_dict[date].sort(key=lambda q: q[3], reverse=True)
                                above_profit_target_price_dict[date] = above_profit_target_price_dict[date][:daily_num]
                        except:
                            print("Error generating base dicts")

                        try:
                            for key, value in above_target_price_dict.items():
                                companies_above_target_price_dict[key] = [t[2] for t in above_target_price_dict[key] if
                                                                          t[0] == 1]
                                companies_above_profit_target_price_dict[key] = [t[2] for t in
                                                                                 above_profit_target_price_dict[key] if
                                                                                 t[0] == 1]
                                complement_companies_set_dict[key] = list(set(companies_above_target_price_dict[key]) -
                                                                          set(companies_above_profit_target_price_dict[key]))
                        except:
                            print("Error organizing dicts")

                        try:
                            for key, value in complement_companies_set_dict.items():
                                complement_companies_set_dict[key] = [[t[2], t[4], t[5], t[6]] for t in
                                                                      above_target_price_dict[key] if t[2] in value]
                            print("CC sum: {}".format(sum([sum([x[3] for x in value]) for key, value in
                                                           complement_companies_set_dict.items()])))
                        except:
                            print("Error generating cc dict")

                        try:
                            for key, value in above_target_price_dict.items():
                                above_target_price_dict[key] = [sum([x[0] for x in above_target_price_dict[key]])]
                                above_profit_target_price_dict[key] = [sum([x[0] for x in above_profit_target_price_dict[key]])]
                        except:
                            print("Error slicing dicts")

                        sum1 = 0.00000000001  # to escape from divided by zero exception
                        sum2 = 0.00000000001  # same as above
                        for key, value in above_target_price_dict.items():
                            sum1 = sum1 + above_target_price_dict[key][0]
                            sum2 = sum2 + above_profit_target_price_dict[key][0]
                        sum2_divided_by_sum1 = sum2 / sum1
                    except:
                        print("Unknown error occurred while processing whole data")

                    print("Sum1: {}".format(sum1))
                    print("Sum2: {}".format(sum2))
                    print("Sum2/Sum1: {}".format(sum2_divided_by_sum1))

                    print(above_target_price_dict)
                    print(above_profit_target_price_dict)
                    print(companies_above_target_price_dict)
                    print(companies_above_profit_target_price_dict)
                    print(complement_companies_set_dict)

                    data_names = [[above_target_price_dict, "AT"],
                                  [above_profit_target_price_dict, "APT"],
                                  [companies_above_target_price_dict, "CAT"],
                                  [companies_above_profit_target_price_dict, "CAPT"],
                                  [complement_companies_set_dict, "CC"]]

                    for data_name in data_names:
                        with open("K{:.1f}_P{}_{}.csv".format(k, profit_rate, data_name[1]), 'w', newline='') \
                                as my_file:
                            wr = csv.writer(my_file, quoting=csv.QUOTE_ALL)
                            for key, value in data_name[0].items():
                                wr.writerow([key] + value)

                    print("End of this program")
                    sys.exit(0)

                date = datetime.strptime(words[0], "%Y-%m-%d")     # "2018-02-02"

                self.code = words[1]     # "000020"
                while len(self.code) < 6:   # HACK: 0s should be prepended to code
                    self.code = "0" + self.code
                self.name = words[2]     # "동화약품"

                is_processing = 0
                self.get_stock_price_by_day(self.code, date)
                time.sleep(1)

                while is_processing != 1:
                    time.sleep(1)

                next_date = date + timedelta(days=1)
                while next_date not in working_dates:
                    next_date = next_date + timedelta(days=1)

                self.get_stock_price_by_day(self.code, next_date)
                time.sleep(1)

                while is_processing != 2:
                    time.sleep(1)

                if three_day_mode_on:
                    next_date = next_date + timedelta(days=1)
                    while next_date not in working_dates:
                        next_date = next_date + timedelta(days=1)

                    self.get_stock_price_by_day(self.code, next_date)
                    time.sleep(1)

                    while is_processing != 3:
                        time.sleep(1)

    def get_stock_price_by_day(self, code, date):
        self.kiwoom.dynamicCall("SetInputValue(QStirng, QString)", "종목코드", code)
        self.kiwoom.dynamicCall("SetInputValue(QStirng, QString)", "조회일자", date.strftime("%Y%m%d"))
        self.kiwoom.dynamicCall("SetInputValue(QStirng, QString)", "표시구분", "1")
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "일별주가요청", "opt10086", 0, "5001")

    def receive_tr_data(self, s_scr_no, s_rq_name, s_tr_code, s_record_name, s_prev_next,
                        n_data_length, s_error_code, s_message, s_splmMsg):
        global is_processing
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
                        item.insert(1, self.name)
                        item.insert(1, self.code)

                    # [20180816, '우리은행', '000030', 10600, 11050, 11100, 10300, -6.19]
                    # date(0), symbol(1), name(2), close(3), open(4), high(5), low(6), change(7)
                    queue_recv.append(item)
                    if not three_day_mode_on:
                        if len(queue_recv) == 2 and queue_recv[0][1] == queue_recv[1][1] \
                                and queue_recv[0][7] > rate_limit:
                            print("Processing: {}".format(queue_recv))
                            curr_day_item = queue_recv[0]
                            item = queue_recv[1]    # item = next day item
                            curr_uprate = curr_day_item[7]  # use change as uprate value.

                            # 1. 최대값(고가) 이 목표가(target price) 를 넘어선 횟수
                            target_price = item[4] + k * (curr_day_item[5] - curr_day_item[6])
                            if target_price <= item[5]:
                                # [1, '001040', 'CJ', 8000.0], [0, '082740', 'HSD엔진', 275.0, target_price]
                                # key: date, item: [0/1(0), symbol(1), name(2), curr_uprate(3),
                                #                   target_price(4), 당일_종가(5), 수익률(6)].
                                # Use (3) to sort the list.
                                if curr_day_item[0] in above_target_price_dict:
                                    above_target_price_dict[curr_day_item[0]] = \
                                        above_target_price_dict[curr_day_item[0]] + \
                                        [[1, item[1], item[2], curr_uprate, target_price, item[4],
                                          100*(item[3]-target_price)/target_price]]
                                else:
                                    above_target_price_dict[curr_day_item[0]] = [[1, item[1], item[2], curr_uprate,
                                                                                  target_price, item[4],
                                                                                  100*(item[3]-target_price)/target_price]]
                            else:
                                if curr_day_item[0] in above_target_price_dict:
                                    above_target_price_dict[curr_day_item[0]] = above_target_price_dict[curr_day_item[0]] + \
                                                                                [[0, item[1], item[2], curr_uprate, target_price, item[4],
                                                                                  100*(item[3]-target_price)/target_price]]
                                else:
                                    above_target_price_dict[curr_day_item[0]] = [[0, item[1], item[2], curr_uprate,
                                                                                  target_price, item[4],
                                                                                  100*(item[3]-target_price)/target_price]]

                            # 2. 최대값(고가)이 목표가(target price) * 수익률을 넘어선 횟수
                            if ((100.0 + profit_rate) / 100.0) * (item[4] + k * (curr_day_item[5] - curr_day_item[6])) <= \
                                    item[5]:
                                if curr_day_item[0] in above_profit_target_price_dict:
                                    above_profit_target_price_dict[curr_day_item[0]] = \
                                        above_profit_target_price_dict[curr_day_item[0]] + \
                                        [[1, item[1], item[2], curr_uprate, target_price, item[4],
                                          100*(item[3]-target_price)/target_price]]
                                else:
                                    above_profit_target_price_dict[curr_day_item[0]] = [[1, item[1], item[2], curr_uprate,
                                                                                         target_price, item[4],
                                                                                         100*(item[3]-target_price)/target_price]]
                            else:
                                if curr_day_item[0] in above_profit_target_price_dict:
                                    above_profit_target_price_dict[curr_day_item[0]] = \
                                        above_profit_target_price_dict[curr_day_item[0]] + \
                                        [[0, item[1], item[2], curr_uprate, target_price, item[4],
                                          100*(item[3]-target_price)/target_price]]
                                else:
                                    above_profit_target_price_dict[curr_day_item[0]] = [[0, item[1], item[2], curr_uprate,
                                                                                         target_price, item[4],
                                                                                         100*(item[3]-target_price)/target_price]]
                    elif three_day_mode_on:
                        if len(queue_recv) == 3 and queue_recv[0][1] == queue_recv[1][1] and queue_recv[1][1] \
                                == queue_recv[2][1] and queue_recv[0][7] > rate_limit:
                            print("Processing: {}".format(queue_recv))
                            curr_day_item = queue_recv[0]
                            item = queue_recv[1]    # item = next day item
                            next_day_item = queue_recv[2]
                            curr_uprate = curr_day_item[7]  # use change as uprate value.

                            # 1. 최대값(고가) 이 목표가(target price) 를 넘어선 횟수
                            target_price = item[4] + k * (curr_day_item[5] - curr_day_item[6])
                            if target_price <= item[5]:
                                # [1, '001040', 'CJ', 8000.0], [0, '082740', 'HSD엔진', 275.0, target_price]
                                # key: date, item: [0/1(0), symbol(1), name(2), curr_uprate(3),
                                #                   target_price(4), 익일_시가(5), 수익률(6)].
                                # Use (3) to sort the list.
                                if curr_day_item[0] in above_target_price_dict:
                                    above_target_price_dict[curr_day_item[0]] = \
                                        above_target_price_dict[curr_day_item[0]] + \
                                        [[1, item[1], item[2], curr_uprate, target_price, item[4],
                                          100*(next_day_item[4]-target_price)/target_price]]
                                else:
                                    above_target_price_dict[curr_day_item[0]] = [[1, item[1], item[2], curr_uprate,
                                                                                  target_price, item[4],
                                                                                  100*(next_day_item[4]-target_price)
                                                                                  / target_price]]
                            else:
                                if curr_day_item[0] in above_target_price_dict:
                                    above_target_price_dict[curr_day_item[0]] = above_target_price_dict[curr_day_item[0]] \
                                                                                + [[0, item[1], item[2], curr_uprate,
                                                                                    target_price, item[4],
                                                                                    100*(next_day_item[4]-target_price)
                                                                                    / target_price]]
                                else:
                                    above_target_price_dict[curr_day_item[0]] = [[0, item[1], item[2], curr_uprate,
                                                                                  target_price, item[4],
                                                                                  100*(next_day_item[4]-target_price)
                                                                                  / target_price]]

                            # 2. 최대값(고가)이 목표가(target price) * 수익률을 넘어선 횟수
                            if ((100.0 + profit_rate) / 100.0) * (item[4] + k * (curr_day_item[5] - curr_day_item[6])) <= \
                                    item[5]:
                                if curr_day_item[0] in above_profit_target_price_dict:
                                    above_profit_target_price_dict[curr_day_item[0]] = \
                                        above_profit_target_price_dict[curr_day_item[0]] + \
                                        [[1, item[1], item[2], curr_uprate,
                                          target_price, item[4],
                                          100*(next_day_item[4]-target_price)
                                          / target_price]]
                                else:
                                    above_profit_target_price_dict[curr_day_item[0]] = [[1, item[1], item[2], curr_uprate,
                                                                                         target_price, item[4],
                                                                                         100*(next_day_item[4]-target_price)
                                                                                         / target_price]]
                            else:
                                if curr_day_item[0] in above_profit_target_price_dict:
                                    above_profit_target_price_dict[curr_day_item[0]] = \
                                        above_profit_target_price_dict[curr_day_item[0]] + \
                                        [[0, item[1], item[2], curr_uprate,
                                          target_price, item[4],
                                          100*(next_day_item[4]-target_price)
                                          / target_price]]
                                else:
                                    above_profit_target_price_dict[curr_day_item[0]] = [[0, item[1], item[2], curr_uprate,
                                                                                         target_price, item[4],
                                                                                         100*(next_day_item[4]-target_price)
                                                                                         / target_price]]
        except:     # Catch all possible errors
            print("*** Error occurred: {} {}".format(self.code, self.name))
        is_processing = is_processing + 1
