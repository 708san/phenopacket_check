import os
import json
import csv
import argparse
from typing import List, Dict, Optional, Any

def find_json_files(directory: str) -> List[str]:
    """指定されたディレクトリ以下のJSONファイルを再帰的に検索する"""
    json_files = []
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith('.json'):
                json_files.append(os.path.join(root, filename))
    return json_files

def extract_data_from_json(filepath: str) -> Optional[Dict[str, str]]:
    """
    JSONファイルから指定された情報を抽出し、親ディレクトリ名を'gene'として追加する。
    エラーが発生した場合や必須項目がない場合はNoneを返す。
    """
    try:
        # --- ここから追加 ---
        # JSONファイルの親ディレクトリ（サブディレクトリ）名を取得
        parent_directory_path = os.path.dirname(filepath)
        gene_name = os.path.basename(parent_directory_path)
        # --- ここまで追加 ---

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. idの取得 (必須)
        record_id = data.get('id')
        if not record_id:
            print(f"警告: {filepath} に 'id' が見つかりません。スキップします。")
            return None

        phenotypes = []
        excluded_phenotypes = []

        # 2. phenotypicFeaturesの処理
        phenotypic_features = data.get('phenotypicFeatures', [])
        if isinstance(phenotypic_features, list):
            for feature in phenotypic_features:
                if not isinstance(feature, dict):
                    print(f"警告: {filepath} の phenotypicFeatures 内に不正な要素があります。")
                    continue

                feature_type = feature.get('type')
                if isinstance(feature_type, dict) and 'id' in feature_type:
                    hp_id = feature_type['id']
                    is_excluded = feature.get('excluded', False)
                    if is_excluded is True:
                        excluded_phenotypes.append(hp_id)
                    else:
                        phenotypes.append(hp_id)
                else:
                    print(f"警告: {filepath} の phenotypicFeatures 内の要素に 'type.id' が見つかりません。")
        elif phenotypic_features is not None:
             print(f"警告: {filepath} の 'phenotypicFeatures' がリスト形式ではありません。")

        # 3. diseasesの処理 (最初の要素のterm.idを取得)
        disease_id = ""
        diseases = data.get('diseases', [])
        if isinstance(diseases, list) and len(diseases) > 0:
            first_disease = diseases[0]
            if isinstance(first_disease, dict):
                term = first_disease.get('term')
                if isinstance(term, dict) and 'id' in term:
                    disease_id = term['id']
                else:
                    print(f"警告: {filepath} の最初の disease に 'term.id' が見つかりません。")
            else:
                print(f"警告: {filepath} の diseases の最初の要素がオブジェクトではありません。")
        elif diseases is not None and not isinstance(diseases, list) :
             print(f"警告: {filepath} の 'diseases' がリスト形式ではありません。")

        # 4. カンマ区切り文字列に変換
        phenotypes_str = ",".join(phenotypes)
        excluded_phenotypes_str = ",".join(excluded_phenotypes)

        # --- ここから変更 ---
        # 戻り値の辞書に gene を追加
        return {
            'id': record_id,
            'phenotype': phenotypes_str,
            'excluded_phenotype': excluded_phenotypes_str,
            'disease': disease_id,
            'gene': gene_name # 親ディレクトリ名を追加
        }
        # --- ここまで変更 ---

    except json.JSONDecodeError:
        print(f"エラー: {filepath} は不正なJSON形式です。スキップします。")
        return None
    except Exception as e:
        print(f"エラー: {filepath} の処理中に予期せぬエラーが発生しました: {e}。スキップします。")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="指定ディレクトリ下のJSONファイルから情報を抽出しCSVに出力します。\nJSONファイルの親ディレクトリ名が 'gene' 列に追加されます。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_dir",
        help="JSONファイルが含まれるディレクトリのパス（サブディレクトリも検索対象）。"
    )
    parser.add_argument(
        "-o", "--output",
        default="output_with_gene.csv", # デフォルトファイル名を変更
        help="出力するCSVファイル名 (デフォルト: output_with_gene.csv)"
    )
    args = parser.parse_args()

    input_directory = args.input_dir
    output_csv_file = args.output

    if not os.path.isdir(input_directory):
        print(f"エラー: 指定されたディレクトリ '{input_directory}' が存在しません。")
        return

    json_files = find_json_files(input_directory)
    if not json_files:
        print(f"'{input_directory}' 内にJSONファイルが見つかりませんでした。")
        return

    print(f"{len(json_files)} 個のJSONファイルが見つかりました。処理を開始します...")

    csv_data = []
    processed_count = 0
    error_count = 0
    for filepath in json_files:
        extracted_data = extract_data_from_json(filepath)
        if extracted_data:
            csv_data.append(extracted_data)
            processed_count += 1
        else:
            error_count += 1

    if not csv_data:
        print("有効なデータがJSONファイルから抽出されませんでした。")
        return

    print(f"処理完了: {processed_count} 件のデータを抽出しました。{error_count} 件のファイルでエラーまたは必須項目不足がありました。")

    # CSV出力
    try:
        with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            # --- ここから変更 ---
            # ヘッダー名に 'gene' を追加
            fieldnames = ['id', 'phenotype', 'excluded_phenotype', 'disease', 'gene']
            # --- ここまで変更 ---
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(csv_data)
        print(f"CSVファイル '{output_csv_file}' を正常に出力しました。")

    except IOError as e:
        print(f"エラー: CSVファイル '{output_csv_file}' への書き込み中にエラーが発生しました: {e}")
    except Exception as e:
         print(f"エラー: CSV書き込み中に予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    main()