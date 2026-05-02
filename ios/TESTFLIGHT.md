# TestFlight 配信手順 (初回)

このドキュメントは あずきサーチ iOSアプリを TestFlight にアップロードする手順をまとめたもの。
2回目以降は手順 4-7 だけでOK。

---

## 0. 前提

- ✅ Apple Developer Program 登録済み (個人 99/year または 法人)
- ✅ Mac + Xcode 26 以降
- ✅ App Store Connect にログインできる Apple ID
- ✅ リポジトリ `kitagawadaisuke/azuki-search` が public (data fetch 用)

---

## 1. プロジェクトを開く

```bash
cd ios
xcodegen generate     # AzukiSearch.xcodeproj を生成
open AzukiSearch.xcodeproj
```

---

## 2. Team & 署名設定 (初回のみ)

Xcode で:

1. 左ペインで **AzukiSearch** project を選択 → ターゲット **AzukiSearch**
2. **"Signing & Capabilities"** タブ
3. **"Automatically manage signing"** にチェック (default ON)
4. **Team** ドロップダウンから自分の Apple Developer Team を選ぶ
5. **Bundle Identifier** が `com.kitagawadaisuke.azukisearch` になってる
   - すでに同じBundle IDが他で使われてたら衝突する → ユニークなID(例: `com.<yourname>.azukisearch`)に変える
6. Xcode が自動で signing certificate / provisioning profile を作成する (数秒待つ)

---

## 3. App Store Connect にアプリ登録 (初回のみ)

ブラウザで [App Store Connect](https://appstoreconnect.apple.com) へ:

1. **マイ App** → **+** → **新規App**
2. 入力:
   - プラットフォーム: **iOS**
   - 名前: **あずきサーチ**
   - 主要言語: **日本語**
   - Bundle ID: 上で設定したID (Xcodeでまだarchiveしてないと表示されない場合あり、その場合は archive後にやる)
   - SKU: `azukisearch` (任意)
   - ユーザアクセス: フルアクセス
3. 作成

---

## 4. Archive ビルド作成

Xcode で:

1. 上部の **destination 選択ドロップダウン** を **"Any iOS Device (arm64)"** に変更
   - シミュレータでは Archive できない、要注意
2. メニュー: **Product → Archive**
3. 数分待つ → 自動で **Organizer** ウィンドウが開く

---

## 5. TestFlight にアップロード

Organizer の Archives タブで:

1. 作成された archive を選択
2. 右の **"Distribute App"** ボタン
3. **"App Store Connect"** → **"Upload"** → 次へ
4. 自動署名で進めるならそのまま、Distribution certificate と provisioning profile が自動作成
5. **"Upload"** ボタンでアップロード開始 (5〜10分)
6. ✅ "App uploaded successfully" が出れば成功

---

## 6. App Store Connect で TestFlight 設定

[App Store Connect](https://appstoreconnect.apple.com) → 自App → **TestFlight** タブ:

1. アップロードから 5〜30 分後にビルドが現れる(処理中→処理完了)
2. ビルド横の "Manage" → **輸出コンプライアンス** で:
   - 暗号化使ってないので **"いいえ"** を選択 (Info.plist で `ITSAppUsesNonExemptEncryption: false` 設定済みなので質問されないかも)
3. **左メニュー: 内部テスト** → **+** → 新規グループ
   - 名前: 例 "Family"
   - ビルドを **追加**
4. **テスター** タブで自分の Apple ID メアドを追加 → "招待" 送信

---

## 7. iPhone でインストール

1. iPhone に **TestFlight** アプリをApp Storeからインストール (まだなら)
2. 招待メールを iPhone で開く → **"テストの承諾"** をタップ
3. TestFlight アプリで **「あずきサーチ」** が見える → **"インストール"**
4. 起動 → 動作確認 (音声検索は実機でしか試せないやつ!)

---

## トラブル時

| エラー | 解決 |
|---|---|
| `No accounts found` | Xcode → Settings → Accounts で Apple ID 追加 |
| `Could not find or create signing certificates` | Apple Developer プログラムに加入済か確認 / Team選択 |
| Bundle ID 衝突 | `com.<unique>.azukisearch` に変更 |
| Archive メニューがグレーアウト | destination が **"Any iOS Device"** か確認、シミュレータNG |
| アップロード後ビルドが現れない | 30分待つ。それでも出なければ App Store Connect の「メッセージ」を確認 |

---

## 開発時の通常フロー

```bash
# データを最新に
python3 scraper.py --weeks 4 --retain-weeks 4
cp data.json ios/AzukiSearch/bundled_data.json

# プロジェクト再生成 (project.yml いじったとき)
cd ios && xcodegen generate

# 動作確認
open AzukiSearch.xcodeproj   # Xcode → Run on simulator

# 新バージョン配信
# project.yml の CFBundleVersion を 1 → 2 に
cd ios && xcodegen generate
# Xcode → Archive → TestFlight upload (手順 4-5)
```
