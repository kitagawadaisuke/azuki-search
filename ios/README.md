# AzukiSearch (iOS)

おかあさんといっしょ・いないいないばあっ! の放送内容を検索・記録・アーカイブする SwiftUI ネイティブアプリ。

## プロジェクト構成

```
ios/
├── project.yml                 # xcodegen設定 (Bundle ID / version 等)
├── AzukiSearch.xcodeproj/      # 生成物 (project.ymlからxcodegenで再生成可)
├── AzukiSearch/
│   ├── AzukiSearchApp.swift    # @main エントリ
│   ├── ContentView.swift       # TabView (4タブ)
│   ├── Models/                 # データモデル (Codable)
│   ├── Stores/                 # DataStore / FavoritesStore
│   ├── Theme/                  # 色・フォント・デザイントークン
│   ├── Views/                  # HeaderView / WeekCalendarView / ItemCardView etc.
│   ├── Assets.xcassets/        # AppIcon / AccentColor / LaunchScreenBackground
│   └── bundled_data.json       # オフライン/初回起動用 fallbackデータ
```

## 開発時

```bash
# 1) プロジェクト再生成 (project.yml を変更したとき)
cd ios && xcodegen generate

# 2) Xcode で開く
open AzukiSearch.xcodeproj

# 3) シミュレータで実行
xcodebuild -project AzukiSearch.xcodeproj -scheme AzukiSearch \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -configuration Debug build CODE_SIGNING_ALLOWED=NO
```

## データの流れ

1. アプリ起動 → `DataStore.load()`
2. リモート fetch: `https://raw.githubusercontent.com/kitagawadaisuke/okaa-san-finder/main/data.json`
3. 失敗時 (ネット無し / private repo / 404 等) → バンドル済 `bundled_data.json` を読む

**重要**: 現状リポジトリが private のため raw URL は 404 を返す。
リアルタイム更新を有効にするには **以下のどれか** を実施↓

### 案A: リポジトリを public にする (推奨)
```bash
gh repo edit kitagawadaisuke/okaa-san-finder --visibility public
```
これだけで OK。GH Actions の `refresh-data.yml` が毎日 4回 data.json を更新し、アプリは即取りに来る。

### 案B: data用に別 public repo を作る
- 新規 `kitagawadaisuke/azuki-data` (public) を作成
- 既存 `refresh-data.yml` で生成した data.json をそっちに push
- `DataStore.swift` の `dataURL` を新URLに差し替え

### 案C: バンドルのまま運用
- データ更新するたび `cp data.json ios/AzukiSearch/bundled_data.json` してリビルド & TestFlight再アップ

## TestFlight への配信手順

### 1. Xcode を開く
```bash
open ios/AzukiSearch.xcodeproj
```

### 2. Signing & Capabilities を設定
- ターゲット `AzukiSearch` 選択
- "Signing & Capabilities" タブ
- **Team** を自分の Apple Developer account (Personal Team含む) に設定
- **Bundle Identifier** が `com.kitagawadaisuke.azukisearch` になっているか確認 (重複NGなら変える)

### 3. App Store Connect にアプリを作成
- https://appstoreconnect.apple.com → "マイApp" → "+" → 新規App
- プラットフォーム: iOS
- 名前: あずきサーチ
- 言語: 日本語
- バンドルID: 上で設定したID
- SKU: `azukisearch` (任意の文字列)
- アクセス権: フルアクセス

### 4. Archive ビルド作成
- Xcode → 上部のターゲット選択を **"Any iOS Device (arm64)"** に変更 (シミュレータNG)
- メニュー: **Product → Archive**
- 数分待つ → Organizer ウィンドウが開く

### 5. TestFlight にアップロード
- Organizer で archive を選択 → **Distribute App**
- "App Store Connect" → "Upload" → 次へ
- 自動署名で OK
- アップロード完了 (5-10分)

### 6. App Store Connect で TestFlight 設定
- App Store Connect → 自App → TestFlight タブ
- 数分後にビルドが現れる
- "輸出コンプライアンス" を回答 (暗号化なしで `false`、Info.plistで設定済)
- **内部テストグループ** を作成 → ビルドを追加
- 自分のメアド (Apple ID) をテスター追加

### 7. iPhone で受け取る
- iPhoneに **TestFlight** アプリをインストール
- App Store Connect から招待メールが届く → "テストの承諾" をタップ
- TestFlightアプリで「あずきサーチ」が見える → **インストール**

## 既知の課題 / Future work

- AppIcon が空 → 1024x1024 png をデザインして `Assets.xcassets/AppIcon.appiconset/` に追加
- リモート data fetch (案A適用待ち)
- カードタップ時の詳細モーダル
- お気に入り fav の同期 (CloudKit や iCloud Drive)
- ダークモード対応 (現状ライトのみを想定)
- Pull-to-refresh のフィードバック改善
- 番組 (おかあさん/いないばあ) の切替UI
