import os
import csv
from datetime import datetime
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



def  calc_profit(price, cost_price, shipping, fee_rate):
    """"docstring
        TODO プログラムの解説を書く

    """
    return price - cost_price - shipping - (price * fee_rate)

#csvファイルへの書き込みを行う関数
def export_result_csv(data: dict):
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
  print(f"CSV出力完了:{filename}")
  return


#csvファイル読み込み関数
def load_csv(filepath):
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
    if profit < 0:
        return "赤字です","red"
    elif profit < 300: 
        return "利益が少なめです。(要塞検討)", "yellow"
    else:
        return "出品候補です", "green"
    
# テスト用関数
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

@app.route('/', methods=["GET","POST"])
def index():
    result = None
    error = None
    judge = None
    judge_class = None

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        cost_price = request.form.get("cost_price")
        shipping = request.form.get("shipping")

        #空欄チェック
        if not name or not price or not cost_price or not shipping:
            error = ERROR_REQUIRED
        else:
            try:
                #入力値チェック後、int型へ変更
                price = int(price)
                cost_price = int(cost_price)
                shipping = int(shipping)

                #数値の正当性をチェック
                if price <= 0 or cost_price <= 0 or shipping <= 0:
                  error = ERROR_POSITYVE
                elif price < cost_price + shipping:
                    error = ERROR_TOO_LOW
                else:
                    #ここで計算処理
                    profit  = int(calc_profit(price, cost_price, shipping, FEE_RATE))
                    profit_rate = int(profit / cost_price * 100) if cost_price > 0 else 0
                    #赤字判定を関数で行う
                    judge, judge_class = judge_profit(profit)
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

                        }
                    #csvファイル書き込み
                    export_result_csv(result)

            except ValueError:
                error = ERROR_NOT_NUMBER

    records = load_csv("output/output.csv")

    #利益でソート
    rows_sorted = sorted(records, key=lambda x: int(x["利益"]), reverse=True)

    return render_template("index.html", result=result, error=error)

@app.route("/history")
def history():
    records = load_csv("output/output.csv")

    #利益で降順ソート
    rows_sorted = sorted(records, key=lambda x: int(x["利益"]), reverse=True)
    return render_template("history.html", records=rows_sorted)


#↓これは一番最後に書いて無きゃいけなさそう
if __name__ == "__main__":
    #test_judge()  # 確認したいときだけ有効化
    app.run(debug=True)

#TODO:
#docstring(プログラムの解説)の記述をする
#index以外のページ遷移とか表示ってできるのだろうか(履歴表示をクローズでもいいけど)
#csvの中身の並べ替え(利益が高い順、日付が新しい順、赤字だけ表示等)
# やること案
# history 画面に
# 利益フィルタ（赤字だけ等）
# 日付ソート
# CSVダウンロード
# 見た目の軽い整形（表の色分け）