import Foundation
import SwiftUI

// データ取得状態
enum LoadState: Equatable {
    case idle
    case loading
    case loaded
    case error(String)
}

@MainActor
final class DataStore: ObservableObject {
    @Published var items: [BroadcastItem] = []
    @Published var meta: [String: [String: BroadcastDayMeta]] = [:]
    @Published var generatedAt: String? = nil
    @Published var loadState: LoadState = .idle
    @Published var lastUpdated: Date? = nil

    // GitHub raw URL — scraper.py が生成した data.json を直接 fetch
    // 24h 以内ならローカル cache を返す (URLCache 経由)
    static let dataURL = URL(string: "https://raw.githubusercontent.com/kitagawadaisuke/azuki-search/main/data.json")!

    private var hasLoadedOnce = false

    /// アプリ起動 / 引っ張り更新 で呼ぶ
    func load(force: Bool = false) async {
        if loadState == .loading { return }
        if !force && hasLoadedOnce && Date().timeIntervalSince(lastUpdated ?? .distantPast) < 60 * 30 {
            return  // 30分以内ならスキップ
        }
        loadState = .loading

        // 1) リモート (GitHub raw) を試行
        if let remote = try? await fetchRemote(force: force) {
            self.applyPayload(remote)
            return
        }

        // 2) 失敗時はバンドル済 fallback を読む
        if let bundled = loadBundled() {
            self.applyPayload(bundled)
            // エラーは投げず、ステータスだけ控えめに
            return
        }

        // どちらもダメ
        self.loadState = .error("データの取得に失敗しました。ネットワーク接続を確認してください。")
    }

    private func applyPayload(_ p: DataPayload) {
        self.items = p.items
        self.meta = p.broadcastMeta ?? [:]
        self.generatedAt = p.generatedAt
        self.lastUpdated = Date()
        self.hasLoadedOnce = true
        self.loadState = .loaded
    }

    private func fetchRemote(force: Bool) async throws -> DataPayload {
        var req = URLRequest(url: Self.dataURL)
        req.cachePolicy = force ? .reloadIgnoringLocalCacheData : .useProtocolCachePolicy
        req.timeoutInterval = 12
        let (data, response) = try await URLSession.shared.data(for: req)
        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(DataPayload.self, from: data)
    }

    private func loadBundled() -> DataPayload? {
        guard let url = Bundle.main.url(forResource: "bundled_data", withExtension: "json"),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(DataPayload.self, from: data)
    }

    /// 同日同曲を1件にまとめる (週報+NHKの重複対策)
    func uniqueItems(forDate date: String) -> [BroadcastItem] {
        let same = items.filter { $0.date == date }
        var byKey: [String: BroadcastItem] = [:]
        for it in same {
            let key = "\(it.show)|\(Self.normalizeTitle(it.title))"
            if let prev = byKey[key] {
                let prevHasKw = !(prev.keywords ?? []).isEmpty
                let curHasKw = !(it.keywords ?? []).isEmpty
                if curHasKw && !prevHasKw {
                    byKey[key] = it
                } else if curHasKw == prevHasKw && (it.order ?? 999) < (prev.order ?? 999) {
                    byKey[key] = it
                }
            } else {
                byKey[key] = it
            }
        }
        // okaasan を先、inai を後、その後 order
        return byKey.values.sorted { a, b in
            if a.show != b.show { return a.show < b.show }
            return (a.order ?? 0) < (b.order ?? 0)
        }
    }

    /// 検索: タイトル/コーナー/歌詞/キーワードを横断
    /// 用途は録画済み番組の振り返りなので、未来日付(今日より後)は除外
    func searchItems(query: String) -> [BroadcastItem] {
        let q = Self.normalizeQuery(query)
        guard !q.isEmpty else { return [] }
        let today = Self.todayIso()
        return items.filter { it in
            it.date <= today && haystack(for: it).contains(q)
        }.sorted {
            // 新しい順 (date降順)
            $0.date > $1.date
        }
    }

    /// data.json に含まれる全日付 (YYYY-MM-DD) を昇順で
    func allDates() -> [String] {
        Array(Set(items.map { $0.date })).sorted()
    }

    /// 今日(Asia/Tokyo)の日付文字列 "YYYY-MM-DD"
    static func todayIso() -> String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Tokyo")
        return f.string(from: Date())
    }

    // MARK: - 検索正規化
    private func haystack(for it: BroadcastItem) -> String {
        var parts: [String] = [it.title, it.corner]
        if let m = it.mood { parts.append(m) }
        if let t = it.theme { parts.append(t) }
        if let s = it.snippet { parts.append(s) }
        if let ss = it.snippets { parts.append(contentsOf: ss) }
        if let kw = it.keywords { parts.append(contentsOf: kw) }
        if let sub = it.subcategory { parts.append(sub) }
        return parts.map(Self.normalizeQuery).joined(separator: "|")
    }

    /// カナ→ひらがな、記号削除、lowercase
    static func normalizeQuery(_ s: String) -> String {
        var result = ""
        for scalar in s.unicodeScalars {
            // カタカナ→ひらがな
            if scalar.value >= 0x30A1 && scalar.value <= 0x30F6 {
                result.unicodeScalars.append(Unicode.Scalar(scalar.value - 0x60)!)
            } else {
                result.unicodeScalars.append(scalar)
            }
        }
        return result
            .lowercased()
            .replacingOccurrences(of: "ー", with: "")
            .replacingOccurrences(of: "－", with: "")
            .replacingOccurrences(of: "〜", with: "")
            .replacingOccurrences(of: "！", with: "")
            .replacingOccurrences(of: "？", with: "")
            .replacingOccurrences(of: "・", with: "")
            .filter { !$0.isWhitespace }
    }

    static func normalizeTitle(_ s: String) -> String {
        normalizeQuery(s).replacingOccurrences(of: "♪", with: "")
            .replacingOccurrences(of: "☆", with: "")
            .replacingOccurrences(of: "★", with: "")
    }
}
