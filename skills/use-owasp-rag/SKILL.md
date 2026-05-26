---
name: owasp-rag
description: |
  OWASP ASVS（Application Security Verification Standard v5.0）および AISVS（AI Security Verification Standard v1.0）を参照・検索するスキル。
  セキュリティ要件の確認、仕様レビュー、カバレッジチェックに使用する。

  以下のような状況で**必ず**このスキルを参照すること：
  - 「ASVS」「AISVS」「OWASP」「セキュリティ要件」「セキュリティ標準」に関する質問
  - 認証・認可・セッション管理・入力バリデーション・暗号化などのセキュリティ実装レビュー
  - 「どの要件を満たすべきか」「この機能は要件を満たしているか」という確認
  - 要件 ID（例: V1.1.1、C2.3.1）への直接言及
  - セキュリティレベル（Level 1 / 2 / 3）に関する質問
  - AI システムのセキュリティ要件確認（プロンプトインジェクション、訓練データ整合性など）
  - 仕様書・設計書のセキュリティレビュー依頼
---

# OWASP RAG MCP スキル

OWASP ASVS / AISVS の要件を MCP ツール経由で検索・参照するスキル。
ローカル Docker で起動した RAG システムに接続し、日本語クエリでも英語要件を横断検索できる。

## 前提条件

- ローカルで `owasp-rag-mcp` が起動済み（`make up` 完了後）
- `owasp-rag` MCP が Claude に登録・接続されていること

起動確認は `.env` で設定したポート番号を使って行うこと（例: `curl http://localhost:<PORT>/health`）

## 利用可能なツール

| ツール名 | 概要 | いつ使うか |
|---|---|---|
| `search_requirements` | 自然言語で要件をセマンティック検索 | キーワード・概念で要件を探すとき |
| `get_requirement` | 要件 ID を指定して詳細取得 | 特定の要件 ID が分かっているとき |
| `list_categories` | 章・カテゴリ一覧を取得 | 標準の構造を把握するとき・絞り込み前の確認 |
| `check_coverage` | 機能説明から関連要件を取得 | 実装・設計のカバレッジ確認 |

詳細は `references/mcp-tools.md` を参照。

## ツール選択フロー

```
ユーザーの質問
    │
    ├─ 「V2.1.1 を教えて」「C1.1.1 の内容は？」
    │   → get_requirement（req_id + standard を指定）
    │
    ├─ 「セッション管理の要件は？」「プロンプトインジェクション対策は？」
    │   → search_requirements（query + 必要に応じて standard / level）
    │
    ├─ 「ASVS にはどんな章がある？」「AISVS の構造を教えて」
    │   → list_categories（standard を指定）
    │
    └─ 「この認証機能はどの要件を満たすか？」「仕様書のセキュリティ確認をして」
        → check_coverage（feature に機能説明を渡す）
```

## 使い方パターン

### パターン1：要件の横断検索

```
search_requirements(
  query="セッション固定化の防止",
  standard="ASVS",   # 省略可（全標準を横断）
  level=1,           # 省略可（全レベル）
  top_k=5            # デフォルト5件
)
```

### パターン2：特定要件の参照

```
get_requirement(
  req_id="V3.2.1",
  standard="ASVS"   # 必須（ASVS / AISVS）
)
```

### パターン3：カテゴリ一覧の取得

```
list_categories(standard="AISVS")  # 省略すると全標準
```

### パターン4：仕様レビュー（カバレッジ確認）

```
check_coverage(
  feature="JWT を使ったステートレス認証。アクセストークン有効期限15分、リフレッシュトークン7日。",
  standard="ASVS",   # 省略可
  top_k=10           # デフォルト10件
)
```

## 回答スタイルのガイドライン

1. **検索結果は要件 ID・章名・本文を整理して提示**する
2. **スコア（類似度）も参考として伝える**（0.8以上は高関連、0.5未満は参考程度）
3. **レベル（L1/L2/L3）の意味を補足する**
   - Level 1：最低限のセキュリティ（全アプリ対象）
   - Level 2：一般的な業務アプリ向け
   - Level 3：高リスク・金融・医療など
4. **カバレッジ確認の結果は「満たせていない可能性がある要件」を強調する**
5. **日本語で質問されたら日本語で回答する**（要件本文は英語のまま引用してよい）

## エラー対処

| 症状 | 原因 | 対処 |
|---|---|---|
| ツールが応答しない | MCPサーバー未起動 | `make up` を実行、`curl http://localhost:8080/health` で確認 |
| 検索結果が0件 | データ未投入 | `make ingest` を実行 |
| req_id が見つからない | IDまたはstandardの誤り | `list_categories` で正しい章構造を確認 |

詳細は `references/mcp-tools.md` を参照。