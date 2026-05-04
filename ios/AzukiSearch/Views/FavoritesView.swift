import SwiftUI

struct FavoritesView: View {
    @EnvironmentObject var dataStore: DataStore
    @EnvironmentObject var favs: FavoritesStore

    @State private var query: String = ""

    private var favItems: [BroadcastItem] {
        // favsローカル保存ベース。dataStore.items に無くなった古い回も表示し続ける
        let all = favs.allItems
        if query.trimmingCharacters(in: .whitespaces).isEmpty {
            return all
        }
        let q = DataStore.normalizeQuery(query)
        return all.filter { DataStore.normalizeTitle($0.title).contains(q) }
    }

    var body: some View {
        ZStack(alignment: .top) {
            AppColor.bgGradient.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HeaderView(
                        title: "お気に入り",
                        subtitle: "保存した放送内容",
                        query: $query,
                        searchPlaceholder: "保存した曲名で絞り込み"
                    )

                    Text("保存した放送 (\(favItems.count)件)")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(AppColor.text)
                        .padding(.horizontal, 16)
                        .padding(.top, 14)
                        .padding(.bottom, 10)

                    if favItems.isEmpty {
                        emptyState
                    } else {
                        LazyVStack(spacing: 10) {
                            ForEach(favItems) { item in
                                ItemCardView(
                                    item: item,
                                    isFav: true,
                                    onToggleFav: { favs.toggle(item) },
                                    showDate: true
                                )
                            }
                        }
                        .padding(.horizontal, 16)
                    }

                    Spacer(minLength: 24)
                }
            }
        }
    }

    @ViewBuilder
    private var emptyState: some View {
        VStack(spacing: 12) {
            Text("♡")
                .font(.system(size: 48))
                .foregroundColor(AppColor.textVeryDim)
            Text("お気に入りはまだありません")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(AppColor.textDim)
            Text("気になる曲の★を押して保存")
                .font(.system(size: 11))
                .foregroundColor(AppColor.textVeryDim)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 60)
    }
}
