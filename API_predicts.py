import pandas as pd
import requests
import json
import time
import argparse
import os

def process_hpo_data(csv_file, output_path):

    df = pd.read_csv(csv_file)
    results = []

    for index, row in df.iterrows():
        hpo_ids = row["HPO_IDs"].replace('"', '')  # HPO_IDs列の"を削除
        disease = row["Disease"]

        url = f"https://pubcasefinder.dbcls.jp/api/pcf_get_ranked_list?target=omim&format=json&hpo_id={hpo_ids}"

        try:
            response = requests.get(url)
            response.raise_for_status()  # エラーステータスコードの場合、例外を発生
            data = response.json()

            # 各予測された疾患のIDをリストに追加
            predicted_diseases = [item["id"] for item in data]
            # predicted_diseases_json = json.dumps(predicted_diseases) # 不要な行。json.dumpsは文字列にするのでここでは不適切
            results.append({"predicted_Disease": predicted_diseases, "Disease": disease})  #  直接リストを渡す


        except requests.exceptions.RequestException as e:
            print(f"Error during API request for HPO IDs {hpo_ids}: {e}")
            results.append({"predicted_Disease": [], "Disease": disease})  # エラーが起きた場合は空のリスト

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for HPO IDs {hpo_ids}: {e}")
            results.append({"predicted_Disease": [], "Disease": disease})  # エラーが起きた場合は空のリスト

        time.sleep(1)  # APIへの連続アクセスを避けるため、1秒待機

    # 結果をDataFrameに変換し、CSVファイルに出力
    result_df = pd.DataFrame(results)
    result_df.to_csv(output_path + ".csv", index=False)


def main():
    parser = argparse.ArgumentParser(description='HPOと正解を持つcsvを受け取って、PubcaseFinderAPIに投げ、予測のリストと正解を持つcsvを出力するプログラム')
    parser.add_argument('csv_file_path', help='csvファイルのパス')
    parser.add_argument('--output_dir', default='API_res', help='出力のディレクトリ')
    parser.add_argument('--output_name', default="API_result", help='アウトプットファイルの名前')

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    process_hpo_data(args.csv_file_path, args.output_dir + "/" + args.output_name)


if __name__ == "__main__":
    main()