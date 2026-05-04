import SwiftUI

struct KeywordSearchView: View {
    @EnvironmentObject var dataStore: DataStore
    @EnvironmentObject var favs: FavoritesStore

    @State private var query: String = ""
    @State private var expandedTitles: Set<String> = []
    @FocusState private var searchFocus: Bool

    private var results: [BroadcastItem] {
        if query.trimmingCharacters(in: .whitespaces).isEmpty { return [] }
        return dataStore.searchItems(query: query)
    }

    private var grouped: [(title: String, items: [BroadcastItem])] {
        // タイトル単位でgroup、最新放送回を代表表示
        var byTitle: [String: [BroadcastItem]] = [:]
        for it in results {
            byTitle[it.title, default: []].append(it)
        }
        return byTitle
            .map { (title: $0.key, items: $0.value.sorted { $0.date > $1.date }) }
            .sorted { ($0.items.first?.date ?? "") > ($1.items.first?.date ?? "") }
    }

    var body: some View {
        ZStack(alignment: .top) {
            AppColor.bgGradient.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HeaderView(
                        title: "キーワード検索",
                        subtitle: "曲名・コーナー・歌詞で探す",
                        query: $query
                    )

                    Group {
                        if query.trimmingCharacters(in: .whitespaces).isEmpty {
                            emptyHint
                        } else {
                            resultHeading

                            if grouped.isEmpty {
                                noResults
                            } else {
                                LazyVStack(spacing: 10) {
                                    ForEach(grouped, id: \.title) { g in
                                        groupSection(g)
                                    }
                                }
                                .padding(.horizontal, 16)
                            }
                        }
                    }

                    Spacer(minLength: 24)
                }
            }
        }
    }

    @ViewBuilder
    private var resultHeading: some View {
        let total = results.count
        let unique = grouped.count
        Text(unique == total
             ? "「\(query)」の検索結果 (\(total)件)"
             : "「\(query)」の検索結果 (\(unique)曲・\(total)回放送)")
            .font(.system(size: 16, weight: .bold))
            .foregroundColor(AppColor.text)
            .padding(.horizontal, 16)
            .padding(.top, 14)
            .padding(.bottom, 10)
    }

    @ViewBuilder
    private func groupSection(_ g: (title: String, items: [BroadcastItem])) -> some View {
        let isExpanded = expandedTitles.contains(g.title)
        VStack(alignment: .leading, spacing: 6) {
            // 代表(最新放送)
            ItemCardView(
                item: g.items[0],
                isFav: favs.contains(g.items[0].id),
                onToggleFav: { favs.toggle(g.items[0]) },
                showDate: true
            )

            if g.items.count > 1 {
                if isExpanded {
                    // 展開: 残りの放送日を全部出す
                    ForEach(g.items.dropFirst(), id: \.id) { it in
                        ItemCardView(
                            item: it,
                            isFav: favs.contains(it.id),
                            onToggleFav: { favs.toggle(it) },
                            showDate: true
                        )
                    }
                    Button {
                        expandedTitles.remove(g.title)
                    } label: {
                        Text("▲ 折りたたむ")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(AppColor.primaryBlue)
                            .padding(.leading, 14)
                            .padding(.bottom, 4)
                    }
                    .buttonStyle(.plain)
                } else {
                    // 折畳: タップで展開リンク
                    Button {
                        expandedTitles.insert(g.title)
                    } label: {
                        Text("▼ 同じ曲: 他に \(g.items.count - 1) 回放送 (タップで全部表示)")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(AppColor.primaryBlue)
                            .padding(.leading, 14)
                            .padding(.bottom, 4)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    @ViewBuilder
    private var emptyHint: some View {
        VStack(spacing: 12) {
            Text("🔎")
                .font(.system(size: 48))
            Text("曲名・コーナー・歌詞などで検索")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(AppColor.textDim)
                .multilineTextAlignment(.center)
            Text("カナ・ひらがな・漢字どれでもOK")
                .font(.system(size: 11))
                .foregroundColor(AppColor.textVeryDim)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 80)
    }

    @ViewBuilder
    private var noResults: some View {
        VStack(spacing: 8) {
            Text("見つかりませんでした")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(AppColor.textDim)
            Text("カナ・ひらがな両方ためしてみてね")
                .font(.system(size: 11))
                .foregroundColor(AppColor.textVeryDim)
        }
        .padding(.vertical, 40)
        .frame(maxWidth: .infinity)
    }
}
