import Foundation
import SwiftUI

@MainActor
final class FavoritesStore: ObservableObject {
    private static let key = "azukisearch.favorites"

    @Published private(set) var ids: Set<Int> = []

    init() {
        load()
    }

    func contains(_ id: Int) -> Bool {
        ids.contains(id)
    }

    func toggle(_ id: Int) {
        if ids.contains(id) {
            ids.remove(id)
        } else {
            ids.insert(id)
        }
        save()
    }

    private func load() {
        let arr = UserDefaults.standard.array(forKey: Self.key) as? [Int] ?? []
        ids = Set(arr)
    }

    private func save() {
        UserDefaults.standard.set(Array(ids), forKey: Self.key)
    }
}
