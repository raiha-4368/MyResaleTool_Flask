import os
import io
import csv
import uuid
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import send_file
from flask import redirect
from flask import url_for
from flask import Flask, render_template, request

########################################################################
#メルカリ出品前に利益と利益率を計算するツール
#使い方;
#コマンドラインにpython app.py
#実行後、http://127.0.0.1:5000/へアクセス
########################################################################

app = Flask(__name__)

#現状は固定値
#メルカリ手数料10%を想定
FEE_RATE = 0.1 

#エラーメッセージ定義
ERROR_REQUIRED = "すべての項目を入力してください"
ERROR_POSITYVE = "数値は正の値を入力してください"
ERROR_TOO_LOW = "価格が原価+送料を下回っています"
ERROR_NOT_NUMBER = "価格・原価・送料は数値で入力してください"

#ソート機能用
#csvファイルのカラム名とhtmlのページの齟齬を埋めるためのもの
SORT_MAP = {
    "profit": "利益",
    "date": "日時"
}

SORT_CAST = {
    "日時": str,
    "利益": int,
    "価格": int,
    "原価": int,
    "送料": int,
    "利益率": int,
}


#利益計算関数
def  calc_profit(price, cost_price, shipping, fee_rate):
    """
    売値(price)・原価(cost_price)・送料(shipping)・手数料(fee_rate)から
    販売後の最終的な利益額を計算して返す。
    """
    logger.info("def calc_profit 開始")
    profit = price - cost_price - shipping - (price * fee_rate)
    return profit

#csvファイルへの書き込みを行う関数
def export_result_csv(data: dict):
  """
  dataで受け取った計算結果をCSVファイル(output/output.csv)に追記する。
  ファイルが存在しない場合は新規作成し、ヘッダー行も自動で出力する。
  """
  logger.info("def export_result_csv 開始")
  #outputディレクトリがなければ作成
  os.makedirs("output", exist_ok=True)
  #ファイル名を固定とする場合の処理
  filename = "output/output.csv"

  #新規書き込みw,追記モードaで使い分け
  with open(filename, mode="a", newline="", encoding="utf-8") as f:
    write = csv.DictWriter(f, fieldnames=data.keys())
    #見出し行を付ける処理
    if os.path.getsize(filename) == 0:
      write.writeheader()
    #現在ファイル名を固定としているため、csvのカラムを記述する処理はコメントアウト
    #write.writeheader()
    write.writerow(data)
  logger.info(f"CSV出力完了:{filename}")
  return


#csv書き込み関数(上書き用)
# def save_csv(path, data: list[dict]):
#     with open(path, mode="w", newline="", encoding="utf-8") as f:
#         write = csv.DictWriter(f, fieldnames=data[0].keys())
#         write.writeheader()
#         write.writerow(data)
#     print(f"CSV更新完了:{path}")
#     return


def save_csv(path, data):
    logger.info("def save_csv 開始")
    logger.info("書き込み内容: %s", data)
    if not data:
        #全権削除された場合は空ファイルにする
        open(path, "w").close()
        return
    
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()    #ヘッダーは必須
        writer.writerows(data)  #←複数行を書き込む
    logger.info("CSV更新完了:%s", path)

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
    
# テスト用関数
# 通常は実行されない
#if __name__ == "__main__":以下の
#test_judgeのコメントアウトを外した場合、有効化される
def test_judge():
    print("=== test_judge(テスト開始) ===")
    test_cases = [
        (-100, "赤字です"),
        (0, "利益が少なめです。(要塞検討)"),
        (200, "利益が少なめです。(要塞検討)"),
        (300, "出品候補です"),
        (1000, "出品候補です"),
        ]

    for profit, expected in test_cases:
        result, judge_class = judge_profit(profit)
        print(f"profit={profit} -> {result} color:{judge_class} (期待値: {expected})")

        #想定外の結果が出た場合、NGと表示する
        if result != expected:
            print("   - > NG")

    print("=== test_judge(テスト終了) ===")
   
    print("=== calc_profit(テスト開始) ===")
    print(judge_profit(calc_profit(3000, 900, 600, 0.1)))
    print(judge_profit(calc_profit(5000, 300, 500, FEE_RATE)))
    print(judge_profit(calc_profit(2000, 3000, 300, FEE_RATE)))
    print("=== calc_profit(テスト終了) ===")

    return

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
            export_result_csv(result)
    except ValueError:
        error = ERROR_NOT_NUMBER
        logger.warning("数値変換エラー")
 
    if error:
        logger.error("%s",error)

    return result, error


@app.route('/', methods=["GET","POST"])
def index():
    logger.info("def index 開始")
    
    #infoかdebugどっちがいいかは要検討
    logger.debug("URL: %s", request.url)

    result = None
    error = None

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        cost_price = request.form.get("cost_price")
        shipping = request.form.get("shipping")
        #空欄チェック
        if not name or not price or not cost_price or not shipping:
            error = ERROR_REQUIRED
            logger.warning("未入力エラー")
        else:
            #入力値に対する処理を行う
            result,error = input_exe(name, price, cost_price, shipping)

    return render_template("index.html", result=result, error=error)

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

@app.route("/history")
def history():
    """
    history の Docstring
    過去の入力履歴であるoutput.csvを読み込み、それを並び替えもしくは特定条件で絞り込みを行う
    押されたURLによってページ遷移を行い、読み込み、切り替えを行う
    """
    logger.info("def history開始")
    logger.info("URL: %s", request.url)

    records = load_csv("output/output.csv")
    filtered = records

    #渡されたURLのsort=の部分を取得。デフォルトは日付
    sort_parm = request.args.get("sort") or "date"

    #sort_pramを鍵として、SORT_MAPから値を取得(取得できなければデフォルトを日時とする)
    sort_key = SORT_MAP.get(sort_parm, "日時")

    #渡されたURLのfilter部分を取得。デフォルト値は指定なし
    filter_key = request.args.get("filter", None)

    #フィルター(現状は判定カラーのみ)が設定されているのなら
    logger.info("request.args.get=%s", filter_key)

    if filter_key:
        filtered = history_filter(filtered, "判定カラー", filter_key)

    #sort_key(日付、利益)でソートを行う
    filtered = history_sort(filtered, sort_key, True)

    logger.info("sort_parm:%s",sort_parm)
    logger.info("sort_key:%s",sort_key)
    logger.info("filter_key:%s",filter_key)

    return render_template(
        "history.html",
         records=filtered,
         current_sort=sort_parm,
         current_filter=filter_key)

@app.route("/delete_all")
def delete_all():
    logger.info("def delete_all 開始")

    #w モードで開いて空にする
    with open('output/output.csv', 'w', encoding='utf-8') as f:
      pass  # 何もしない

    return redirect(url_for("history"))

@app.route("/delete")
def delete():
    logger.info("def delete 開始")
    #日付を取得
    target_id = request.args.get("id")
    logger.info("CSV削除: target_date= %s", target_id)
    records = load_csv("output/output.csv") 

    #削除対象以外だけを出す
    #以下、省略していない書き方の認識
    # for r in records:
    #     print("確認用")
    #     print("csv date:", repr(r["日時"]))
    #     if r["日時"] == target_date:
    #          print("確認2")
    #          print("ターゲット:",target_date)
    #          print("csvデータ：",r["日時"])
    #          print("一致している！！1回だけの想定")
    #     else:
    #         print("一致していない！これだけを格納想定")
    #         print("ターゲット:",target_date)
    #         print("csvデータ：",r["日時"])

    new_records = [r for r in records if r["ID"] != target_id]
    # print("======削除後のデータ確認======")
    # print(new_records)
    # print("======削除後のデータ確認終了======")
    logger.info("CSV削除: 件数=%s", len(new_records))


    save_csv("output/output.csv" ,new_records)

    #redirect(url_for("history"))は
    #今の関数で画面を描かない、もとのURLに戻して再読み込みの意味がある
    return redirect(url_for("history"))

@app.route("/download")
def download_csv():
    logger.info("def download_csv 開始")

    path = "output/output.csv"
    logger.info("CSVダウンロード実行")
    if not os.path.exists(path):
        return "CSVファイルがありません。"
    return send_file(
        path,
        as_attachment=True,
        download_name = "profit_history.csv",
        mimetype = "text/csv"
    )

@app.route('/import', methods=["POST"])
def import_csv():
    logger.info("def import_csv 開始")
    file = request.files.get("file")

    results = []
    error = None

    logger.info("CSV import 開始: %s", file.filename)

    if not file:
        logger.error("ファイルがアップロードされていません。")
        return redirect("/")
    
    stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
    rows = csv.DictReader(stream)
    logger.info("ファイルにあるデータ: %s", rows)
    count = 0
    for row in rows:
        try:
            logger.info("row確認: %s", row)

            name = str(row["商品名"])
            price= int(row["価格"])
            cost_price= int(row["原価"])
            shipping= int(row["送料"])

            #入力値に対する処理を行う
            result, error = input_exe(name, price, cost_price, shipping)
            results.append(result)
            count += 1
        except Exception as e:
            logger.error("インポート失敗 row=%s, error=%s", row, e)
        
        logger.info("CSV import finished: %s rows", count)

    return render_template("index.html", import_success=True, imported_records=results, error=error)

#↓これは一番最後に書いて無きゃいけなさそう
if __name__ == "__main__":
    #test_judge()  # 確認したいときだけ有効化
    #======================================
    # logging 設定
    #======================================
    os.makedirs("logs", exist_ok=True)

    log_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes = 1024 * 1024, # 1MBでローテーション
        backupCount = 3,        # 古いログを3世代保持
        encoding = "utf-8"
    )
    log_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )
    log_handler.setFormatter(log_formatter)

    logger = logging.getLogger("resale_app")
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)

    app.run(debug=True)

#TODO:
# 改修案
# ①csvファイルのインポート処理
#   ∟計算対象の一括インポート処理
#   ∟実務を考えるならあった方が良さそうな機能
#   ∟難易度が高い?みたいな認識

# 継続課題
# docstring(プログラムの解説)の記述をする
# ∟一応済?もう少しかけることはあるかもしれないけど、コメントだらけで現状でもコメントだらけで見にくいんじゃ?という気もしている
# 見た目の軽い整形(htmlやcssの理解を深める事)
#  ∟継続的な課題。htmlやcssの記述と構造の把握をしていきたい。


# 出来るのか不明なこと
# DB実装
#     ∟現状のcsv管理とは根本から変えなくてはならない認識
#      やる場合はプログラムを分けたい
# 動的な表の実装
#     ∟履歴のページリロード(URLの遷移)ではなく、そのページの状態でフィルタ、ソートができる機能を付ける
#      Javascriptとかphpを駆使することになるのでしょうか、ちょっとわからない



