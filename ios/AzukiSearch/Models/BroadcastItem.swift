import Foundation

// data.json items[] の1件
struct BroadcastItem: Codable, Identifiable, Hashable {
    let id: Int
    let show: String              // "okaasan" | "inai"
    let title: String
    let corner: String            // "うた" / "人形劇" / "アニメ" / "体操" / "コーナー" など
    let date: String              // "YYYY-MM-DD"
    let airtime: String           // "HH:MM"
    let offset: String?
    let order: Int?
    let keywords: [String]?
    let mood: String?
    let snippet: String?
    let snippets: [String]?
    let theme: String?
    let characters: [String]?
    let source: String?           // "nhk" | "nhk+weekly" | nil
    let parent: String?           // ネスト曲: コーナー名
    let subcategory: String?

    enum CodingKeys: String, CodingKey {
        case id, show, title, corner, date, airtime, offset, order
        case keywords, mood, snippet, snippets, theme, characters
        case source, parent, subcategory
    }
}

// data.json broadcast_meta[show][date]
struct BroadcastDayMeta: Codable, Hashable {
    let description: String?
    let episodeName: String?
    let tvEpisodeId: String?
    let broadcastEventId: String?
    let startDate: String?
    let source: String?
}

// data.json ルート
struct DataPayload: Codable {
    let generatedAt: String?
    let source: String?
    let items: [BroadcastItem]
    let broadcastMeta: [String: [String: BroadcastDayMeta]]?

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case source
        case items
        case broadcastMeta = "broadcast_meta"
    }
}
