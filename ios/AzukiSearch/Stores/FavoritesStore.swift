import Foundation
import SwiftUI

/// お気に入り保存。
/// item 自体をローカルに保持するため、data.json から放送が消えても(古い回など)表示し続ける。
/// 外す(★を解除する)とローカルからも消える。
@MainActor
final class FavoritesStore: ObservableObject {
    private static let key = "azukisearch.favorites.v2"
    private static let legacyKey = "azukisearch.favorites"

    /// id -> item
    @Published private(set) var items: [Int: BroadcastItem] = [:]

    init() {
        load()
    }

    func contains(_ id: Int) -> Bool {
        items[id] != nil
    }

    /// itemをお気に入りに追加(または最新メタで更新)
    func add(_ item: BroadcastItem) {
        items[item.id] = item
        save()
    }

    /// 外す
    func remove(_ id: Int) {
        items.removeValue(forKey: id)
        save()
    }

    /// トグル: 追加には item 情報が必須
    func toggle(_ item: BroadcastItem) {
        if contains(item.id) {
            remove(item.id)
        } else {
            add(item)
        }
    }

    /// 並び替え済の全件 (新しい順)
    var allItems: [BroadcastItem] {
        items.values.sorted {
            if $0.date != $1.date { return $0.date > $1.date }
            return ($0.order ?? 0) < ($1.order ?? 0)
        }
    }

    /// dataStore側に同 id があれば、保存しているメタ情報を最新で上書きする
    /// (snippets追加など、最新dataで補強したい時用。fav登録自体は維持)
    func refreshIfPresent(from sourceItems: [BroadcastItem]) {
        var changed = false
        for src in sourceItems where items[src.id] != nil {
            items[src.id] = src
            changed = true
        }
        if changed { save() }
    }

    // MARK: - 永続化

    private func load() {
        if let data = UserDefaults.standard.data(forKey: Self.key),
           let decoded = try? JSONDecoder().decode([Int: BroadcastItem].self, from: data) {
            items = decoded
            return
        }
        // 旧フォーマット(id配列のみ)からの移行はitem実体が無いため不可
        // 起動時に dataStore.items から refreshIfPresent で補完する想定だが、
        // 旧 id を仮のplaceholderで持っても意味がないため一旦無視
        _ = UserDefaults.standard.array(forKey: Self.legacyKey)
    }

    private func save() {
        if let data = try? JSONEncoder().encode(items) {
            UserDefaults.standard.set(data, forKey: Self.key)
        }
    }
}
