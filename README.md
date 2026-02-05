# MyResaleTool_Flask
## フリマ出品向け 売買利益計算ツール概要（Webアプリ）
売買時（メルカリ等の出品前）に、  
売値・原価・送料から利益と利益率を計算する簡易ツールです。  
Python（Flask）で作成しています。  
※ 本ツールは学習目的で作成した個人開発アプリです。  

## できること
- 商品名・売値・原価・送料の入力
- 利益・利益率の計算
- 赤字／低利益／出品候補の判定表示
- 入力値のcsvインポート/今までの計算結果のcsvエクスポート

## 使用技術
- Python
- Flask

## 想定ユーザー
メルカリ・ヤフオク等で商品を仕入れて販売する個人出品車向けの、出品前の利益確認ツールです。

## 環境
- Python 3.10 以上
- Flask

## セットアップ
### 仮想環境作成
python -m venv venv

### 仮想環境有効化
Windows:
venv\Scripts\activate

Mac:
source venv/bin/activate

### 依存関係インストール
pip install -r requirements.txt

## フォルダ構成(仮想環境を作成した場所によって異なりますが以下を推奨)
flask/  
├ myenv/←上記コマンドで作成した仮想環境（こちらはGit管理しない）  
flask_test/    
├─docs  
│  └─****.png (実行時のスクリーンショット各種)    
├─logs  
│  └─app.log  
├─output  
│  └─output.csv  
│  └─test_input.csv (importテスト用のデータ)  
├─static  
│  └─css  
├─templates  
│  └ index.html  
│  └ history.html  
└─test  
│  └─logig_test.py  
├ app.py  
├ logic.py  
└ requirements.txt  
└ .gitignore  

## 起動及び使用手順
python app.py

上記実行後、以下へコマンドラインに表示されるアドレス(以下デフォルト)へアクセス  
http://127.0.0.1:5000/  

### 使用手順
1. 商品名,価格,原価,送料の入力値を受け取り、利益,利益率を出し、出品対象となるかどうかの判定を行う。
	 価格が未入力の場合、利益が300円以上になるよう自動計算する。  
2. 1の処理をcsvファイルによるインポートを行うことで、複数件同時に行うことができる。
3. 履歴をoutput以下にcsv形式で保持し、プログラム内で読み取ることができる。
4. 3のcsv形式の履歴を削除することができる。(1つずつor全件同時)
5. 3のcsv形式の履歴をエクスポートすることができる。

## 簡易設計
app.py(flaskのエントリーインポート)
	∟index  
	∟history  
	∟delete_all  
	∟delete  
	∟download  
	∟import  
	
logic.py(CSV処理/計算及び判定/フィルタ・ソート機能)
	∟calc_profit (利益計算関数)  
	∟write_csv (csvファイルへの書き込みを行う)  
	∟csv_write_control (csvファイルの書き込みの複数or単体の制御を行う)  
	∟load_csv (csvファイルの読み込み)  
	∟judge_profit (買時購入の判定処理)  
	∟input_exe (入力値に対する処理)  
	∟history_sort (ソート機能)  
	∟history_filter (フィルタ機能)  
	∟price_prediction(価格が未入力の場合、みなし値を入れつつ利益300円以上になるよう計算する)  
	∟result_collect(htmlへ渡すresultの生成)
	∟input_check(数値の正当性をチェック)    


## 関数のテスト
簡単なテスト関数(手動確認用)も含まれます。コメントアウトによりON,OFFする想定です。  
ソースコード部分  
"if __name__ == "__main__":  
    test_judge()  # 確認したいときだけ有効化  
    app.run(debug=True)"  

## 実行イメージ
### 出品候補の例
#### 出品候補
![出品候補](docs/03_index_出品候補.png)

#### 利益が少なめ
![利益が少なめ](docs/04_index_利益が少なめ.png)

#### 赤字の例
![赤字](docs/05_index_赤字.png)

#### その他のスクリーンショット
flask_test/docs/以下に格納  

### 今後の改善
 2026/1/18で一旦区切りをつける
 以下項目に関しては次回以降のアプリ開発で取り組めたらいいなという案
- テストをpytestに置き換える
- デプロイ
- 継続課題  
	∟docstring(プログラムの解説)やコメントの記述をする  
	∟見直し＆追記を行う  
- DB実装  
	∟flaskとの共存を考える  
- 動的なページの実装  
	∟Javascriptとかphpを駆使すること  

### 区切り以降の機能更新
- 2025/2/5更新  
	価格が未入力の場合、利益が300円以上になるよう自動計算する機能を追加  
	これにより、価格を必須入力から除外  
	また送料が未入力の場合も自動計算するようする予定だったが、商品の大きさにより振れ幅が大きい為こちらの自動計算機能は実装しないこととする。  
