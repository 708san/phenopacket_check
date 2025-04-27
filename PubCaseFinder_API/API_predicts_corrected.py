# coding: utf-8
import pandas as pd
import requests
import json
import time
import argparse
import os
from typing import List, Dict, Any # 型ヒントを追加

def process_hpo_data(csv_file: str, output_path: str):
    """
    指定されたCSVファイルを読み込み、'phenotype'列のHPO IDを使って
    PubCaseFinder APIに問い合わせ、予測された疾患IDリストと元の情報をCSVに出力する。
    'phenotype'が空の行はスキップする。
    """
    try:
        # CSV読み込み
        df = pd.read_csv(csv_file)
        # 必須カラムの存在チェック
        required_columns = ['id', 'phenotype', 'disease', 'gene']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            print(f"エラー: 入力CSVファイル '{csv_file}' に必須のカラムが不足しています: {missing_cols}")
            return

    except FileNotFoundError:
        print(f"エラー: CSVファイル '{csv_file}' が見つかりません。")
        return
    except Exception as e:
        print(f"エラー: CSVファイル '{csv_file}' の読み込み中にエラーが発生しました: {e}")
        return

    results: List[Dict[str, Any]] = [] # 結果を格納するリスト
    total_rows = len(df)
    processed_count = 0
    skipped_count = 0

    print(f"CSVファイル '{csv_file}' の処理を開始します。全{total_rows}行。")

    # DataFrameの各行を処理
    for index, row in df.iterrows():
        print(f"\r処理中: {index + 1}/{total_rows}", end="")

        # phenotype カラムの値を取得し、NaNやNoneの場合は空文字列にする
        phenotype_raw = row.get("phenotype")
        if pd.isna(phenotype_raw):
             phenotype_value = ""
        else:
            phenotype_value = str(phenotype_raw).strip() # 文字列化して前後の空白削除

        # phenotype が空の場合はスキップ
        if not phenotype_value:
            skipped_count += 1
            # スキップした行のIDを記録しておくとデバッグに役立つ場合がある
            # print(f"\n情報: 行 {index + 1} (id: {row.get('id', 'N/A')}) の phenotype が空のためスキップします。")
            continue # 次の行へ

        # 引用符を削除 (Phenopacket -> CSV 変換時に混入する可能性があるため)
        hpo_ids = phenotype_value.replace('"', '')

        # 元の disease, id, gene を取得
        original_disease = row.get("disease", "")
        original_id = row.get("id", "")
        original_gene = row.get("gene", "")

        # API URLを構築 (phenotype列のHPO IDを使用)
        # URLエンコードが必要な文字が含まれている場合は urllib.parse.quote を使うべきだが、
        # HPO IDとカンマなら通常は不要
        if not hpo_ids: # 念のため、置換後に空になっていないかチェック
            skipped_count += 1
            continue

        # APIエンドポイント (元のコードに合わせてdevサーバーではなく本番を使用)
        # 必要に応じて 'https://dev-pubcasefinder.dbcls.jp/api/pcf_get_ranked_list?target=omim&format=json&hpo_id={hpo_ids}' に変更してください
        url = f"https://pubcasefinder.dbcls.jp/api/pcf_get_ranked_list?target=omim&format=json&hpo_id={hpo_ids}"

        predicted_diseases: List[str] = [] # 予測結果リストの初期化

        try:
            # APIリクエスト実行 (タイムアウトを設定)
            response = requests.get(url, timeout=60) # タイムアウトを60秒に延長
            response.raise_for_status()  # HTTPエラー(4xx, 5xx)があれば例外発生
            data = response.json()

            # 予測された疾患のIDをリストに追加
            if isinstance(data, list): # レスポンスが期待通りリスト形式か確認
                predicted_diseases = [item["id"] for item in data if isinstance(item, dict) and "id" in item]
            else:
                 print(f"\n警告: 行 {index + 1} (id: {original_id}) APIレスポンスが予期せぬ形式です: {data}")

        except requests.exceptions.Timeout:
             print(f"\nエラー: 行 {index + 1} (id: {original_id}) APIリクエストがタイムアウトしました。URL: {url}")
             # タイムアウト時は空リストとして扱う
             predicted_diseases = []
        except requests.exceptions.RequestException as e:
            print(f"\nエラー: 行 {index + 1} (id: {original_id}) APIリクエスト中にエラー: {e}")
            # その他のリクエストエラー時も空リストとして扱う
            predicted_diseases = []
        except json.JSONDecodeError as e:
            print(f"\nエラー: 行 {index + 1} (id: {original_id}) JSONデコードエラー: {e}。レスポンス: {response.text[:200]}...")
            # JSONデコードエラー時も空リストとして扱う
            predicted_diseases = []
        except Exception as e:
             print(f"\nエラー: 行 {index + 1} (id: {original_id}) 予期せぬエラー: {e}")
             # その他のエラー時も空リストとして扱う
             predicted_diseases = []

        # 結果をリストに追加 (元の情報も保持)
        results.append({
            "id": original_id,
            "gene": original_gene,
            "phenotype": phenotype_value, # 参考のために元のphenotypeも出力
            "Disease": original_disease,   # 出力カラム名を 'Disease' に統一
            "predicted_Disease": predicted_diseases # 予測結果のリスト
        })
        processed_count += 1

        # APIへの連続アクセスを避けるため、1秒待機
        time.sleep(1)

    print(f"\n処理完了。処理行数: {processed_count}, スキップ行数(phenotype空): {skipped_count}")

    # 結果をDataFrameに変換し、CSVファイルに出力
    if results:
        result_df = pd.DataFrame(results)
        # 出力する列の順序を指定
        output_columns = ['id', 'gene', 'phenotype', 'Disease', 'predicted_Disease']
        # 存在しない列があってもエラーにならないようにフィルタリング
        result_df = result_df[[col for col in output_columns if col in result_df.columns]]

        try:
            # encoding='utf-8-sig' はExcelでの日本語文字化けを防ぐのに役立つ
            result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"結果をCSVファイル '{output_path}' に出力しました。")
        except IOError as e:
            print(f"エラー: CSVファイル '{output_path}' への書き込み中にエラーが発生しました: {e}")
        except Exception as e:
             print(f"エラー: CSV書き込み中に予期せぬエラーが発生しました: {e}")
    else:
        print("処理対象のデータが見つからなかったか、すべての行がスキップされたため、CSVファイルは出力されませんでした。")


def main():
    parser = argparse.ArgumentParser(
        description='phenotype情報を含むCSVを受け取り、PubCaseFinder APIで疾患予測を行い、結果をCSV出力するプログラム'
    )
    parser.add_argument('csv_file_path', help='入力CSVファイルのパス (id,phenotype,disease,gene カラムを含む)')
    parser.add_argument('--output_dir', default='API_res', help='出力ディレクトリ (デフォルト: API_res)')
    # デフォルトの出力ファイル名に拡張子 .csv を含めるように修正
    parser.add_argument('--output_name', default="API_result.csv", help='出力ファイル名 (デフォルト: API_result.csv)')

    args = parser.parse_args()

    # 出力ディレクトリを作成 (存在していてもエラーにならない)
    try:
        os.makedirs(args.output_dir, exist_ok=True)
    except OSError as e:
        print(f"エラー: 出力ディレクトリ '{args.output_dir}' の作成に失敗しました: {e}")
        return

    # 出力ファイルのフルパスを作成
    output_file_path = os.path.join(args.output_dir, args.output_name)

    # HPOデータの処理を実行
    process_hpo_data(args.csv_file_path, output_file_path)


if __name__ == "__main__":
    main()

