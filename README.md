# Gemma 4 Developer Agent Competition

Gemma E4B を使う単一エージェントの提出ベースラインです。リポジトリ調査、問題の再現、最小限の修正、テスト、`submit_patch` による提出をシステムプロンプトで指示します。推論時のツールはコンペのハーネスが提供します。外部 API は使用しません。

## ローカルでの検証と ZIP 生成

Python 3.10 以上で、リポジトリのルートから実行します。

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/package_submission.py
```

`dist/submission.zip` にルートの `agent.yaml` と `prompts/system.md` が入ります。同じ入力から同じ ZIP を生成します。パッケージャーは未知のモデル・ツール、提出ツールの欠落、危険な include、シンボリックリンク、余分なファイルを拒否します。現在のベースライン専用で、ADK 全仕様の検証器ではありません。拡張時は検証器とテストも更新してください。

## 構成

- `submission/agent.yaml`: E4B モデルとハーネス提供ツールの宣言。
- `submission/prompts/system.md`: 修正・テスト・予算管理・提出の手順。
- `tools/package_submission.py`: 安全性の基本検証と ZIP 生成。
- `tests/`: パッケージ生成と不正な設定の拒否テスト。

LoRA アダプターは含みません。これは未学習の設定ベースラインで、事後学習済みモデルや評価スコアを提供するものではありません。

## ハーネス仕様との照合

ユーザー提供の `HARNESS_README.md` の §2・§5–9 に照合しました。ツールは文字列リストで宣言し、`submit_patch` は最後のツール操作にします。サンドボックスはオフラインで依存関係は導入済みです。テスト・ランナー設定は提出パッチから除外されるため、エージェントは本体コードを修正し、一時再現スクリプトは `/tmp` に置きます。

ローカル検証器はこの2ファイルのベースライン専用です。公式コンパイラーや実際のモデル推論を代替しません。現環境には `swegemma` / `adk-submission` とモデル重み・評価データがなく、公式コンパイル、推論、解決率の測定は未実行です。

## データセット環境での評価

コンペ提供のハーネスをその配布手順で導入し、モデルと公開タスク・スナップショットを用意した環境で、次の公式 CLI を使います。パスは実データに合わせて変更してください。

```bash
swegemma eval \
  --tasks tasks.jsonl \
  --snapshots-dir snapshots \
  --submission-dir submission \
  --results-dir results/run_01 \
  --sandbox docker \
  --max-tool-calls 50 \
  --max-time-minutes 30 \
  --concurrency 1 \
  --display auto
```

これはローカル評価コマンドで、Kaggle の提出処理とは異なります。`summary.json` の解決率、`task_results.jsonl`、`patches/`、`test_outputs/`、`traces/` で失敗と時間を確認します。新しい実行ごとに別の結果ディレクトリを使ってください。

任意の `submission/eval_config.yaml` では `evaluation` 配下に `timeout_seconds`（単一コマンドの秒数）、`max_tool_calls`、`max_time_minutes`、`max_turns` を指定できます。現在は評価データ数が不明なため予算の値は固定していません。追加する場合はベースライン検証器の許可ファイルも拡張してください。全タスク12時間の総予算にはセットアップ時間も見込んで調整します。エージェント単体の時間計測はコンテナー準備後に始まります。

LoRA の学習、Kaggle へのアップロード、エントリー操作は未実施です。公式ランナーでのコンパイルと代表 issue のパッチ検証を通してから提出してください。L4 セッションはインターネット無効で運用します。

## Google Colab

`notebooks/gemma_agent_colab.ipynb` をColabで開き、最初のセルで `dist/colab-source.zip` をアップロードすると、テストと提出ZIP生成を実行できます。後半は任意の公式ハーネス評価用です。ハーネス・モデル・データと推論サーバーは別途準備し、パスを指定してください。Colab用セルは構文検証済みですが、Colab上での実行は未検証です。

### GitHubからColabを開く

[修正版ノートブックをColabで開く](https://colab.research.google.com/github/IrohasDarknesss/Gemma-4-Developer-Agent-Competition/blob/master/notebooks/Untitled1_gemma_ready.ipynb)

アップロード用の [colab-source.zip](downloads/colab-source.zip) と [submission.zip](downloads/submission.zip) は `downloads/` に保存しています。GitHubで各ファイルの「Download raw file」からダウンロードできます。ZIPは現時点のスナップショットです。設定変更後はパッケージャーで提出ZIPを再生成してください。

Colabノートブックの「共有された評価データの取得」で、指定されたGoogle Driveファイルを取得し、アーカイブのファイル一覧を確認できます。データ自体はGitHubに含めていません。ダウンロード・データ内容の確認はColab上で実行する必要があります。
