import SwiftUI

struct KeywordSearchView: View {
    @EnvironmentObject var dataStore: DataStore
    @EnvironmentObject var favs: FavoritesStore

    @State private var query: String = ""
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
                        subtitle: "曲名・コーナー・歌詞・出演者で探す",
                        query: $query
                    )

                    Group {
                        if query.trimmingCharacters(in: .whitespaces).isEmpty {
                            emptyHint
                        } else {
                            Text("「\(query)」の検索結果 (\(grouped.count)件)")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundColor(AppColor.text)
                                .padding(.horizontal, 16)
                                .padding(.top, 14)
                                .padding(.bottom, 10)

                            if grouped.isEmpty {
                                noResults
                            } else {
                                LazyVStack(spacing: 10) {
                                    ForEach(grouped, id: \.title) { g in
                                        VStack(alignment: .leading, spacing: 4) {
                                            ItemCardView(
                                                item: g.items[0],
                                                isFav: favs.contains(g.items[0].id),
                                                onToggleFav: { favs.toggle(g.items[0].id) },
                                                showDate: true
                                            )
                                            if g.items.count > 1 {
                                                Text("同じ曲: 他に \(g.items.count - 1) 回放送")
                                                    .font(.system(size: 10))
                                                    .foregroundColor(AppColor.textDim)
                                                    .padding(.leading, 14)
                                                    .padding(.bottom, 4)
                                            }
                                        }
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
    private var emptyHint: some View {
        VStack(spacing: 12) {
            Text("🔎")
                .font(.system(size: 48))
            Text("曲名・コーナー・歌詞・出演者などで検索")
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
