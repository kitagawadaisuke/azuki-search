import Foundation
import SwiftUI

/// 各放送itemに対するユーザーメモ。item id をキーにUserDefaultsで永続化。
@MainActor
final class MemoStore: ObservableObject {
    private static let key = "azukisearch.memos.v1"

    /// id -> memo
    @Published private(set) var memos: [Int: String] = [:]

    init() {
        load()
    }

    func memo(for id: Int) -> String {
        memos[id] ?? ""
    }

    func hasMemo(for id: Int) -> Bool {
        !(memos[id] ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    /// 上書き保存。空文字なら削除。
    func set(_ text: String, for id: Int) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            memos.removeValue(forKey: id)
        } else {
            memos[id] = text
        }
        save()
    }

    private func load() {
        if let data = UserDefaults.standard.data(forKey: Self.key),
           let decoded = try? JSONDecoder().decode([Int: String].self, from: data) {
            memos = decoded
        }
    }

    private func save() {
        if let data = try? JSONEncoder().encode(memos) {
            UserDefaults.standard.set(data, forKey: Self.key)
        }
    }
}
