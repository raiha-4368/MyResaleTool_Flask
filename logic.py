import os
import io
import csv
import uuid
import logging
from datetime import datetime

########################################################################
#メルカリ出品前に利益と利益率を計算するツールのロジック
#使い方;
#コマンドラインにpython app.py
#実行後、http://127.0.0.1:5000/へアクセス
########################################################################
#現状は固定値
#メルカリ手数料10%を想定
FEE_RATE = 0.1 

#エラーメッセージ定義
ERROR_POSITYVE = "数値は正の値を入力してください"
ERROR_TOO_LOW = "価格が原価+送料を下回っています"
ERROR_NOT_NUMBER = "価格・原価・送料は数値で入力してください"

#ソート機能用
SORT_CAST = {
    "日時": str,
    "利益": int,
    "価格": int,
    "原価": int,
    "送料": int,
    "利益率": int,
}

#app.pyからlog設定を取得
logger = logging.getLogger(__name__)

#利益計算関数
def  calc_profit(price, cost_price, shipping, fee_rate):
    """
    売値(price)・原価(cost_price)・送料(shipping)・手数料(fee_rate)から
    販売後の最終的な利益額を計算して返す。
    """
    logger.info("def calc_profit 開始")
    profit = price - cost_price - shipping - (price * fee_rate)
    return profit

#csv書き込み関数
def write_csv(f_mode, data):
    logger.info("def write_csv 開始")

    #outputディレクトリがなければ作成
    os.makedirs("output", exist_ok=True)
    filename = "output/output.csv"
    
    if not data:
        #全権削除された場合は空ファイルにする
        open(filename, "w").close()
        return
    
    #新規書き込みw,追記モードaで使い分け
    with open(filename, mode=f_mode, newline="", encoding="utf-8") as f:
        write = csv.DictWriter(f, fieldnames=data.keys())
        #サイズが0なら見出し行を付ける処理
        if os.path.getsize(filename) == 0:
            write.writeheader()
        write.writerow(data)
        #複数行を書き込む処理(forで1回ずつ書き込んでいるので使用しない)
        #writer.writerows(data)
    logger.info(f"CSV出力完了:{filename}")
    return


#scvの書き込み制御(dataは1件、datasは複数件)
def csv_write_control(data, datas):
    count = 0
    #データが1件だけなら追記(a)
    if data:
        write_csv("a",data)
    else:
        if not datas:
            write_csv("w",None)
        #データが複数件なら最初の1回だけ(w)
        for r in datas:
            if count == 0:
                write_csv("w",r)
                count+=1
            else:
                write_csv("a", r)
    return

#csvファイル読み込み関数
def load_csv(filepath):
    """
    ファイルパスを受け取り、csvファイルを読み込み、その配列を返す。
    """
    records = []
    if not os.path.exists(filepath):
        return records

    with open(filepath,newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records

#売買時購入の判定処理を関数化
def judge_profit(profit):
    """
    受け取った値を販売時の利益(profit)とし、利益が出ているかを判定し、
    表示用メッセージとCSS用クラス名を返す。
    判定基準は以下の通り
    利益0円未満：赤字
    利益300未満：利益が少なめ
    利益300円以上：出品候補
    """
    if profit < 0:
        return "赤字です","red"
    elif profit < 300: 
        return "利益が少なめです。(要塞検討)", "yellow"
    else:
        return "出品候補です", "green"
    
#入力値に対する処理をindexから分離し、importでも使えるようにした関数
def input_exe(name, price, cost_price, shipping):
    logger.info("def input_exe 開始")
    try:
        name = str(name)
        price = int(price)
        cost_price = int(cost_price)
        shipping = int(shipping)
        judge = None
        judge_class = None
        result = None
        error = None

        logger.info("入力受付: name=%s, price=%s, cost=%s, shipping=%s", name,price,cost_price,shipping)

        #数値の正当性をチェック
        if price <= 0 or cost_price <= 0 or shipping <= 0:
            error = ERROR_POSITYVE
        elif price < cost_price + shipping:
            error = ERROR_TOO_LOW

        else:
            logger.info("入力値正常性確認完了")

            #ここで計算処理
            profit  = int(calc_profit(price, cost_price, shipping, FEE_RATE))
            logger.info("profit = %s", profit)
            profit_rate = int(profit / cost_price * 100) if cost_price > 0 else 0
            logger.info("profit_rate = %s", profit_rate)
            #赤字判定を関数で行う
            judge, judge_class = judge_profit(profit)
            logger.info("計算完了 profit=%s, judge=%s", profit, judge)
            result = {
                "商品名": name,
                "価格": price,
                "原価": cost_price,
                "送料": shipping,
                "利益": profit,
                "利益率": profit_rate,
                "判定": judge,
                "判定カラー": judge_class,
                "日時": datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),
                'ID': str(uuid.uuid4()),
            }
            #csvファイル書き込み
            csv_write_control(result, None)
    except ValueError:
        error = ERROR_NOT_NUMBER
        logger.info("数値変換エラー")
 
    if error:
        logger.info("%s",error)

    return result, error

#ソート機能を独立
def history_sort(records, sort_key, flag):
    logger.info("def history_sort 開始")
    cast = SORT_CAST.get(sort_key, str)
    logger.info("%sソート実施", sort_key)
    logger.info("レコード件数(ソート前):%s件数", len(records))
    sort_records = sorted(records, key=lambda x: cast(x[sort_key]), reverse=flag)
    logger.info("レコード件数:%s件数", len(sort_records))
    #数値の場合、int変換する必要があるため、分岐処理
    # if sort_key in ("利益","価格","原価","送料","利益率"):
    #     sort_records = sorted(records, key=lambda x: int(x[sort_key]), reverse=flag)
    # else:
    #     sort_records = sorted(records, key=lambda x: x[sort_key], reverse=flag)
    return sort_records

#フィルター機能を独立
def history_filter(records, filter_word,filter_key):
    logger.info("def history_filter 開始")
    logger.info("%sフィルター実施(key)", filter_key)
    logger.info("%sフィルター実施(word)", filter_word)

    logger.info("レコード件数(フィルタ前):%s件数", len(records))
    filter_records = [ r for r in records if r[filter_word] == filter_key]
    logger.info("レコード件数(フィルタ後):%s件数", len(filter_records))
    return filter_records
