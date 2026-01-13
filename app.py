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

#ソート機能用
#csvファイルのカラム名とhtmlのページの齟齬を埋めるためのもの
SORT_MAP = {
    "profit": "利益",
    "date": "日時"
}

#利益計算関数
def  calc_profit(price, cost_price, shipping, fee_rate):
    """
    売値(price)・原価(cost_price)・送料(shipping)・手数料(fee_rate)から
    販売後の最終的な利益額を計算して返す。
    """
    return price - cost_price - shipping - (price * fee_rate)

#csvファイルへの書き込みを行う関数
def export_result_csv(data: dict):
  """
  dataで受け取った計算結果をCSVファイル(output/output.csv)に追記する。
  ファイルが存在しない場合は新規作成し、ヘッダー行も自動で出力する。
  """
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


#csv書き込み関数(上書き用)
# def save_csv(path, data: list[dict]):
#     with open(path, mode="w", newline="", encoding="utf-8") as f:
#         write = csv.DictWriter(f, fieldnames=data[0].keys())
#         write.writeheader()
#         write.writerow(data)
#     print(f"CSV更新完了:{path}")
#     return


def save_csv(path, data):
    print("------書き込み内容確認------")
    print(data)
    print("------書き込み内容確認終了------")
    if not data:
        #全権削除された場合は空ファイルにする
        open(path, "w").close()
        return
    
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()    #ヘッダーは必須
        writer.writerows(data)  #←複数行を書き込む
    print(f"CSV更新完了:{path}")

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

    return render_template("index.html", result=result, error=error)

#ソート機能を独立
def history_sort(records, sort_key, flag):

    #数値の場合、int変換する必要があるため、分岐処理
    if sort_key in ("利益","価格","原価","送料"):
        sort_records = sorted(records, key=lambda x: int(x[sort_key]), reverse=flag)
    else:
        sort_records = sorted(records, key=lambda x: x[sort_key], reverse=flag)
    return sort_records

#フィルター機能を独立
def history_filter(records, filter_word,filter_key):
    return [ r for r in records if r[filter_word] == filter_key]

@app.route("/history")
def history():
    """
    history の Docstring
    過去の入力履歴であるoutput.csvを読み込み、それを並び替えもしくは特定条件で絞り込みを行う
    押されたURLによってページ遷移を行い、読み込み、切り替えを行う
    """
    records = load_csv("output/output.csv")
    filtered = records

    #渡されたURLのsort=の部分を取得。デフォルトは日付
    sort_parm = request.args.get("sort", "date") 
    sort_key = SORT_MAP.get(sort_parm, "日時")

    #渡されたURLのfilter部分を取得。デフォルト値は指定なし
    filter_key = request.args.get("filter", None)

    #フィルター(現状は判定カラーのみ)が設定されているのなら
    if filter_key != None:
        filtered = history_filter(filtered, "判定カラー", filter_key)

    #sort_key(日付、利益)でソートを行う
    filtered = history_sort(filtered, sort_key, True)
    
    return render_template("history.html", records=filtered)

@app.route("/delete")
def delete():
    #日付を取得
    target_date = request.args.get("date")

    records = load_csv("output/output.csv") 

    #削除対象以外だけを出す
    #以下、省略していない書き方の認識
    for r in records:
        print("確認用")
        print("csv date:", repr(r["日時"]))
        if r["日時"] == target_date:
             print("確認2")
             print("ターゲット:",target_date)
             print("csvデータ：",r["日時"])
             print("一致している！！1回だけの想定")
        else:
            print("一致していない！これだけを格納想定")
            print("ターゲット:",target_date)
            print("csvデータ：",r["日時"])

    new_records = [r for r in records if r["日時"] != target_date]
    print("======削除後のデータ確認======")
    print(new_records)
    print("======削除後のデータ確認終了======")


    save_csv("output/output.csv" ,new_records)

    return render_template("history.html")


#↓これは一番最後に書いて無きゃいけなさそう
if __name__ == "__main__":
    #test_judge()  # 確認したいときだけ有効化
    app.run(debug=True)

#TODO:
#改修案

#優先度-1
#csvの中身の並べ替え(利益が高い順、日付が新しい順、赤字だけ表示等)
# ∟ページリロードで色々出来るようにしたいかもしれない
# 利益フィルタ（赤字だけ等）
#  ∟履歴画面で表示するものにも赤字などのcssを反映させる
#  ∟一応上記は実装済み(改修の可能性はあるけども)

#優先度-2
#outputの中身を削除出来るようにする(DB化でもcsvから削除でも)
# ∟現状DB化などは出来ていないので、csvファイルを弄る方向性ならできるかも?
# ∟1件ずつの削除は出来た、全権削除は未実装

#優先度-3
# CSVダウンロード
#  ∟ダウンロードボタンを付けて、output.csvを任意のディレクトリに保存させる処理を実装したい

#優先度-4
# logファイルの実装
# ∟現状では必要性がないが、あった方がいいとは思う。

#優先度-5
# 見た目の軽い整形（表の色分け）
#  ∟継続的な課題。htmlやcssの記述と構造の把握をしていきたい。

#優先度-6
# 難易度が高いため、優先度低
# csvファイルをインポートすることで、一括で処理できるような機能を追加
#  ∟出来たらいいなとは思っている

#継続課題
#docstring(プログラムの解説)の記述をする
# ∟一応済?もう少しかけることはあるかもしれないけど、コメントだらけで現状でもコメントだらけで見にくいんじゃ?という気もしている



#追加課題
#index.html↔history.htmlの相互移動を可能にすること
#∟実行テストのときちょっとめんどくさい

