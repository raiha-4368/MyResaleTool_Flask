from flask import Flask, render_template, request

app = Flask(__name__)

FEE_RATE = 0.1 #メルカリ手数料10%を想定

def  colc_profit(price, cost_price, shipping, fee_rate):
    return price - cost_price - shipping - (price * fee_rate)


@app.route('/', methods=["GET","POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        cost_price = request.form.get("cost_price")
        shipping = request.form.get("shipping")

        #空欄チェック
        if not name or not price or not cost_price or not shipping:
            error = "すべての項目を入力してください"
        else:
            try:
                #入力値チェック後、int型へ変更
                price = int(price)
                cost_price = int(cost_price)
                shipping = int(shipping)

                #数値の正当性をチェック
                if price <= 0 or cost_price <= 0 or shipping <= 0:
                  error = "数値は正の値を入力してください"
                elif price < cost_price + shipping:
                    error = "価格が原価+送料を下回っています。"
                else:
                    #ここで計算処理
                    profit  = int(colc_profit(price, cost_price, shipping, FEE_RATE))
                    profit_rate = int(profit / cost_price * 100) if cost_price > 0 else 0
                    result = {
                        "name": name,
                        "price": price,
                        "cost_price": cost_price,
                        "shipping": shipping,
                        "profit": profit,
                        "profit_rate": profit_rate,
                        }

            except ValueError:
                error = "価格・原価・送料は数値で入力してください。"



        
        # return f"""
        # 商品名: {name}<br>
        # 売値: {price}<br>
        # 原価: {cost_price}<br>
        # 送料: {shipping}<br>
        # """

    return render_template("index.html", result=result, error=error)

if __name__ == "__main__":
    app.run(debug=True)

    #TODO:
    #・入力値バリデーション(未入力・マイナス値)
    #・判定ロジックを関数化
    #・デザインを最低限整える