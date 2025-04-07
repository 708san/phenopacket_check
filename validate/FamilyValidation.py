import json
# jsonschemaからRefResolverをインポート
from jsonschema import validate, ValidationError, FormatChecker, RefResolver
import argparse
import os
import pathlib # pathlib を使うとパス操作が楽

def validation_json_files(json_schema_path, json_dir):
    schema_path_obj = pathlib.Path(json_schema_path).resolve()
    schema_dir = schema_path_obj.parent # スキーマファイルのあるディレクトリ

    try:
        with open(schema_path_obj) as f:
            main_schema_content = json.load(f) # メインスキーマをロード
    except FileNotFoundError:
        print(f"エラー: メインのJSONスキーマファイルが見つかりません: {schema_path_obj}")
        return []
    except json.JSONDecodeError:
        print(f"エラー: メインのスキーマファイルが不適切なJSONです: {schema_path_obj}")
        return []

    # --- 修正箇所 ---
    # store を初期化し、まずメインスキーマ自身を登録する
    base_uri = schema_path_obj.as_uri()
    store = {
        base_uri: main_schema_content
    }

    # 参照される可能性のあるスキーマ (PhenoPacket_Schema.json) を特定し、読み込みを試みる
    # ここでは特定のファイル名を想定しているが、より汎用的な処理も可能
    ref_schema_name = "PhenoPacket_Schema.json"
    ref_schema_path = schema_dir / ref_schema_name
    try:
        with open(ref_schema_path) as f:
            ref_schema_content = json.load(f)
        # 読み込みに成功した場合のみ store に追加
        store[ref_schema_name] = ref_schema_content
        store[ref_schema_path.as_uri()] = ref_schema_content
        print(f"情報: 参照スキーマ '{ref_schema_name}' を読み込みました。")
    except FileNotFoundError:
        # ファイルが存在しなくてもエラーとせず、警告メッセージを出す（参照がなければ問題ない）
        print(f"警告: 参照スキーマファイル '{ref_schema_name}' がディレクトリ '{schema_dir}' に見つかりません。")
        print("      もしメインスキーマがこのファイルを参照している場合、検証エラーになります。")
    except json.JSONDecodeError:
        # JSONとして不正な場合はエラーメッセージを出力するが、処理は続行させる場合もある
        # ここではエラーとして扱い、検証不能とするのが安全かもしれないのでリストを返す
        print(f"エラー: 参照されるスキーマファイル '{ref_schema_name}' が不適切なJSONです。検証を中断します。")
        return []
    # --- 修正箇所ここまで ---


    # RefResolverインスタンスを作成 (storeには読み込めたスキーマのみが含まれる)
    resolver = RefResolver(base_uri=base_uri, referrer=main_schema_content, store=store)

    invalid_files = []

    for root, _, files in os.walk(json_dir):
        for file_name in files:
            if file_name.endswith(".json"):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, "r") as f:
                        loaded_json = json.load(f)
                    # validate関数に resolver を渡す
                    validate(instance=loaded_json, schema=main_schema_content, resolver=resolver, format_checker=FormatChecker())
                    print(f"✅ {file_path} はスキーマに準拠しています。") # 成功メッセージを追加
                except FileNotFoundError:
                    print(f"エラー: {file_path} にファイルが存在しません")
                    # invalid_files に追加しない（検証対象のJSONがないだけなので）
                except json.JSONDecodeError:
                    print(f"エラー: {file_path} は不適切なJSONファイルです")
                    invalid_files.append(file_path)
                except ValidationError as e:
                    # エラーメッセージを少し詳しく表示
                    error_path = " -> ".join(map(str, e.path)) if e.path else "ルート要素"
                    print(f"\n--- Validation Error ---")
                    print(f"❌ ファイル: {file_path}")
                    print(f"   場所: {error_path}")
                    print(f"   エラー内容: {e.message}")
                    # print(f"   違反したスキーマ部分: {e.schema}") # 詳細すぎる場合はコメントアウト
                    print(f"------------------------")
                    invalid_files.append(file_path)
                except Exception as e: # 参照解決エラーなども含め、他のエラーもキャッチ
                    # jsonschema.exceptions._WrappedReferencingError を含む
                    print(f"\n--- Error during validation ---")
                    print(f"❌ ファイル: {file_path}")
                    print(f"   エラー: {type(e).__name__} - {e}")
                    print(f"-----------------------------")
                    invalid_files.append(file_path)

    return invalid_files


def main():
    parser = argparse.ArgumentParser(description='json_schemaファイルのパスとjsonファイルが保存されているディレクトリのパスを受け取り、ディレクトリ内のjsonファイルをvalidationするプログラム')
    parser.add_argument('schema_path', help='メインのjsonスキーマのパス (例: Phenopacket_schema/Family_schema.json)')
    parser.add_argument('file_dir', help='検証対象のjsonファイルが保存されているディレクトリのパス')
    args = parser.parse_args()

    print(f"スキーマ: {args.schema_path}")
    print(f"検証対象ディレクトリ: {args.file_dir}")
    print("検証を開始します...")

    invalid_files = validation_json_files(args.schema_path, args.file_dir)

    print("\n検証が完了しました。")
    if not invalid_files:
        print("\n🎉 すべての検証対象JSONファイルはスキーマに準拠しています。")
    else:
        # 重複を除いてリスト化し、ソート
        unique_invalid_files = sorted(list(set(invalid_files)))
        print(f"\n⚠️ {len(unique_invalid_files)}個のファイルがスキーマに準拠していません:")
        for file_path in unique_invalid_files:
            print(f"  - {file_path}")


if __name__ == '__main__':
    main()