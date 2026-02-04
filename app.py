import os
import io
import csv
import logging
from logging.handlers import RotatingFileHandler

#======================================
# logging 設定
#======================================

# Logger 作成
logger = logging.getLogger("resale_app")
logger.setLevel(logging.INFO)

# handler 作成
log_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes = 1024 * 1024, # 1MBでローテーション
        backupCount = 3,        # 古いログを3世代保持
        encoding = "utf-8"
    )

# formatter
log_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    )
log_handler.setFormatter(log_formatter)

# handler 登録(重複防止)
if not logger.handlers:
    logger.addHandler(log_handler)

#hundlerを設定した場合、basicConfigは設定しない(重複する)
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
#     filename="logs/app.log",
#     encoding="utf-8"
# )

import logic
from datetime import datetime
from flask import Flask, render_template, request,send_file, redirect, url_for 
from flask import session


########################################################################
#メルカリ出品前に利益と利益率を計算するツール
#使い方;
#コマンドラインにpython app.py
#実行後、http://127.0.0.1:5000/へアクセス
########################################################################

app = Flask(__name__)

#セッションでの情報保持用(必須)
app.secret_key = "dev-secret-key"


#エラーメッセージ定義
ERROR_REQUIRED = "すべての項目を入力してください"

#ソート機能用
#csvファイルのカラム名とhtmlのページの齟齬を埋めるためのもの
SORT_MAP = {
    "profit": "利益",
    "date": "日時"
}

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
        result, judge_class = logic.judge_profit(profit)
        print(f"profit={profit} -> {result} color:{judge_class} (期待値: {expected})")

        #想定外の結果が出た場合、NGと表示する
        if result != expected:
            print("   - > NG")

    print("=== test_judge(テスト終了) ===")
   
    print("=== calc_profit(テスト開始) ===")
    print(logic.judge_profit(logic.calc_profit(3000, 900, 600, 0.1)))
    print(logic.judge_profit(logic.calc_profit(5000, 300, 500, 0.1)))
    print(logic.judge_profit(logic.calc_profit(2000, 3000, 300, 0.1)))
    print("=== calc_profit(テスト終了) ===")

    return

@app.route('/', methods=["GET","POST"])
def index():
    logger.info("def index 開始")
    
    #infoかdebugどっちがいいかは要検討
    logger.debug("URL: %s", request.url)

    result = None
    error = None

    import_result = session.pop("import_result", None)
    import_success = session.pop("import_success", False)
    #今使えていないかもしれないerror
    error = session.pop("import_error", None)

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        cost_price = request.form.get("cost_price")
        shipping = request.form.get("shipping")
        #必須項目の空欄チェック
        if not name or not cost_price or not shipping:
            error = ERROR_REQUIRED
            logger.warning("未入力エラー")
        elif not price and cost_price:
            logger.info("売値設定がない状態で原価入力された場合、いくら足せば利益が出るのか計算する")
            result,error = logic.input_exe(name, 0, cost_price, shipping)

        else:
            #入力値に対する処理を行う
            result,error = logic.input_exe(name, price, cost_price, shipping)

    return render_template("index.html", 
                            result=result,
                            error=error,
                            import_success=import_success,
                            import_records=import_result,)

@app.route("/history")
def history():
    """
    history の Docstring
    過去の入力履歴であるoutput.csvを読み込み、それを並び替えもしくは特定条件で絞り込みを行う
    押されたURLによってページ遷移を行い、読み込み、切り替えを行う
    """
    logger.info("def history開始")
    logger.info("URL: %s", request.url)

    records = logic.load_csv("output/output.csv")
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
        filtered = logic.history_filter(filtered, "判定カラー", filter_key)

    #sort_key(日付、利益)でソートを行う
    filtered = logic.history_sort(filtered, sort_key, True)

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
        #想定されているヘッダーだけ残す
        f.write("商品名,価格,原価,送料,利益,利益率,判定,判定カラー,日時,ID\n")
    logger.info("output/output.csvの履歴データ削除完了")
    return redirect(url_for("history"))

@app.route("/delete")
def delete():
    logger.info("def delete 開始")
    #日付を取得
    target_id = request.args.get("id")
    logger.info("CSV削除: target_date= %s", target_id)
    records = logic.load_csv("output/output.csv") 

    new_records = [r for r in records if r["ID"] != target_id]
    logger.info("CSV削除後: 件数=%s", len(new_records))

    #csv書き込み
    logic.csv_write_control(None, new_records)

    #redirect(url_for("history"))は
    #今の関数で画面を描かない、もとのURLに戻して再読み込みの意味がある
    #request.referrerでソートやフィルターの状態を持ちこしてhistoryに戻る
    return redirect(request.referrer or url_for("history"))

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
            result, error = logic.input_exe(name, price, cost_price, shipping)
            results.append(result)
            count += 1
        except Exception as e:
            logger.error("インポート失敗 row=%s, error=%s", row, e)
        
        logger.info("CSV import finished: %s rows", count)

    session["import_result"] = results
    session["import_success"] = True
    session["import errror"] = error

#    render_template("index.html", import_success=True, imported_records=results, error=error)
    return redirect(url_for("index"))
#↓これは一番最後に書いて無きゃいけなさそう
if __name__ == "__main__":
    #test_judge()  # 確認したいときだけ有効化
    os.makedirs("logs", exist_ok=True)

    app.run(debug=True)



